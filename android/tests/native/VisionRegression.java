package com.ailocal.app;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/** Uses actual pixels, never color names in the prompt or a substitute response. */
public class VisionRegression {
  private static final String SYSTEM = "Answer briefly. Identify the image accurately.";
  private static final String QUESTION = "What color is the square in the center of this picture?";

  private static byte[] pixels(int channel) {
    byte[] image = new byte[224 * 224 * 3];
    java.util.Arrays.fill(image, (byte) 255);
    for (int y = 28; y < 196; y++)
      for (int x = 28; x < 196; x++) {
        int i = (y * 224 + x) * 3;
        image[i] = image[i + 1] = image[i + 2] = 0;
        image[i + channel] = (byte) 255;
      }
    return image;
  }

  private static String ask(String[] roles, String[] texts, byte[] image, int imageIndex) {
    ByteArrayOutputStream output = new ByteArrayOutputStream();
    Engine.generateImage(
        roles,
        texts,
        image,
        224,
        224,
        32,
        b -> output.write(b, 0, b.length),
        null,
        imageIndex,
        true);
    return new String(output.toByteArray(), StandardCharsets.UTF_8);
  }

  private static void color(String text, String expected) {
    if (!text.toLowerCase(Locale.ROOT).contains(expected))
      throw new AssertionError("Expected " + expected + ": " + text);
    if (!Engine.stats().contains("\"imageProcessed\":true"))
      throw new AssertionError("Image was not consumed: " + Engine.stats());
  }

  public static void main(String[] args) {
    if (args.length > 2) Engine.configureBackends(args[2]);
    Engine.load(args[0], args[1], 4, 2048);
    String red =
        ask(new String[] {"system", "user"}, new String[] {SYSTEM, QUESTION}, pixels(0), 1);
    color(red, "red");
    System.out.println("RED_OK " + red + "\n" + Engine.stats());
    String again =
        ask(
            new String[] {"system", "user", "assistant", "user"},
            new String[] {SYSTEM, QUESTION, red, "What color was that square?"},
            pixels(0),
            1);
    color(again, "red");
    if (!Engine.stats().contains("\"imageReused\":true"))
      throw new AssertionError("Image prefix was encoded twice: " + Engine.stats());
    System.out.println("FOLLOWUP_OK " + again + "\n" + Engine.stats());
    String blue =
        ask(new String[] {"system", "user"}, new String[] {SYSTEM, QUESTION}, pixels(2), 1);
    color(blue, "blue");
    if (!Engine.stats().contains("\"imageReused\":false"))
      throw new AssertionError("A different image reused old pixels");
    System.out.println("BLUE_OK " + blue + "\n" + Engine.stats());
    String redAgain =
        ask(new String[] {"system", "user"}, new String[] {SYSTEM, QUESTION}, pixels(0), 1);
    color(redAgain, "red");
    if (Engine.stats().contains("\"imageReused\":true"))
      throw new AssertionError("Returning to red must invalidate blue");
    System.out.println("RED_AGAIN_OK " + redAgain + "\n" + Engine.stats());
    Engine.unload();
  }
}
