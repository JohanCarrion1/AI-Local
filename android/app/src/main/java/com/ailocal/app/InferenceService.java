package com.ailocal.app;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.os.*;
import android.util.AtomicFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.*;
import org.json.*;

/** Owns the model and inference independently of any Activity or WebView. */
public class InferenceService extends Service {
  static final String STOP = "com.ailocal.app.STOP_GENERATION";
  static final String RELEASE = "com.ailocal.app.RELEASE_MODEL";
  private static final String CHANNEL = "local-inference";
  private static final int NOTIFICATION = 17;
  private static final ConcurrentLinkedQueue<Input> inputs = new ConcurrentLinkedQueue<>();

  private static final class Input {
    final String action;
    final JSONObject request;
    final byte[] image;
    final int width, height;

    Input(String a, JSONObject r, byte[] i, int w, int h) {
      action = a;
      request = r;
      image = i;
      width = w;
      height = h;
    }
  }

  static void enqueue(
      Context context, String action, JSONObject request, byte[] image, int width, int height) {
    Input input = new Input(action, request, image, width, height);
    inputs.add(input);
    try {
      context
          .getApplicationContext()
          .startForegroundService(new Intent(context, InferenceService.class));
    } catch (RuntimeException e) {
      inputs.remove(input);
      throw e;
    }
  }

  interface Listener {
    void changed(JSONObject state);
  }

  public final class LocalBinder extends Binder {
    InferenceService service() {
      return InferenceService.this;
    }
  }

  private final LocalBinder binder = new LocalBinder();
  // JNI state is process-wide; old service teardown must precede a new load.
  private static final ExecutorService worker = Executors.newSingleThreadExecutor();
  private final CopyOnWriteArraySet<Listener> listeners = new CopyOnWriteArraySet<>();
  private final Object lock = new Object();
  private final String instanceId = UUID.randomUUID().toString();
  private long revision;
  private final Handler main = new Handler(Looper.getMainLooper());
  private JSONArray models;
  private JSONObject job = new JSONObject();
  private JSONObject rejection = new JSONObject();
  private volatile String active = "";
  private volatile int activeContext;
  private volatile boolean busy;
  private volatile boolean foreground;
  private volatile boolean closing;
  private volatile boolean releasing;
  private AtomicFile journal;
  private PowerManager.WakeLock wake;
  private long lastDisk, lastNotification;

  @Override
  public void onCreate() {
    super.onCreate();
    try {
      models = ModelStore.catalog(this);
    } catch (Exception e) {
      models = new JSONArray();
    }
    journal = new AtomicFile(new File(getFilesDir(), "inference-session.json"));
    try {
      job = new JSONObject(new String(journal.readFully(), StandardCharsets.UTF_8));
      if ("running".equals(job.optString("status"))) {
        set("status", "interrupted");
        set("error", "Android interrumpió la ejecución anterior. Puedes reintentar tu mensaje.");
      }
    } catch (Exception ignored) {
      job = new JSONObject();
    }
    NotificationChannel channel =
        new NotificationChannel(
            CHANNEL, "IA en tu dispositivo", NotificationManager.IMPORTANCE_LOW);
    channel.setDescription("Mantiene el modelo local y las respuestas al cambiar de aplicación.");
    getSystemService(NotificationManager.class).createNotificationChannel(channel);
    wake =
        ((PowerManager) getSystemService(POWER_SERVICE))
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AI-Local:inference");
    wake.setReferenceCounted(false);
  }

  @Override
  public IBinder onBind(Intent intent) {
    return binder;
  }

  @Override
  public int onStartCommand(Intent intent, int flags, int startId) {
    if (intent != null && RELEASE.equals(intent.getAction())) releaseModel();
    else if (intent != null && STOP.equals(intent.getAction())) stopGeneration();
    else {
      promote();
      Input input;
      while ((input = inputs.poll()) != null) {
        try {
          submit(input.action, input.request, input.image, input.width, input.height);
        } catch (RuntimeException e) {
          try {
            synchronized (lock) {
              rejection =
                  new JSONObject()
                      .put("id", input.request.optString("requestId"))
                      .put("action", input.action)
                      .put("message", e.getMessage());
            }
          } catch (JSONException ignored) {
          }
          publish(false);
        }
      }
    }
    // Never restart a multi-GB model unattended after a system/force stop.
    return START_NOT_STICKY;
  }

  void listen(Listener listener) {
    listeners.add(listener);
    listener.changed(snapshot());
  }

  void unlisten(Listener listener) {
    listeners.remove(listener);
  }

  String activeModel() {
    return active;
  }

  int contextSize() {
    return activeContext;
  }

  boolean isBusy() {
    return busy;
  }

  JSONObject snapshot() {
    synchronized (lock) {
      try {
        return new JSONObject()
            .put("active", active)
            .put("instanceId", instanceId)
            .put("revision", revision)
            .put("activeContext", activeContext)
            .put("busy", busy || releasing)
            .put("releasing", releasing)
            .put("foreground", foreground)
            .put("wakeHeld", wake != null && wake.isHeld())
            .put("job", new JSONObject(job.toString()))
            .put("rejection", new JSONObject(rejection.toString()));
      } catch (JSONException e) {
        throw new IllegalStateException(e);
      }
    }
  }

