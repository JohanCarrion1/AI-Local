package com.ailocal.app;

final class Engine {
  static {
    System.loadLibrary("ailocal");
  }

  interface Sink {
    void onToken(byte[] text);
  }

  interface Progress {
    void onProgress(String phase, int current, int total);
  }

  static void load(String model, String projector, int threads, int context) {
    loadNative(model, projector, threads, context, null);
  }

  static native void configureBackends(String directory);

  static void loadNative(
      String model, String projector, int threads, int context, Progress progress) {
    loadConfigured(model, projector, threads, context, 256, progress);
  }

  static native void loadConfigured(
      String model, String projector, int threads, int context, int imageTokens, Progress progress);

  static void generate(
      String[] roles,
      String[] messages,
      byte[] rgb,
      int width,
      int height,
      int maxTokens,
      Sink sink) {
    generateNative(roles, messages, rgb, width, height, maxTokens, sink, null);
  }

  static void generateNative(
      String[] roles,
      String[] messages,
      byte[] rgb,
      int width,
      int height,
      int maxTokens,
      Sink sink,
      Progress progress) {
    generateImage(
        roles,
        messages,
        rgb,
        width,
        height,
        maxTokens,
        sink,
        progress,
        rgb == null ? -1 : messages.length - 1,
        true);
  }

  static native void generateImage(
      String[] roles,
      String[] messages,
      byte[] rgb,
      int width,
      int height,
      int maxTokens,
      Sink sink,
      Progress progress,
      int imageIndex,
      boolean allowHistoryWindow);

  static native String stats();

  static native void stop();

  /** Text appended after the chat template, e.g. a closed think block to skip reasoning. */
  static native void setGenerationPrefix(String prefix);

  static native void unload();
}
