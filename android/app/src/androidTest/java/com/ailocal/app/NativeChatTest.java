package com.ailocal.app;

import static org.junit.Assert.*;

import android.app.NotificationManager;
import android.content.Intent;
import android.webkit.WebView;
import androidx.test.ext.junit.rules.ActivityScenarioRule;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.rule.ServiceTestRule;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Real WebView -> Java bridge -> JNI -> GGUF -> streamed WebView response. */
@RunWith(AndroidJUnit4.class)
public class NativeChatTest {
  @Rule
  public ActivityScenarioRule<MainActivity> rule = new ActivityScenarioRule<>(MainActivity.class);

  @Rule public ServiceTestRule serviceRule = new ServiceTestRule();

  private MainActivity activity() {
    MainActivity[] current = {null};
    rule.getScenario().onActivity(value -> current[0] = value);
    return current[0];
  }

  private String evaluate(String script) throws Exception {
    CountDownLatch ready = new CountDownLatch(1);
    String[] result = {null};
    rule.getScenario()
        .onActivity(
            activity -> {
              WebView web = activity.getWindow().getDecorView().findViewWithTag("app-webview");
              web.evaluateJavascript(
                  script,
                  value -> {
                    result[0] = value;
                    ready.countDown();
                  });
            });
    assertTrue(ready.await(15, TimeUnit.SECONDS));
    return result[0];
  }

  private void await(String condition, int seconds) throws Exception {
    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(seconds);
    while (System.nanoTime() < deadline) {
      if ("true".equals(evaluate(condition))) return;
      Thread.sleep(250);
    }
    fail("Timed out: " + condition + "\nUI: " + evaluate("document.body.innerText"));
  }

  @Test
  public void downloadedModelAnswersThroughActualBridgeAndSurvivesLongPrompt() throws Exception {
    File fixture = new File(activity().getFilesDir(), "inference-fixture.gguf");
    assertTrue("CI must install its SHA-verified inference fixture", fixture.isFile());
    File model =
        new File(
            activity().getExternalFilesDir("models"), "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf");
    Files.copy(fixture.toPath(), model.toPath(), StandardCopyOption.REPLACE_EXISTING);
    Files.write(
        new File(model + ".ready").toPath(),
        "CI verified SHA-256".getBytes(StandardCharsets.UTF_8));
    await("typeof window.receive === 'function'", 30);
    evaluate("Native.command('state','{}')");
    await("state.installed.includes('qwen05')", 30);
    evaluate(
        "prefs.autoLoad=false;prefs.response=256;document.getElementById('responseTokens').value='256';"
            + "beginLoad(state.models.find(m=>m.id==='qwen05'))");
    await("!running && state.active === 'qwen05'", 120);
    assertEquals("false", evaluate("!!chatFailure"));
    assertEquals(
        "false", evaluate("!document.getElementById('chatHint').classList.contains('hidden')"));

    // The exact greeting from the reported blank-chat screen must reach real inference.
    evaluate(
        "newConversation();document.getElementById('prompt').value='Hola que"
            + " tal';document.getElementById('send').click()");
    await("!running", 120);
    assertEquals(
        "true", evaluate("messages.some(m=>m.role==='assistant' && m.content.trim().length>0)"));
    assertEquals("false", evaluate("!!chatFailure"));

    // More than n_batch=128 input tokens previously caused a native assertion/abort.
    evaluate(
        "newConversation();document.getElementById('prompt').value='dato '.repeat(160)+' Responde:"
            + " ¿cuánto es 2+2?';document.getElementById('send').click()");
    await("!running", 180);
    assertEquals(
        "true",
        evaluate(
            "messages.length===2 && messages[1].role==='assistant' &&"
                + " messages[1].content.trim().length>0"));
    assertEquals("false", evaluate("!!chatFailure"));

    // A native context error remains visible, preserving the user message for retry.
    evaluate(
        "newConversation();document.getElementById('prompt').value='dato"
            + " '.repeat(1500);document.getElementById('send').click()");
    await("!running && !!chatFailure", 30);
    assertEquals(
        "true", evaluate("messages.length===1 && !!document.querySelector('.retry-operation')"));
    evaluate(
        "newConversation();document.getElementById('prompt').value='Responde solo con el número:"
            + " 2+2=';document.getElementById('send').click()");
    await("!running", 120);
    assertEquals(
        "true", evaluate("messages.some(m=>m.role==='assistant' && m.content.includes('4'))"));
    InferenceService service =
        ((InferenceService.LocalBinder)
                serviceRule.bindService(new Intent(activity(), InferenceService.class)))
            .service();
    String instance = service.snapshot().getString("instanceId");
    assertTrue(service.snapshot().getBoolean("foreground"));
    assertTrue(
        activity().getSystemService(NotificationManager.class).getActiveNotifications().length > 0);

    // Go Home during real generation. No WebView receives tokens while stopped.
    evaluate(
        "newConversation();document.getElementById('prompt').value='Cuenta del 1 al 100, separados"
            + " por comas.';document.getElementById('send').click()");
    await("state.inference.busy && state.inference.job.action === 'chat'", 30);
    assertTrue(service.snapshot().getBoolean("wakeHeld"));
    assertTrue(
        InstrumentationRegistry.getInstrumentation()
            .getUiAutomation()
            .performGlobalAction(
                android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME));
    long backgroundDeadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(180);
    while (service.snapshot().getBoolean("busy") && System.nanoTime() < backgroundDeadline)
      Thread.sleep(250);
    assertFalse(
        "Inference did not finish while the Activity was in the background",
        service.snapshot().getBoolean("busy"));
    assertEquals("qwen05", service.activeModel());
    assertFalse(
        "CPU wake lock must be released after the answer",
        service.snapshot().getBoolean("wakeHeld"));
    Intent reopen =
        InstrumentationRegistry.getInstrumentation()
            .getTargetContext()
            .getPackageManager()
            .getLaunchIntentForPackage("com.ailocal.app");
    reopen.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
    InstrumentationRegistry.getInstrumentation().getTargetContext().startActivity(reopen);
    await("!running && messages.filter(m=>m.role==='assistant').length === 1", 60);
    assertEquals("false", evaluate("!!chatFailure"));

    // Recreating the Activity must reconnect to the same model and in-flight reply.
    evaluate(
        "newConversation();document.getElementById('prompt').value='dato '.repeat(160)+' Cuenta del"
            + " 1 al 30.';document.getElementById('send').click()");
    await("state.inference.busy && state.inference.job.action === 'chat'", 30);
    rule.getScenario().recreate();
    await("typeof window.receive === 'function' && state.active === 'qwen05'", 30);
    await("!running && messages.filter(m=>m.role==='assistant').length === 1", 180);
    assertEquals(instance, service.snapshot().getString("instanceId"));
    assertEquals("false", evaluate("!!chatFailure"));
    evaluate(
        "document.getElementById('prompt').value='Responde solo con el número:"
            + " 3+3=';document.getElementById('send').click()");
    await("!running && messages.filter(m=>m.role==='assistant').length === 2", 120);
    assertTrue(
        "Subsequent turns must reuse the processed prefix",
        service.snapshot().getJSONObject("job").getJSONObject("metrics").getInt("cachedTokens")
            > 20);
    assertFalse(activity().isFinishing());
    service.releaseModel();
    long releaseDeadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(30);
    while (!service.activeModel().isEmpty() && System.nanoTime() < releaseDeadline)
      Thread.sleep(100);
    assertEquals("", service.activeModel());
    assertFalse(service.snapshot().getBoolean("wakeHeld"));
  }
}
