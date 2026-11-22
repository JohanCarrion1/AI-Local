package com.ailocal.app;

import static androidx.test.espresso.intent.matcher.IntentMatchers.hasAction;
import static org.junit.Assert.*;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.*;
import android.graphics.*;
import android.net.Uri;
import android.provider.MediaStore;
import android.webkit.WebView;
import androidx.test.espresso.intent.Intents;
import androidx.test.ext.junit.rules.ActivityScenarioRule;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.*;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;

/** Production picker-result, private photo store, service, JNI, and real visual model. */
@RunWith(AndroidJUnit4.class)
public class VisionPhotoTest {
  @Rule
  public ActivityScenarioRule<MainActivity> rule = new ActivityScenarioRule<>(MainActivity.class);

  private String evaluate(String js) throws Exception {
    CountDownLatch done = new CountDownLatch(1);
    String[] result = {null};
    rule.getScenario()
        .onActivity(
            activity -> {
              WebView web = activity.getWindow().getDecorView().findViewWithTag("app-webview");
              web.evaluateJavascript(
                  js,
                  value -> {
                    result[0] = value;
                    done.countDown();
                  });
            });
    assertTrue(done.await(15, TimeUnit.SECONDS));
    return result[0];
  }

  private void await(String js, int seconds) throws Exception {
    long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(seconds);
    while (System.nanoTime() < until) {
      if ("true".equals(evaluate(js))) return;
      Thread.sleep(200);
    }
    fail(js + "\n" + evaluate("document.body.innerText"));
  }

  private Uri photo(int color) throws Exception {
    Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
    ContentValues values = new ContentValues();
    values.put(MediaStore.Images.Media.DISPLAY_NAME, "auren-fixture.png");
    values.put(MediaStore.Images.Media.MIME_TYPE, "image/png");
    Uri uri =
        context.getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
    assertNotNull(uri);
    Bitmap image = Bitmap.createBitmap(224, 224, Bitmap.Config.ARGB_8888);
    image.eraseColor(color);
    try (OutputStream out = context.getContentResolver().openOutputStream(uri)) {
      assertTrue(image.compress(Bitmap.CompressFormat.PNG, 100, out));
    }
    image.recycle();
    return uri;
  }

  private void select(Uri uri) throws Exception {
    Intents.intending(hasAction(Intent.ACTION_OPEN_DOCUMENT))
        .respondWith(
            new Instrumentation.ActivityResult(
                Activity.RESULT_OK,
                new Intent().setData(uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)));
    evaluate("document.getElementById('attach').click()");
    await("!!attachment && attachment.status==='ready' && !imagePreparing", 30);
    assertEquals("true", evaluate("document.getElementById('attachmentPreview').naturalWidth>0"));
  }

  private void ask() throws Exception {
    evaluate(
        "document.getElementById('prompt').value='What is the dominant color in this"
            + " picture?';document.getElementById('send').click()");
    await("!running && messages.some(m=>m.role==='assistant')", 150);
    assertEquals("false", evaluate("!!chatFailure"));
    assertEquals("true", evaluate("state.inference.job.metrics.imageProcessed"));
    assertEquals("1", evaluate("document.querySelectorAll('.message-photo img').length"));
  }

  @Test
  public void photoSurvivesRecreationAndDifferentPixelsProduceDifferentAnswers() throws Exception {
    Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
    JSONArray catalog = ModelStore.catalog(context);
    JSONObject model = ModelStore.find(catalog, "smol");
    for (int i = 0; i < 2; i++) {
      JSONObject info = model.getJSONArray("files").getJSONObject(i);
      Files.copy(
          new File(context.getFilesDir(), "smol-" + i + ".gguf").toPath(),
          ModelStore.file(context, info).toPath(),
          StandardCopyOption.REPLACE_EXISTING);
      Files.write(
          ModelStore.ready(context, info).toPath(),
          "SHA-verified CI fixture".getBytes(StandardCharsets.UTF_8));
    }
    await("typeof window.receive==='function'", 30);
    evaluate("Native.command('state','{}')");
    await("state.installed.includes('smol')", 30);
    evaluate("page('chat');newConversation();beginLoad(state.models.find(m=>m.id==='smol'))");
    await("!running && state.active==='smol'", 120);
    Uri red = photo(Color.RED), blue = photo(Color.BLUE);
    Intents.init();
    try {
      select(red);
      String id = evaluate("attachment.id");
      rule.getScenario().recreate();
      await(
          "typeof window.receive==='function' && !!attachment && attachment.status==='ready'", 30);
      assertEquals(id, evaluate("attachment.id"));
      ask();
      assertEquals("true", evaluate("/red|rojo/i.test(messages.at(-1).content)"));
      evaluate(
          "document.getElementById('prompt').value='What color was that"
              + " picture?';document.getElementById('send').click()");
      await("!running && messages.filter(m=>m.role==='assistant').length===2", 120);
      assertEquals("true", evaluate("state.inference.job.metrics.imageReused"));
      evaluate("newConversation()");
      select(blue);
      ask();
      assertEquals("true", evaluate("/blue|azul/i.test(messages.at(-1).content)"));
      assertEquals("false", evaluate("state.inference.job.metrics.imageReused"));
    } finally {
      Intents.release();
      context.getContentResolver().delete(red, null, null);
      context.getContentResolver().delete(blue, null, null);
      evaluate("Native.command('unload','{}')");
    }
  }
}
