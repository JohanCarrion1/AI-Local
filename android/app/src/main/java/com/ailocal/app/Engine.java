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

  static native void loadNative(
      String model, String projector, int threads, int context, Progress progress);

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

  static native void generateNative(
      String[] roles,
      String[] messages,
      byte[] rgb,
      int width,
      int height,
      int maxTokens,
      Sink sink,
      Progress progress);

  static native String stats();

  static native void stop();

  static native void unload();
}
