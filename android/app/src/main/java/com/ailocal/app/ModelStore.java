package com.ailocal.app;

import android.app.DownloadManager;
import android.content.Context;
import java.io.File;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

final class ModelStore {
  static JSONArray catalog(Context context) throws Exception {
    try (java.io.InputStream in = context.getAssets().open("models.json")) {
      java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
      byte[] buffer = new byte[8192];
      int length;
      while ((length = in.read(buffer)) != -1) out.write(buffer, 0, length);
      return new JSONArray(new String(out.toByteArray(), StandardCharsets.UTF_8));
    }
  }

  static JSONObject find(JSONArray models, String id) throws Exception {
    for (int i = 0; i < models.length(); i++)
      if (models.getJSONObject(i).getString("id").equals(id)) return models.getJSONObject(i);
    throw new java.io.IOException("Modelo desconocido");
  }

  static File file(Context context, JSONObject file) throws Exception {
    return new File(context.getExternalFilesDir("models"), file.getString("file"));
  }

  static File ready(Context context, JSONObject file) throws Exception {
    return new File(file(context, file).getPath() + ".ready");
  }

  static boolean installed(Context context, JSONObject model) throws Exception {
    JSONArray files = model.getJSONArray("files");
    for (int i = 0; i < files.length(); i++) {
      JSONObject file = files.getJSONObject(i);
      if (!ready(context, file).exists() || file(context, file).length() != file.getLong("size"))
        return false;
    }
    return true;
  }

  static void delete(Context context, JSONObject model) throws Exception {
    android.content.SharedPreferences prefs =
        context.getSharedPreferences("local", Context.MODE_PRIVATE);
    DownloadManager downloads =
        (DownloadManager) context.getSystemService(Context.DOWNLOAD_SERVICE);
    JSONArray files = model.getJSONArray("files");
    for (int i = 0; i < files.length(); i++) {
      JSONObject file = files.getJSONObject(i);
      String key = "download_" + file.getString("file");
      long task = prefs.getLong(key, -1);
      if (task != -1) downloads.remove(task);
      prefs.edit().remove(key).apply();
      file(context, file).delete();
      ready(context, file).delete();
    }
  }
}
