package com.ailocal.app;

import static org.junit.Assert.*;

import android.webkit.WebView;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.rule.ActivityTestRule;
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
  @Rule public ActivityTestRule<MainActivity> rule = new ActivityTestRule<>(MainActivity.class);

  private String evaluate(String script) throws Exception {
    CountDownLatch ready = new CountDownLatch(1);
    String[] result = {null};
    InstrumentationRegistry.getInstrumentation()
        .runOnMainSync(
            () -> {
              WebView web =
                  rule.getActivity().getWindow().getDecorView().findViewWithTag("app-webview");
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
    File fixture = new File(rule.getActivity().getFilesDir(), "inference-fixture.gguf");
    assertTrue("CI must install its SHA-verified inference fixture", fixture.isFile());
    File model =
        new File(
            rule.getActivity().getExternalFilesDir("models"),
            "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf");
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
    assertFalse(rule.getActivity().isFinishing());
  }
}
