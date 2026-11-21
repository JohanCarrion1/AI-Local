package com.ailocal.app;

import static org.junit.Assert.*;

import android.content.pm.ActivityInfo;
import android.view.View;
import android.webkit.WebView;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.rule.ActivityTestRule;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class SafeAreaTest {
  @Rule public ActivityTestRule<MainActivity> rule = new ActivityTestRule<>(MainActivity.class);

  private void assertSafeViewport() throws Exception {
    InstrumentationRegistry.getInstrumentation().waitForIdleSync();
    CountDownLatch checked = new CountDownLatch(1);
    final Throwable[] failure = {null};
    rule.getActivity()
        .runOnUiThread(
            () -> {
              try {
                View decor = rule.getActivity().getWindow().getDecorView();
                View safeArea = decor.findViewWithTag("safe-area");
                WebView web = decor.findViewWithTag("app-webview");
                assertNotNull(safeArea);
                assertNotNull(web);
                WindowInsetsCompat window = ViewCompat.getRootWindowInsets(safeArea);
                assertNotNull(window);
                Insets bars =
                    window.getInsets(
                        WindowInsetsCompat.Type.systemBars()
                            | WindowInsetsCompat.Type.displayCutout());
                int[] origin = new int[2], position = new int[2];
                decor.getLocationOnScreen(origin);
                web.getLocationOnScreen(position);
                int breathing = Math.round(8 * web.getResources().getDisplayMetrics().density);
                assertTrue(
                    "HTML viewport must start below status bar/cutout",
                    position[1] - origin[1] >= bars.top + breathing);
                assertTrue(
                    "HTML viewport must end above navigation bar",
                    position[1] + web.getHeight() <= origin[1] + decor.getHeight() - bars.bottom);
                assertTrue(position[0] - origin[0] >= bars.left);
                assertTrue(
                    position[0] + web.getWidth() <= origin[0] + decor.getWidth() - bars.right);
                // The reservation must be on a native parent, never WebView padding.
                assertEquals(0, web.getPaddingTop());
                assertEquals(0, web.getPaddingBottom());
              } catch (Throwable error) {
                failure[0] = error;
              } finally {
                checked.countDown();
              }
            });
    assertTrue(checked.await(15, TimeUnit.SECONDS));
    if (failure[0] != null) throw new AssertionError(failure[0]);
  }

  @Test
  public void portraitStaysOutsideSystemBars() throws Exception {
    Thread.sleep(1200);
    assertSafeViewport();
  }

  @Test
  public void landscapeReappliesSystemInsets() throws Exception {
    rule.getActivity()
        .runOnUiThread(
            () ->
                rule.getActivity()
                    .setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE));
    Thread.sleep(1600);
    assertSafeViewport();
  }

  @Test
  public void keyboardInsetsShrinkNativeParentViewport() throws Exception {
    Thread.sleep(1200);
    InstrumentationRegistry.getInstrumentation()
        .runOnMainSync(
            () -> {
              View safe =
                  rule.getActivity().getWindow().getDecorView().findViewWithTag("safe-area");
              WindowInsetsCompat synthetic =
                  new WindowInsetsCompat.Builder()
                      .setInsets(WindowInsetsCompat.Type.statusBars(), Insets.of(0, 48, 0, 0))
                      .setInsets(WindowInsetsCompat.Type.navigationBars(), Insets.of(0, 0, 0, 72))
                      .setInsets(WindowInsetsCompat.Type.ime(), Insets.of(0, 0, 0, 300))
                      .setVisible(WindowInsetsCompat.Type.ime(), true)
                      .build();
              ViewCompat.dispatchApplyWindowInsets(safe, synthetic);
              assertEquals(300, safe.getPaddingBottom());
              assertTrue(safe.getPaddingTop() > 48);
              WebView web = safe.findViewWithTag("app-webview");
              assertEquals(0, web.getPaddingBottom());
            });
  }
}