  private void set(String name, Object value) {
    synchronized (lock) {
      try {
        job.put(name, value);
      } catch (JSONException e) {
        throw new IllegalStateException(e);
      }
    }
  }

  private void publish(boolean durable) {
    synchronized (lock) {
      revision++;
    }
    long now = SystemClock.elapsedRealtime();
    if (durable || now - lastDisk >= 1000) {
      FileOutputStream out = null;
      try {
        byte[] bytes;
        synchronized (lock) {
          bytes = job.toString().getBytes(StandardCharsets.UTF_8);
        }
        out = journal.startWrite();
        out.write(bytes);
        journal.finishWrite(out);
        lastDisk = now;
      } catch (Exception e) {
        if (out != null) journal.failWrite(out);
      }
    }
    if (foreground && (durable || now - lastNotification >= 1000)) {
      if (Build.VERSION.SDK_INT < 33
          || checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
              == android.content.pm.PackageManager.PERMISSION_GRANTED)
        getSystemService(NotificationManager.class).notify(NOTIFICATION, notification());
      lastNotification = now;
    }
    if (!listeners.isEmpty()) {
      JSONObject state = snapshot();
      for (Listener listener : listeners) listener.changed(state);
    }
  }

  private Notification notification() {
    PendingIntent open =
        PendingIntent.getActivity(
            this,
            0,
            new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    String action, phase, status, modelName;
    synchronized (lock) {
      action = job.optString("action");
      status = job.optString("status");
      JSONObject progress = job.optJSONObject("progress");
      phase = progress == null ? "" : progress.optString("phase");
      modelName = job.optString("modelName", "AI Local");
    }
    String text =
        busy
            ? (action.equals("load")
                ? "Cargando modelo…"
                : phase.equals("prompt")
                    ? "Preparando tu mensaje…"
                    : "Generando respuesta en segundo plano…")
            : status.equals("error") || status.equals("interrupted")
                ? "Abre el chat para revisar la ejecución."
                : "Modelo listo · puedes volver al chat.";
    Notification.Builder notification =
        new Notification.Builder(this, CHANNEL)
            .setSmallIcon(com.ailocal.app.R.drawable.ic_launcher)
            .setContentTitle("AI Local · " + modelName)
            .setContentText(text)
            .setContentIntent(open)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .setCategory(Notification.CATEGORY_SERVICE);
    if (Build.VERSION.SDK_INT >= 31)
      notification.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE);
    if (busy)
      notification.addAction(
          new Notification.Action.Builder(0, "Detener", serviceAction(STOP, 1)).build());
    notification.addAction(
        new Notification.Action.Builder(0, "Liberar memoria", serviceAction(RELEASE, 2)).build());
    return notification.build();
  }

