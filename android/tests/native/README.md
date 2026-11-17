# JNI inference smoke test

`Smoke.java` uses the production `Engine.java` and the production JNI entrypoints. Compile `engine.cpp` with the pinned llama.cpp + mtmd libraries for the host, link it as `libailocal.so`, and compile both Java sources into package `com.ailocal.app`.

Run with JDK 17:

```
java -Djava.library.path=PATH_TO_HOST_LIBRARY -cp PATH_TO_CLASSES com.ailocal.app.Smoke PATH_TO_GGUF [PATH_TO_MMPROJ]
```

Text test asks 2 + 2 in Spanish; vision test feeds a synthetic red RGB image. Stops after at most 35 generated tokens and rejects empty inference. This test was executed on Linux CPU with Qwen Coder 0.5B Q4_K_M and SmolVLM 500M Q8_0 + its matching Q8_0 projector:

- Qwen: `2 + 2 es igual a 4.`
- SmolVLM: `The main color of the image is red.`

These are host JNI smoke results, not device performance measurements or Android instrumentation tests. Android Downloads, Keystore and photo picking still require a phone/emulator integration test. The browser smoke uses a mock native bridge and does not write to real GitHub repositories.
