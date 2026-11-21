package com.ailocal.app;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

/** Host JNI regression with ordinary catalog GGUFs; never a product loading gate. */
public class InferenceRegression {
  private static final String SYSTEM = "Eres un asistente útil. Responde en español con precisión.";

  private static String ask(String prompt, int limit, Engine.Progress progress) {
    ByteArrayOutputStream output = new ByteArrayOutputStream();
    Engine.generateNative(
        new String[] {"system", "user"},
        new String[] {SYSTEM, prompt},
        null,
        0,
        0,
        limit,
        bytes -> output.write(bytes, 0, bytes.length),
        progress);
    return new String(output.toByteArray(), StandardCharsets.UTF_8);
  }

  public static void main(String[] args) {
    boolean[] loaded = {false};
    Engine.loadNative(
        args[0],
        "",
        2,
        1024,
        (phase, current, total) -> {
          if (phase.equals("weights") && current == 100) loaded[0] = true;
        });
    if (!loaded[0]) throw new AssertionError("No actual weight-loading completion");
    String hello = ask("Hola que tal", 12, null);
    if (hello.isBlank()) throw new AssertionError("Empty greeting");
    System.out.println("GREETING_OK: " + hello + "\n" + Engine.stats());
    boolean[] multipleBatches = {false};
    String longAnswer =
        ask(
            "dato ".repeat(160) + "\nResponde solo con el número: 2+2=",
            8,
            (phase, current, total) -> {
              if (phase.equals("prompt") && current == 128 && total > 128)
                multipleBatches[0] = true;
            });
    if (!multipleBatches[0] || longAnswer.isBlank()) throw new AssertionError("Batch regression");
    System.out.println("MULTI_BATCH_OK: " + longAnswer + "\n" + Engine.stats());
    ask(
        "dato ".repeat(160),
        8,
        (phase, current, total) -> {
          if (phase.equals("prompt") && current == 0) Engine.stop();
        });
    if (!Engine.stats().contains("\"cancelled\":true"))
      throw new AssertionError("Cancellation ignored");
    String retry = ask("Responde solo con el número: 2+2=", 8, null);
    if (!retry.contains("4"))
      throw new AssertionError("Cannot answer after cancellation: " + retry);
    System.out.println("CANCEL_RETRY_OK: " + retry + "\n" + Engine.stats());
    Engine.unload();
  }
}
