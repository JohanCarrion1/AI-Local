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

## 7B Q3 memory regression check (host CPU)

Qwen2.5-Coder-7B-Instruct Q3_K_M was downloaded from the pinned catalog revision and SHA-256 verified. The production JNI engine loaded all model weights, created context 1024 with K Q8 / V F16, and answered `4` to 2+2. Linux peak RSS was 5,089,668 KiB with extra repacking buffers and 3,858,816 KiB with `use_extra_bufts=false`. The backend's extra `CPU_REPACK` allocation was 1,201.92 MiB; disabling it prioritizes memory over that acceleration. These are host measurements and not claims about any particular Android phone or long-running chat stability. Product loading opens ordinary chat directly; these engineering checks are not a prerequisite in the app.
