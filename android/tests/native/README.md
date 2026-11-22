# JNI inference smoke test

## 2.3.1 blank-chat regression

Compile `InferenceRegression.java` alongside the production `Engine.java` and run with the same host JNI library:

```
java -Djava.library.path=PATH_TO_HOST_LIBRARY -cp PATH_TO_CLASSES com.ailocal.app.InferenceRegression PATH_TO_GGUF
```

Before the fix, a prompt with more than 128 tokens reproduced a process abort at `GGML_ASSERT(n_tokens_all <= cparams.n_batch)`: the engine submitted 256-token chunks to a 128-token context batch. Both text and vision now use `llama_n_batch(ctx)`.

The updated production JNI was tested on Linux CPU with the catalog's Qwen2.5-Coder-7B-Instruct Q4_K_M (4,683,073,536 bytes; SHA-256 `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`). With context 1024 / K Q8 / V F16 and two CPU threads it answered `Hola que tal` with `Hola! Estoy bien, gracias. ¿Y tú?`, returned `4` after a >128-token prompt, accepted cancellation during preparation, and returned `4` on retry. These are host JNI correctness checks, not performance claims for a phone. The short output caps belong only to this regression test; ordinary app responses still use the user's configured limit up to 2048 tokens.

Android CI separately runs `NativeChatTest` with an SHA-verified Qwen Coder 0.5B engineering fixture through the real WebView, Java bridge, JNI and streamed response. The fixture is not bundled in the distribution APK or loaded as a product prerequisite.

## Initial text and vision smoke

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

## 2.8 context and finish reasons

`WindowRegression` runs the actual JNI with a verified GGUF and a 512-token context. It checks a one-token output cap reports `length`, a longer copy task crosses the context boundary by shifting KV, protected GitHub references are rejected rather than silently truncated, an oversized conversation keeps the latest question, and a natural answer reports `eos`. Android `NativeChatTest` also goes Home while tokens are being produced, verifies the service answer grows without a visible WebView, returns while inference is still active, and checks that completion is imported once. These are real inference checks; UI mocks separately cover color picking, stored finish reasons, continuation and safe code rendering.
