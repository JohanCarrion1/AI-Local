package com.ailocal.app;

final class Engine {
  static {
    System.loadLibrary("ailocal");
  }

  interface Sink {
    void onToken(byte[] text);
  }

  static native void load(String model, String projector, int threads, int context);

  static native void generate(
      String[] roles,
      String[] messages,
      byte[] rgb,
      int width,
      int height,
      int maxTokens,
      Sink sink);

  static native String stats();

  static native void stop();

  static native void unload();
}