  private PendingIntent serviceAction(String action, int request) {
    return PendingIntent.getService(
        this,
        request,
        new Intent(this, InferenceService.class).setAction(action),
        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
  }

  private void promote() {
    if (Build.VERSION.SDK_INT >= 34)
      startForeground(
          NOTIFICATION, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
    else startForeground(NOTIFICATION, notification());
    foreground = true;
  }

  private final Runnable renewWake =
      new Runnable() {
        @Override
        public void run() {
          synchronized (wake) {
            if (busy && !closing) {
              wake.acquire(TimeUnit.MINUTES.toMillis(30));
              main.postDelayed(this, TimeUnit.MINUTES.toMillis(5));
            }
          }
        }
      };

  private void holdCpu() {
    wake.acquire(TimeUnit.MINUTES.toMillis(30));
    main.postDelayed(renewWake, TimeUnit.MINUTES.toMillis(5));
  }

  private void releaseCpu() {
    main.removeCallbacks(renewWake);
    synchronized (wake) {
      if (wake.isHeld()) wake.release();
    }
  }

  void stopGeneration() {
    if (busy) Engine.stop();
  }

  void releaseModel() {
    if (releasing) return;
    releasing = true;
    stopGeneration();
    worker.execute(
        () -> {
          Engine.unload();
          active = "";
          activeContext = 0;
          foreground = false;
          stopForeground(STOP_FOREGROUND_REMOVE);
          stopSelf();
          releasing = false;
          publish(true);
        });
  }

  void submit(String action, JSONObject request, byte[] image, int width, int height) {
    if (busy || releasing)
      throw new IllegalStateException("Hay una operación del modelo en curso.");
    promote();
    synchronized (lock) {
      if (busy) throw new IllegalStateException("Hay una operación del modelo en curso.");
      busy = true;
      job = new JSONObject();
      set("id", request.optString("requestId", UUID.randomUUID().toString()));
      set("sessionId", request.optString("sessionId"));
      set("action", action);
      set("modelId", request.optString("id", active));
      set("status", "running");
      set("startedAt", System.currentTimeMillis());
      set("answer", "");
    }
    worker.execute(
        () -> {
          try {
            holdCpu();
            publish(true);
            if (action.equals("load")) load(request);
            else if (action.equals("chat")) generate(request, image, width, height);
            else if (action.equals("delete")) delete(request);
            else throw new IOException("Operación del modelo desconocida");
            set("status", "success");
          } catch (Throwable e) {
            if (action.equals("load")) {
              Engine.unload();
              active = "";
              activeContext = 0;
            }
            set("status", "error");
            set("error", e.getMessage() == null ? "Error del motor local" : e.getMessage());
          } finally {
            busy = false;
            releaseCpu();
            publish(true);
            if (active.isEmpty()) {
              foreground = false;
              stopForeground(STOP_FOREGROUND_REMOVE);
              stopSelf();
            }
          }
        });
  }

  private void progress(String phase, int current, int total) {
    try {
      set(
          "progress",
          new JSONObject().put("phase", phase).put("current", current).put("total", total));
      publish(false);
    } catch (JSONException e) {
      throw new IllegalStateException(e);
    }
  }

  private void load(JSONObject request) throws Exception {
    JSONObject model = ModelStore.find(models, request.getString("id"));
    if (!ModelStore.installed(this, model))
      throw new IOException("Primero descarga el modelo completo.");
    active = "";
    activeContext = 0;
    Engine.unload();
    set("modelName", model.getString("name"));
    int context =
        Math.max(
            model.getBoolean("vision") ? 2048 : 512,
            Math.min(4096, request.optInt("context", 1024)));
    JSONArray files = model.getJSONArray("files");
    Engine.loadNative(
        ModelStore.file(this, files.getJSONObject(0)).getPath(),
        model.getBoolean("vision") ? ModelStore.file(this, files.getJSONObject(1)).getPath() : "",
        Math.max(1, Math.min(4, Runtime.getRuntime().availableProcessors() - 1)),
        context,
        this::progress);
    active = model.getString("id");
    activeContext = context;
  }

  private void delete(JSONObject request) throws Exception {
    JSONObject model = ModelStore.find(models, request.getString("id"));
    if (active.equals(model.getString("id"))) {
      Engine.unload();
      active = "";
      activeContext = 0;
    }
    ModelStore.delete(this, model);
  }

  private void generate(JSONObject request, byte[] image, int width, int height) throws Exception {
    if (active.isEmpty()) throw new IOException("Carga un modelo para conversar.");
    set("modelName", ModelStore.find(models, active).getString("name"));
    JSONArray history = request.getJSONArray("messages");
    if (history.length() > 40 || history.length() == 0)
      throw new IOException("Inicia una conversación nueva.");
    String[] roles = new String[history.length()], texts = new String[history.length()];
    for (int i = 0; i < history.length(); i++) {
      roles[i] = history.getJSONObject(i).getString("role");
      texts[i] = history.getJSONObject(i).getString("content");
    }
    ByteArrayOutputStream output = new ByteArrayOutputStream();
    long[] lastEmission = {0}, lastPss = {0};
    double[] peakPss = {android.os.Debug.getPss() / 1024.0};
    try {
      Engine.generateNative(
          roles,
          texts,
          image,
          width,
          height,
          Math.max(1, Math.min(2048, request.optInt("maxTokens", 512))),
          bytes -> {
            output.write(bytes, 0, bytes.length);
            long now = SystemClock.elapsedRealtime();
            if (now - lastPss[0] >= 2000) {
              peakPss[0] = Math.max(peakPss[0], android.os.Debug.getPss() / 1024.0);
              lastPss[0] = now;
            }
            if (now - lastEmission[0] >= (listeners.isEmpty() ? 333 : 50)) {
              set("answer", new String(output.toByteArray(), StandardCharsets.UTF_8));
              publish(false);
              lastEmission[0] = now;
            }
          },
          this::progress);
    } finally {
      set("answer", new String(output.toByteArray(), StandardCharsets.UTF_8));
    }
    JSONObject measured = new JSONObject(Engine.stats());
    if (output.toString(StandardCharsets.UTF_8.name()).trim().isEmpty()
        && !measured.optBoolean("cancelled"))
      throw new IOException("El modelo terminó sin devolver texto. Puedes reintentar el mensaje.");
    int tokens = measured.getInt("generatedTokens");
    JSONObject metrics =
        new JSONObject()
            .put("id", active)
            .put("context", measured.getInt("context"))
            .put("compactKv", measured.getBoolean("compactKv"))
            .put("tokens", tokens)
            .put("generationMs", measured.getDouble("generationMs"))
            .put("tps", tokens * 1000.0 / Math.max(1, measured.getDouble("generationMs")))
            .put("peakPssMiB", Math.max(peakPss[0], android.os.Debug.getPss() / 1024.0))
            .put("cachedTokens", measured.optInt("cachedTokens"))
            .put("stopped", measured.optBoolean("cancelled"));
    set("metrics", metrics);
    getSharedPreferences("local", MODE_PRIVATE)
        .edit()
        .putString("usage_" + active + "_" + activeContext, metrics.toString())
        .apply();
  }

  @Override
  public void onDestroy() {
    closing = true;
    foreground = false;
    Engine.stop();
    releaseCpu();
    listeners.clear();
    worker.execute(Engine::unload);
    super.onDestroy();
  }
}
