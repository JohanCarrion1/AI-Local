package com.ailocal.app;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Real model code generation; Python validation accepts only a pure function AST. */
public class CodeRegression {
  public static void main(String[] args) throws Exception {
    Engine.configureBackends(args[1]);
    Engine.load(args[0], "", 4, 1024);
    ByteArrayOutputStream output = new ByteArrayOutputStream();
    Engine.generate(
        new String[] {"system", "user"},
        new String[] {
          "You are a coding assistant. Return only correct Python code, without reasoning or"
              + " explanations.",
          "Write a Python function named add(a, b) that returns the sum of its two arguments. Do"
              + " not import modules, print, or read input."
        },
        null,
        0,
        0,
        128,
        b -> output.write(b, 0, b.length));
    String code = new String(output.toByteArray(), StandardCharsets.UTF_8);
    Files.writeString(Path.of(args[2]), code, StandardCharsets.UTF_8);
    if (code.isBlank()) throw new AssertionError("Empty code generation");
    System.out.println("CODE_GENERATED\n" + code + "\n" + Engine.stats());
    Engine.unload();
  }
}
