package com.ailocal.app;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

/** Real weights exercise finish reasons, rolling KV and subsequent turn recovery. */
public class WindowRegression {
  private static String ask(String[] roles, String[] texts, int limit) {
    ByteArrayOutputStream result = new ByteArrayOutputStream();
    Engine.generateNative(
        roles, texts, null, 0, 0, limit, bytes -> result.write(bytes, 0, bytes.length), null);
    return new String(result.toByteArray(), StandardCharsets.UTF_8);
  }

  private static int number(String json, String key) {
    var matcher = Pattern.compile("\\\"" + key + "\\\":([0-9]+)").matcher(json);
    if (!matcher.find()) throw new AssertionError("Missing " + key + ": " + json);
    return Integer.parseInt(matcher.group(1));
  }

  public static void main(String[] args) throws Exception {
    Engine.configureBackends(args[1]);
    Engine.loadNative(args[0], "", 2, 512, null);
    String[] roles = {"system", "user"};
    String system = "You are a helpful assistant.";
    ask(roles, new String[] {system, "Write a long Python program with at least 100 lines."}, 1);
    String limit = Engine.stats();
    if (!limit.contains("\"finishReason\":\"length\"") || number(limit, "generatedTokens") != 1)
      throw new AssertionError("Missing limit reason: " + limit);
    String copied =
        ask(
            roles,
            new String[] {
              system,
              "Copy the following text exactly, repeating every word and ending with DONE:\n"
                  + "hello world ".repeat(150)
            },
            512);
    String shifted = Engine.stats();
    if (number(shifted, "contextShifts") < 1 || number(shifted, "generatedTokens") < 128)
      throw new AssertionError("Long output stopped at the context boundary: " + shifted + copied);
    boolean protectedFile = false;
    try {
      Engine.generateImage(
          new String[] {"system", "user", "assistant", "user"},
          new String[] {
            system,
            "reference file ".repeat(350),
            "old answer ".repeat(350),
            "Edit the reference file."
          },
          null,
          0,
          0,
          32,
          bytes -> {},
          null,
          -1,
          false);
    } catch (IllegalStateException expected) {
      protectedFile = true;
    }
    if (!protectedFile) throw new AssertionError("Reference files must not be silently windowed");
    String result =
        ask(
            new String[] {"system", "user", "assistant", "user"},
            new String[] {
              system,
              "old message ".repeat(350),
              "old answer ".repeat(350),
              "Reply with the number only: 2+2="
            },
            32);
    String trimmed = Engine.stats();
    if (!result.contains("4") || number(trimmed, "trimmedTokens") < 1)
      throw new AssertionError("History window did not recover: " + result + trimmed);
    if (!trimmed.contains("\"finishReason\":\"eos\""))
      throw new AssertionError("Natural completion must report EOS: " + trimmed);
    System.out.println("WINDOW_OK " + shifted + "\nHISTORY_OK " + trimmed);
    Engine.unload();
  }
}
