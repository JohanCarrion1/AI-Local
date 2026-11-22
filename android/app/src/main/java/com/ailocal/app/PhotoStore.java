package com.ailocal.app;

import android.content.Context;
import android.database.Cursor;
import android.graphics.*;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.util.Base64;
import androidx.exifinterface.media.ExifInterface;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import org.json.JSONObject;

/** Private, bounded photo copies survive Activity recreation; URIs never go to the model. */
final class PhotoStore {
  static final class Pixels {
    final byte[] rgb;
    final int width, height;

    Pixels(byte[] data, int w, int h) {
      rgb = data;
      width = w;
      height = h;
    }
  }

  private static File directory(Context context) {
    File dir = new File(context.getFilesDir(), "chat-images");
    dir.mkdirs();
    return dir;
  }

  private static File file(Context context, String id, String suffix) throws IOException {
    if (!id.matches("[a-fA-F0-9-]{36}")) throw new IOException("Identificador de imagen inválido.");
    return new File(directory(context), id + suffix);
  }

  static JSONObject importPhoto(Context context, Uri uri, String session) throws Exception {
    BitmapFactory.Options options = new BitmapFactory.Options();
    options.inJustDecodeBounds = true;
    try (InputStream in = context.getContentResolver().openInputStream(uri)) {
      BitmapFactory.decodeStream(in, null, options);
    }
    if (options.outWidth <= 0 || options.outHeight <= 0)
      throw new IOException("No se pudo leer la foto. Elige una imagen JPEG, PNG o WebP.");
    int sample = 1;
    while (Math.max(options.outWidth, options.outHeight) / sample > 1536) sample *= 2;
    options.inJustDecodeBounds = false;
    options.inSampleSize = sample;
    options.inPreferredConfig = Bitmap.Config.ARGB_8888;
    Bitmap decoded;
    try (InputStream in = context.getContentResolver().openInputStream(uri)) {
      decoded = BitmapFactory.decodeStream(in, null, options);
    }
    if (decoded == null) throw new IOException("No se pudo decodificar la imagen.");
    Matrix matrix = new Matrix();
    try (InputStream in = context.getContentResolver().openInputStream(uri)) {
      ExifInterface exif = new ExifInterface(in);
      if (exif.isFlipped()) matrix.postScale(-1, 1);
      matrix.postRotate(exif.getRotationDegrees());
    } catch (IOException ignored) {
    }
    Bitmap oriented =
        Bitmap.createBitmap(decoded, 0, 0, decoded.getWidth(), decoded.getHeight(), matrix, true);
    if (oriented != decoded) decoded.recycle();
    float scale = Math.min(1f, 1024f / Math.max(oriented.getWidth(), oriented.getHeight()));
    Bitmap image =
        Bitmap.createScaledBitmap(
            oriented,
            Math.max(1, Math.round(oriented.getWidth() * scale)),
            Math.max(1, Math.round(oriented.getHeight() * scale)),
            true);
    if (image != oriented) oriented.recycle();
    String id = UUID.randomUUID().toString(), name = "Imagen";
    try (Cursor cursor =
        context
            .getContentResolver()
            .query(uri, new String[] {OpenableColumns.DISPLAY_NAME}, null, null, null)) {
      if (cursor != null && cursor.moveToFirst()) name = cursor.getString(0);
    } catch (Exception ignored) {
    }
    if (name == null) name = "Imagen";
    if (name.length() > 100) name = name.substring(0, 100);
    float small = Math.min(1f, 128f / Math.max(image.getWidth(), image.getHeight()));
    Bitmap thumb =
        Bitmap.createScaledBitmap(
            image,
            Math.max(1, Math.round(image.getWidth() * small)),
            Math.max(1, Math.round(image.getHeight() * small)),
            true);
    ByteArrayOutputStream preview = new ByteArrayOutputStream();
    thumb.compress(Bitmap.CompressFormat.JPEG, 80, preview);
    JSONObject metadata =
        new JSONObject()
            .put("id", id)
            .put("sessionId", session)
            .put("status", "ready")
            .put("name", name)
            .put("width", image.getWidth())
            .put("height", image.getHeight())
            .put(
                "thumbnail",
                "data:image/jpeg;base64,"
                    + Base64.encodeToString(preview.toByteArray(), Base64.NO_WRAP));
    try (FileOutputStream out = new FileOutputStream(file(context, id, ".jpg"))) {
      image.compress(Bitmap.CompressFormat.JPEG, 92, out);
    }
    Files.write(
        file(context, id, ".json").toPath(), metadata.toString().getBytes(StandardCharsets.UTF_8));
    if (thumb != image) thumb.recycle();
    image.recycle();
    File[] stored = directory(context).listFiles((dir, f) -> f.endsWith(".json"));
    if (stored != null && stored.length > 24) {
      Arrays.sort(stored, Comparator.comparingLong(File::lastModified));
      for (int i = 0; i < stored.length - 24; i++) {
        String old = stored[i].getName().replace(".json", "");
        stored[i].delete();
        file(context, old, ".jpg").delete();
      }
    }
    return metadata;
  }

  static JSONObject metadata(Context context, String id, String session) throws Exception {
    File stored = file(context, id, ".json");
    if (!stored.exists())
      throw new IOException("La foto ya no está disponible. Vuelve a adjuntarla antes de enviar.");
    JSONObject result =
        new JSONObject(new String(Files.readAllBytes(stored.toPath()), StandardCharsets.UTF_8));
    if (!session.equals(result.optString("sessionId")))
      throw new IOException(
          "La imagen pertenece a otro chat. Adjunta la foto en esta conversación.");
    return result;
  }

  static Pixels pixels(Context context, String id, String session) throws Exception {
    metadata(context, id, session);
    Bitmap image = BitmapFactory.decodeFile(file(context, id, ".jpg").getPath());
    if (image == null) throw new IOException("No se pudo recuperar la foto. Vuelve a adjuntarla.");
    int width = image.getWidth(), height = image.getHeight();
    int[] pixels = new int[width * height];
    image.getPixels(pixels, 0, width, 0, 0, width, height);
    image.recycle();
    byte[] rgb = new byte[pixels.length * 3];
    for (int i = 0; i < pixels.length; i++) {
      rgb[3 * i] = (byte) (pixels[i] >> 16);
      rgb[3 * i + 1] = (byte) (pixels[i] >> 8);
      rgb[3 * i + 2] = (byte) pixels[i];
    }
    return new Pixels(rgb, width, height);
  }

  static void clear(Context context) {
    File[] all = directory(context).listFiles();
    if (all != null) for (File file : all) file.delete();
  }
}
