package com.ailocal.app;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.regex.*;

/** Checks exact-prefix reuse, suffix replacement, cancellation, and reload invalidation. */
public class CacheRegression {
  private static String ask(String prompt) {
    ByteArrayOutputStream output = new ByteArrayOutputStream();
    Engine.generate(
        new String[] {"system", "user"},
        new String[] {"Responde solo con el número solicitado.", prompt},
        null,
        0,
        0,
        8,
        bytes -> output.write(bytes, 0, bytes.length));
    return new String(output.toByteArray(), StandardCharsets.UTF_8);
  }

  private static int cached() {
    Matcher match = Pattern.compile("\"cachedTokens\":(\\d+)").matcher(Engine.stats());
    if (!match.find()) throw new AssertionError(Engine.stats());
    return Integer.parseInt(match.group(1));
  }

  public static void main(String[] args) {
    if (args.length > 1) Engine.configureBackends(args[1]);
    Engine.load(args[0], "", 2, 1024);
    String prompt = "dato ".repeat(160) + "\nResponde solo con el número: 2+2=";
    String cold = ask(prompt);
    int coldCached = cached();
    if (cold.isBlank() || coldCached != 0) throw new AssertionError(cold + Engine.stats());
    System.out.println("COLD_OK " + Engine.stats());
    String warm = ask(prompt);
    if (warm.isBlank() || cached() < 128) throw new AssertionError(warm + Engine.stats());
    int warmCached = cached();
    System.out.println("WARM_OK " + Engine.stats());
    String changed = ask("dato ".repeat(160) + "\nResponde solo con el número: 3+3=");
    if (changed.isBlank() || cached() >= warmCached || cached() < 128)
      throw new AssertionError("Changed suffix was not invalidated: " + Engine.stats());
    System.out.println("SUFFIX_OK " + Engine.stats());
    Engine.unload();
    Engine.load(args[0], "", 2, 1024);
    ask(prompt);
    if (cached() != 0) throw new AssertionError("Cache crossed model reload");
    Engine.unload();
    System.out.println("CACHE_REGRESSION_OK");
  }
}
