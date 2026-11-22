package com.ailocal.app;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.graphics.*;
import android.net.Uri;
import android.os.*;
import android.security.keystore.*;
import android.util.Base64;
import android.webkit.*;
import androidx.webkit.WebViewAssetLoader;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;
import org.json.*;

public class MainActivity extends Activity {
  private WebView web;
  private JSONArray models;
  private final ExecutorService io = Executors.newSingleThreadExecutor();
  private android.content.SharedPreferences prefs;
  private DownloadManager dm;
  private volatile String active = "", token = "";
  private volatile int activeContext = 0;
  private String pickerSessionId = "";
  private volatile boolean busy = false;
  private volatile InferenceService inferenceService;
  private boolean bound, visible;
  private final InferenceService.Listener inferenceListener =
      state -> {
        active = state.optString("active");
        activeContext = state.optInt("activeContext");
        busy = state.optBoolean("busy");
        event("inference", state);
      };
  private final ServiceConnection serviceConnection =
      new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder binder) {
          inferenceService = ((InferenceService.LocalBinder) binder).service();
          if (visible) inferenceService.listen(inferenceListener);
          snapshot();
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
          inferenceService = null;
          active = "";
          activeContext = 0;
          busy = false;
        }
      };
  private boolean destroyed = false;
  private boolean rendererLost = false;
  // Static so a crash loop is still detected across the recreated Activity instance.
  private static long lastRendererRecovery = -1;
  private String interruptedLoad = "";
  private final Handler handler = new Handler(Looper.getMainLooper());
  private long lastResourceRefresh = 0;
  private final Runnable ticker =
      new Runnable() {
        public void run() {
          if (!destroyed) {
            io.execute(
                () -> {
                  try {
                    downloads();
                    if (SystemClock.elapsedRealtime() - lastResourceRefresh >= 10000) {
                      event("resources", resourceSample());
                      lastResourceRefresh = SystemClock.elapsedRealtime();
                    }
                  } catch (Exception e) {
                    event("error", e.getMessage());
                  }
                });
            handler.postDelayed(this, 2000);
          }
        }
      };

  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    if (state != null) pickerSessionId = state.getString("pickerSessionId", "");
    prefs = getSharedPreferences("local", MODE_PRIVATE);
    dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
    recoverInterruptedLoad();
    try {
      models =
          new JSONArray(
              new String(read(getAssets().open("models.json"), 1048576), StandardCharsets.UTF_8));
    } catch (Exception e) {
      models = new JSONArray();
    }
    try {
      token = readToken();
    } catch (Exception e) {
      prefs.edit().remove("token").remove("iv").apply();
      token = "";
    }
    web = new WebView(this);
    // Insets belong on a parent ViewGroup: WebView padding does not reliably
    // move its HTML viewport or fixed-position navigation on Android 15+.
    androidx.core.view.WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
    android.widget.FrameLayout safeArea = new android.widget.FrameLayout(this);
    safeArea.setTag("safe-area");
    web.setTag("app-webview");
    safeArea.setBackgroundColor(Color.rgb(25, 24, 23));
    safeArea.addView(
        web,
        new android.widget.FrameLayout.LayoutParams(
            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
            android.view.ViewGroup.LayoutParams.MATCH_PARENT));
    androidx.core.view.ViewCompat.setOnApplyWindowInsetsListener(
        safeArea,
        (view, insets) -> {
          androidx.core.graphics.Insets bars =
              insets.getInsets(
                  androidx.core.view.WindowInsetsCompat.Type.systemBars()
                      | androidx.core.view.WindowInsetsCompat.Type.displayCutout());
          androidx.core.graphics.Insets ime =
              insets.getInsets(androidx.core.view.WindowInsetsCompat.Type.ime());
          int breathingRoom = Math.round(8 * getResources().getDisplayMetrics().density);
          view.setPadding(
              bars.left, bars.top + breathingRoom, bars.right, Math.max(bars.bottom, ime.bottom));
          return androidx.core.view.WindowInsetsCompat.CONSUMED;
        });
    setContentView(safeArea);
    androidx.core.view.ViewCompat.requestApplyInsets(safeArea);
    web.setBackgroundColor(Color.rgb(25, 24, 23));
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.getSettings().setCacheMode(WebSettings.LOAD_NO_CACHE);
    web.getSettings().setAllowFileAccess(false);
    web.getSettings().setAllowContentAccess(false);
    web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    WebViewAssetLoader loader =
        new WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
            .build();
    web.setWebViewClient(
        new WebViewClient() {
          @Override
          public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
            return loader.shouldInterceptRequest(r.getUrl());
          }

          @Override
          public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
            return true;
          }

          @Override
          public boolean onRenderProcessGone(WebView v, RenderProcessGoneDetail detail) {
            // The WebView renderer is a separate process that Android reclaims first when RAM
            // is tight, which a multi-GB model makes likely while the app is in the background.
            // Returning false would crash this whole process, taking the loaded model and the
            // response in progress with it. The inference service lives in this process, so
            // only the UI is rebuilt and then reattaches to the running job.
            android.util.Log.w("Auren", "WebView renderer gone; crashed=" + detail.didCrash());
            if (destroyed) return true;
            rendererLost = true;
            if (visible) handler.post(MainActivity.this::recoverWebView);
            return true;
          }

          @Override
          public void onPageFinished(WebView v, String u) {
            if (u.equals("https://appassets.androidplatform.net/assets/index.html"))
              io.execute(
                  () -> {
                    snapshot();
                    if (!interruptedLoad.isEmpty()) {
                      event("notice", interruptedLoad);
                      interruptedLoad = "";
                    }
                  });
          }
        });
    web.addJavascriptInterface(new Bridge(), "Native");
    web.loadUrl("https://appassets.androidplatform.net/assets/index.html");
    bound =
        bindService(new Intent(this, InferenceService.class), serviceConnection, BIND_AUTO_CREATE);
  }

  private void event(String type, Object data) {
    try {
      String js =
          "window.receive && window.receive.apply(null,"
              + new JSONArray().put(type).put(data).toString()
              + ")";
      runOnUiThread(
          () -> {
            if (!destroyed) web.evaluateJavascript(js, null);
          });
    } catch (Exception ignored) {
    }
  }

  private static byte[] read(InputStream in, int limit) throws IOException {
    try (InputStream stream = in;
        ByteArrayOutputStream out = new ByteArrayOutputStream()) {
      byte[] b = new byte[8192];
      int n;
      while ((n = stream.read(b)) != -1) {
        if (out.size() + n > limit) throw new IOException("Archivo demasiado grande");
        out.write(b, 0, n);
      }
      return out.toByteArray();
    }
  }

  private JSONObject model(String id) throws Exception {
    for (int i = 0; i < models.length(); i++)
      if (models.getJSONObject(i).getString("id").equals(id)) return models.getJSONObject(i);
    throw new IOException("Modelo desconocido");
  }

  private File file(JSONObject f) throws Exception {
    return new File(getExternalFilesDir("models"), f.getString("file"));
  }

  private File ready(JSONObject f) throws Exception {
    return new File(file(f).getPath() + ".ready");
  }

  private boolean installed(JSONObject m) throws Exception {
    JSONArray fs = m.getJSONArray("files");
    for (int i = 0; i < fs.length(); i++) {
      JSONObject f = fs.getJSONObject(i);
      if (!ready(f).exists() || file(f).length() != f.getLong("size")) return false;
    }
    return true;
  }

  private void recoverInterruptedLoad() {
    String pending = prefs.getString("pendingLoad", "");
    if (pending.isEmpty()) return;
    try {
      JSONObject attempt = new JSONObject(pending);
      int previousPid = attempt.getInt("pid");
      if (previousPid == android.os.Process.myPid()) return;
      boolean memoryExit = false;
      if (Build.VERSION.SDK_INT >= 30) {
        ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        for (android.app.ApplicationExitInfo info :
            manager.getHistoricalProcessExitReasons(getPackageName(), previousPid, 5)) {
          if (info.getReason() == android.app.ApplicationExitInfo.REASON_LOW_MEMORY)
            memoryExit = true;
        }
      }
      interruptedLoad =
          memoryExit
              ? "Android cerró la carga anterior por memoria baja. Puedes usar Q3 o un"
                  + " contexto menor."
              : "La carga anterior se interrumpió; no hay confirmación de la causa. Puedes usar"
                  + " Q3 o menos contexto.";
    } catch (Exception ignored) {
      interruptedLoad =
          "La carga anterior se interrumpió. Puedes volver a cargar el modelo con menos contexto.";
    }
    prefs.edit().remove("pendingLoad").apply();
  }

  private JSONObject resourceSample() throws Exception {
    return ResourceMonitor.sample(this)
        .put("storage", getExternalFilesDir(null).getUsableSpace() / 1073741824.0)
        .put(
            "systemDark",
            (getResources().getConfiguration().uiMode
                    & android.content.res.Configuration.UI_MODE_NIGHT_MASK)
                == android.content.res.Configuration.UI_MODE_NIGHT_YES);
  }

  private void snapshot() {
    try {
      JSONObject s =
          resourceSample()
              .put("models", models)
              .put("storage", getExternalFilesDir(null).getUsableSpace() / 1073741824.0)
              .put("connected", !token.isEmpty())
              .put("githubLogin", prefs.getString("githubLogin", ""))
              .put("active", active)
              .put("activeContext", activeContext);
      JSONArray ids = new JSONArray();
      for (int i = 0; i < models.length(); i++)
        if (installed(models.getJSONObject(i))) ids.put(models.getJSONObject(i).getString("id"));
      s.put("installed", ids);
      JSONArray usage = new JSONArray();
      for (Map.Entry<String, ?> entry : prefs.getAll().entrySet()) {
        if (entry.getKey().startsWith("usage_")) {
          try {
            usage.put(new JSONObject((String) entry.getValue()));
          } catch (Exception ignored) {
          }
        }
      }
      s.put("usage", usage);
      InferenceService service = inferenceService;
      if (service != null) s.put("inference", service.snapshot());
      event("state", s);
      if (service != null) event("inference", service.snapshot());
    } catch (Exception e) {
      event("error", e.getMessage());
    }
  }

  private void downloads() throws Exception {
    for (int i = 0; i < models.length(); i++) {
      JSONObject m = models.getJSONObject(i);
      JSONArray fs = m.getJSONArray("files");
      for (int j = 0; j < fs.length(); j++) {
        JSONObject f = fs.getJSONObject(j);
        String key = "download_" + f.getString("file");
        long id = prefs.getLong(key, -1);
        if (id == -1) continue;
        try (Cursor c = dm.query(new DownloadManager.Query().setFilterById(id))) {
          if (!c.moveToFirst()) {
            prefs.edit().remove(key).apply();
            continue;
          }
          int status = c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
          long bytes =
              c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR));
          event(
              "download",
              new JSONObject()
                  .put("id", m.getString("id"))
                  .put("file", f.getString("file"))
                  .put("bytes", bytes)
                  .put("total", f.getLong("size"))
                  .put("status", status));
          if (status == DownloadManager.STATUS_SUCCESSFUL) {
            event("notice", "Verificando SHA-256: " + m.getString("name"));
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] buf = new byte[1024 * 1024];
            int n;
            try (InputStream in = new FileInputStream(file(f))) {
              while ((n = in.read(buf)) != -1) digest.update(buf, 0, n);
            }
            StringBuilder hash = new StringBuilder();
            for (byte b : digest.digest()) hash.append(String.format("%02x", b & 255));
            if (!hash.toString().equals(f.getString("sha256"))
                || file(f).length() != f.getLong("size")) {
              dm.remove(id);
              event("error", "Descarga dañada. Vuelve a descargar el modelo.");
            } else {
              try (FileOutputStream marker = new FileOutputStream(ready(f))) {
                marker.write(hash.toString().getBytes(StandardCharsets.UTF_8));
              }
              event("notice", "Archivo verificado: " + m.getString("name"));
            }
            prefs.edit().remove(key).apply();
            snapshot();
          } else if (status == DownloadManager.STATUS_FAILED) {
            dm.remove(id);
            prefs.edit().remove(key).apply();
            event("error", "Falló la descarga. Comprueba la red y el espacio; puedes reintentar.");
            snapshot();
          }
        }
      }
    }
  }

  private void download(String id) throws Exception {
    JSONObject m = model(id);
    long needed = 0;
    JSONArray fs = m.getJSONArray("files");
    for (int i = 0; i < fs.length(); i++)
      if (!ready(fs.getJSONObject(i)).exists()) needed += fs.getJSONObject(i).getLong("size");
    if (getExternalFilesDir(null).getUsableSpace() < needed + 268435456)
      throw new IOException("No hay espacio suficiente para este modelo.");
    for (int i = 0; i < fs.length(); i++) {
      JSONObject f = fs.getJSONObject(i);
      String key = "download_" + f.getString("file");
      if (ready(f).exists() || prefs.contains(key)) continue;
      file(f).delete();
      DownloadManager.Request req =
          new DownloadManager.Request(Uri.parse(f.getString("url")))
              .setTitle("Auren · " + m.getString("name"))
              .setNotificationVisibility(
                  DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
              .setDestinationInExternalFilesDir(this, "models", f.getString("file"));
      prefs.edit().putLong(key, dm.enqueue(req)).apply();
    }
    event("notice", "Descarga iniciada. Android la mantiene aunque salgas de la app.");
  }

  private void cancelDownload(String id) throws Exception {
    JSONArray fs = model(id).getJSONArray("files");
    for (int i = 0; i < fs.length(); i++) {
      JSONObject f = fs.getJSONObject(i);
      String key = "download_" + f.getString("file");
      long task = prefs.getLong(key, -1);
      if (task != -1) dm.remove(task);
      prefs.edit().remove(key).apply();
    }
    event("notice", "Descarga cancelada");
    snapshot();
  }

  private void saveToken(String value) throws Exception {
    if (value.isEmpty()) {
      prefs.edit().remove("token").remove("iv").remove("githubLogin").apply();
      token = "";
      return;
    }
    KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
    ks.load(null);
    if (!ks.containsAlias("github")) {
      KeyGenerator gen = KeyGenerator.getInstance("AES", "AndroidKeyStore");
      gen.init(
          new KeyGenParameterSpec.Builder(
                  "github", KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
              .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
              .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
              .build());
      gen.generateKey();
    }
    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(Cipher.ENCRYPT_MODE, ks.getKey("github", null));
    prefs
        .edit()
        .putString(
            "token",
            Base64.encodeToString(
                cipher.doFinal(value.getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP))
        .putString("iv", Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP))
        .apply();
    token = value;
  }

  private String readToken() throws Exception {
    if (!prefs.contains("token")) return "";
    KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
    ks.load(null);
    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(
        Cipher.DECRYPT_MODE,
        ks.getKey("github", null),
        new GCMParameterSpec(128, Base64.decode(prefs.getString("iv", ""), Base64.NO_WRAP)));
    return new String(
        cipher.doFinal(Base64.decode(prefs.getString("token", ""), Base64.NO_WRAP)),
        StandardCharsets.UTF_8);
  }

  private Object github(String path, String method, JSONObject body, String auth) throws Exception {
    if (auth.trim().isEmpty())
      throw new IOException("Conecta tu cuenta con un token antes de abrir repositorios.");
    HttpURLConnection c =
        (HttpURLConnection) new URL("https://api.github.com" + path).openConnection();
    c.setInstanceFollowRedirects(false);
    c.setConnectTimeout(20000);
    c.setReadTimeout(30000);
    c.setRequestMethod(method);
    c.setRequestProperty("Accept", "application/vnd.github+json");
    c.setRequestProperty("X-GitHub-Api-Version", "2022-11-28");
    c.setRequestProperty("Authorization", "Bearer " + auth);
    try {
      if (body != null) {
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type", "application/json");
        try (OutputStream out = c.getOutputStream()) {
          out.write(body.toString().getBytes(StandardCharsets.UTF_8));
        }
      }
      int code = c.getResponseCode();
      if (code == 401) {
        if (auth.equals(token)) {
          saveToken("");
          snapshot();
        }
        throw new IOException(
            "GitHub no aceptó el token. Puede estar revocado o caducado; conecta uno válido.");
      }
      if (code == 403)
        throw new IOException(
            "GitHub rechazó el acceso. Revisa los repositorios autorizados y el permiso Contents:"
                + " lectura y escritura; también puede haberse alcanzado el límite de peticiones.");
      if (code < 200 || code >= 300)
        throw new IOException(
            code == 409 || code == 422
                ? "El archivo cambió en GitHub. Recárgalo antes de guardar."
                : "GitHub HTTP " + code + ". Revisa token, permisos y repositorio.");
      try (InputStream in = c.getInputStream()) {
        return new JSONTokener(new String(read(in, 3 * 1024 * 1024), StandardCharsets.UTF_8))
            .nextValue();
      }
    } finally {
      c.disconnect();
    }
  }

  private static String enc(String s) throws Exception {
    return java.net.URLEncoder.encode(s, "UTF-8").replace("+", "%20");
  }

  private static String repo(String s) throws Exception {
    if (!s.matches("[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"))
      throw new IOException("Usa propietario/repositorio");
    return s;
  }

  private static String path(String s) throws Exception {
    StringBuilder b = new StringBuilder();
    for (String segment : s.split("/")) {
      if (segment.equals("..")) throw new IOException("Ruta inválida");
      if (b.length() > 0) b.append('/');
      b.append(enc(segment));
    }
    return b.toString();
  }

  public class Bridge {
    @JavascriptInterface
    public void command(String action, String payload) {
      if (action.equals("tokenHelp")) {
        runOnUiThread(
            () -> {
              try {
                startActivity(
                    new Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse("https://github.com/settings/personal-access-tokens/new")));
              } catch (Exception e) {
                event("error", "Abre github.com/settings/personal-access-tokens en tu navegador.");
              }
            });
        return;
      }
      if (action.equals("stop")) {
        if (inferenceService != null) inferenceService.stopGeneration();
        return;
      }
      if (action.equals("image")) {
        runOnUiThread(
            () -> {
              if (busy) {
                event("error", "Espera a que termine la respuesta.");
                return;
              }
              try {
                pickerSessionId = new JSONObject(payload).optString("sessionId");
              } catch (JSONException e) {
                event("error", "No se pudo identificar el chat.");
                return;
              }
              Intent intent =
                  new Intent(Intent.ACTION_OPEN_DOCUMENT)
                      .setType("image/*")
                      .addCategory(Intent.CATEGORY_OPENABLE);
              startActivityForResult(intent, 11);
            });
        return;
      }
      if (action.equals("clearImage") || action.equals("clearImages")) {
        runOnUiThread(
            () -> {
              if (inferenceService != null) {
                inferenceService.clearImage();
                if (action.equals("clearImages")) inferenceService.clearImages();
              }
            });
        return;
      }
      if (action.equals("unload")) {
        runOnUiThread(
            () -> {
              if (inferenceService != null) inferenceService.releaseModel();
            });
        return;
      }
      if (action.equals("chat") || action.equals("load") || action.equals("delete")) {
        runOnUiThread(
            () -> {
              try {
                JSONObject request = new JSONObject(payload);
                if (action.equals("chat"))
                  request =
                      ChatContext.prepare(
                          request, !token.isEmpty(), prefs.getString("githubLogin", ""));
                InferenceService.enqueue(MainActivity.this, action, request, null, 0, 0);
                if (Build.VERSION.SDK_INT >= 33
                    && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                        != android.content.pm.PackageManager.PERMISSION_GRANTED
                    && !prefs.getBoolean("notificationAsked", false)) {
                  prefs.edit().putBoolean("notificationAsked", true).apply();
                  requestPermissions(
                      new String[] {android.Manifest.permission.POST_NOTIFICATIONS}, 12);
                }
              } catch (Exception e) {
                try {
                  event(
                      "operationError",
                      new JSONObject()
                          .put("action", action)
                          .put(
                              "message",
                              e.getMessage() == null
                                  ? "No se pudo iniciar el servicio local"
                                  : e.getMessage()));
                } catch (JSONException ignored) {
                }
                event("done", false);
              }
            });
        return;
      }
      io.execute(
          () -> {
            try {
              JSONObject p = new JSONObject(payload);
              switch (action) {
                case "appearance":
                  boolean light = p.optBoolean("light", false);
                  runOnUiThread(
                      () -> {
                        if (destroyed) return;
                        int background = light ? Color.rgb(246, 243, 237) : Color.rgb(25, 24, 23);
                        web.setBackgroundColor(background);
                        ((android.view.View) web.getParent()).setBackgroundColor(background);
                        getWindow().setStatusBarColor(background);
                        getWindow().setNavigationBarColor(background);
                        androidx.core.view.WindowInsetsControllerCompat controller =
                            androidx.core.view.WindowCompat.getInsetsController(getWindow(), web);
                        controller.setAppearanceLightStatusBars(light);
                        controller.setAppearanceLightNavigationBars(light);
                      });
                  break;
                case "state":
                  snapshot();
                  break;
                case "download":
                  download(p.getString("id"));
                  break;
                case "cancel":
                  cancelDownload(p.getString("id"));
                  break;
                case "connect":
                  {
                    String t = p.getString("token").trim();
                    JSONObject user = (JSONObject) github("/user", "GET", null, t);
                    saveToken(t);
                    prefs.edit().putString("githubLogin", user.getString("login")).apply();
                    event("notice", "Conectado como " + user.getString("login"));
                    snapshot();
                    break;
                  }
                case "disconnect":
                  saveToken("");
                  snapshot();
                  event("notice", "Token eliminado");
                  break;
                case "repos":
                  event(
                      "repos", github("/user/repos?per_page=100&sort=updated", "GET", null, token));
                  break;
                case "read":
                  {
                    String r = repo(p.getString("repo")), f = path(p.optString("path"));
                    Object result =
                        github(
                            "/repos/" + r + "/contents/" + f + "?ref=" + enc(p.getString("branch")),
                            "GET",
                            null,
                            token);
                    if (result instanceof JSONObject) {
                      JSONObject ob = (JSONObject) result;
                      if (ob.optLong("size") > 524288 || !ob.optString("encoding").equals("base64"))
                        throw new IOException(
                            "Solo se pueden editar archivos de texto de hasta 512 KB.");
                      String text =
                          StandardCharsets.UTF_8
                              .newDecoder()
                              .onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                              .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT)
                              .decode(
                                  java.nio.ByteBuffer.wrap(
                                      Base64.decode(ob.getString("content"), Base64.DEFAULT)))
                              .toString();
                      if (text.indexOf('\0') >= 0)
                        throw new IOException("No se pueden editar archivos binarios.");
                      ob.put("text", text);
                    }
                    event(
                        "file",
                        new JSONObject()
                            .put("repo", r)
                            .put("path", p.optString("path"))
                            .put("branch", p.getString("branch"))
                            .put("result", result));
                    break;
                  }
                case "write":
                  {
                    if (p.getString("message").trim().isEmpty())
                      throw new IOException("Escribe un mensaje de commit");
                    String r = repo(p.getString("repo"));
                    JSONObject body =
                        new JSONObject()
                            .put("message", p.getString("message"))
                            .put("branch", p.getString("branch"))
                            .put("sha", p.getString("sha"))
                            .put(
                                "content",
                                Base64.encodeToString(
                                    p.getString("text").getBytes(StandardCharsets.UTF_8),
                                    Base64.NO_WRAP));
                    JSONObject result =
                        (JSONObject)
                            github(
                                "/repos/" + r + "/contents/" + path(p.getString("path")),
                                "PUT",
                                body,
                                token);
                    event(
                        "saved",
                        new JSONObject()
                            .put("repo", r)
                            .put("path", p.getString("path"))
                            .put("branch", p.getString("branch"))
                            .put("sha", result.getJSONObject("content").getString("sha")));
                    break;
                  }
              }
            } catch (Exception e) {
              if (action.equals("connect")
                  || action.equals("disconnect")
                  || action.equals("repos")
                  || action.equals("read")
                  || action.equals("write")) {
                try {
                  event(
                      "githubError",
                      new JSONObject().put("action", action).put("message", e.getMessage()));
                } catch (JSONException ignored) {
                }
              } else event("error", e.getMessage());
            }
          });
    }
  }

  @Override
  protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request != 11) return;
    if (result != RESULT_OK || data == null) {
      if (inferenceService != null)
        event("image", inferenceService.snapshot().optJSONObject("selectedImage"));
      return;
    }
    Uri uri = data.getData();
    if (uri == null) {
      event("error", "No se recibió la imagen seleccionada.");
      return;
    }
    try {
      event("image", new JSONObject().put("status", "loading").put("sessionId", pickerSessionId));
      try {
        getContentResolver()
            .takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
      } catch (SecurityException ignored) {
      }
      JSONObject requestData =
          new JSONObject().put("uri", uri.toString()).put("sessionId", pickerSessionId);
      InferenceService.enqueue(this, "prepareImage", requestData, null, 0, 0);
    } catch (Exception e) {
      try {
        event(
            "image",
            new JSONObject()
                .put("status", "error")
                .put("sessionId", pickerSessionId)
                .put("error", "No se pudo adjuntar la imagen: " + e.getMessage()));
      } catch (Exception ignored) {
      }
      event("error", "No se pudo adjuntar la imagen: " + e.getMessage());
    }
  }

  @Override
  protected void onSaveInstanceState(Bundle out) {
    out.putString("pickerSessionId", pickerSessionId);
    super.onSaveInstanceState(out);
  }

  @Override
  public void onConfigurationChanged(android.content.res.Configuration configuration) {
    super.onConfigurationChanged(configuration);
    event(
        "systemTheme",
        (configuration.uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK)
            == android.content.res.Configuration.UI_MODE_NIGHT_YES);
  }

  @Override
  public void onBackPressed() {
    if (destroyed) return;
    web.evaluateJavascript(
        "typeof window.handleBack === 'function' && window.handleBack()",
        handled -> {
          if (destroyed || "true".equals(handled)) return;
          new AlertDialog.Builder(this)
              .setMessage("¿Salir de Auren?")
              .setPositiveButton("Salir", (d, w) -> finish())
              .setNegativeButton("Continuar", null)
              .show();
        });
  }

  /** Rebuilds the UI after the WebView renderer was killed; the model and any job keep running. */
  private void recoverWebView() {
    if (destroyed || !rendererLost) return;
    rendererLost = false;
    long now = SystemClock.elapsedRealtime();
    boolean looping = lastRendererRecovery >= 0 && now - lastRendererRecovery < 10000;
    lastRendererRecovery = now;
    // A second loss right after recovering means recreating will not help: leave the
    // service running and let the next launch start from a clean WebView.
    if (looping) finish();
    else recreate();
  }

  @Override
  protected void onStart() {
    super.onStart();
    visible = true;
    if (rendererLost) handler.post(this::recoverWebView);
    handler.post(ticker);
    if (inferenceService != null) inferenceService.listen(inferenceListener);
  }

  @Override
  protected void onStop() {
    visible = false;
    handler.removeCallbacks(ticker);
    if (inferenceService != null) inferenceService.unlisten(inferenceListener);
    super.onStop();
  }

  @Override
  protected void onDestroy() {
    destroyed = true;
    handler.removeCallbacks(ticker);
    if (inferenceService != null) inferenceService.unlisten(inferenceListener);
    if (bound) {
      unbindService(serviceConnection);
      bound = false;
    }
    inferenceService = null;
    io.shutdown();
    web.destroy();
    super.onDestroy();
  }
}
