package com.ailocal.app;

import static org.junit.Assert.*;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.junit.Test;

public class ExporterTest {
  private static final String SAMPLE =
      "# Informe\n\nTexto con **negrita** y `código` & <etiqueta>.\n\n- uno\n- dos\n\n"
          + "```java\nint x = 1 < 2;\n```\n";

  private static String text(byte[] bytes) {
    return new String(bytes, StandardCharsets.UTF_8);
  }

  @Test
  public void markdownIsKeptVerbatim() throws Exception {
    assertEquals(SAMPLE, text(Exporter.export(SAMPLE, "md")));
  }

  @Test
  public void plainTextDropsMarkdownSyntax() throws Exception {
    String out = text(Exporter.export(SAMPLE, "txt"));
    assertTrue(out.contains("Informe"));
    assertTrue(out.contains("Texto con negrita y código & <etiqueta>."));
    assertTrue(out.contains("• uno"));
    assertTrue(out.contains("    int x = 1 < 2;"));
    assertFalse(out.contains("**"));
    assertFalse(out.contains("```"));
  }

  @Test
  public void htmlEscapesUntrustedContent() throws Exception {
    String out =
        text(Exporter.export("<script>alert(1)</script> [x](javascript:alert(1))", "html"));
    assertFalse(out.contains("<script>alert"));
    assertTrue(out.contains("&lt;script&gt;"));
    assertFalse(out.contains("href=\"javascript"));
    String full = text(Exporter.export(SAMPLE, "html"));
    assertTrue(full.contains("<h1>Informe</h1>"));
    assertTrue(full.contains("<strong>negrita</strong>"));
    assertTrue(full.contains("<li>uno</li>"));
    assertTrue(full.contains("int x = 1 &lt; 2;"));
  }

  @Test
  public void docxIsAValidPackageWithTheContent() throws Exception {
    byte[] bytes = Exporter.export(SAMPLE, "docx");
    Map<String, String> parts = new HashMap<>();
    try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(bytes))) {
      for (ZipEntry e; (e = zip.getNextEntry()) != null; ) {
        ByteArrayOutputStream part = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        for (int n; (n = zip.read(buffer)) > 0; ) part.write(buffer, 0, n);
        parts.put(e.getName(), text(part.toByteArray()));
      }
    }
    assertTrue(parts.containsKey("[Content_Types].xml"));
    assertTrue(parts.containsKey("_rels/.rels"));
    assertTrue(parts.containsKey("word/styles.xml"));
    String document = parts.get("word/document.xml");
    assertTrue(document.contains("Heading1"));
    assertTrue(document.contains("Informe"));
    assertTrue(document.contains("&amp; &lt;etiqueta&gt;"));
    assertTrue(document.contains("int x = 1 &lt; 2;"));
  }

  @Test
  public void pdfHasStructureAndAccentedText() throws Exception {
    byte[] bytes = Exporter.export("# Título\n\nCanción, año y ñandú (prueba) \\ fin", "pdf");
    String raw = new String(bytes, StandardCharsets.ISO_8859_1);
    assertTrue(raw.startsWith("%PDF-1.4"));
    assertTrue(raw.trim().endsWith("%%EOF"));
    assertTrue(raw.contains("/Count 1"));
    assertTrue(raw.contains("\\355")); // í in WinAnsi
    assertTrue(raw.contains("\\(prueba\\)"));
    int xref = Integer.parseInt(raw.substring(raw.indexOf("startxref") + 10).split("\n")[0]);
    assertEquals("xref", raw.substring(xref, xref + 4));
    // Every xref offset must point at "N 0 obj".
    String[] lines = raw.substring(xref).split("\n");
    int count = Integer.parseInt(lines[1].split(" ")[1]);
    for (int i = 1; i < count; i++) {
      int offset = Integer.parseInt(lines[2 + i].substring(0, 10));
      assertTrue(raw.substring(offset).startsWith(i + " 0 obj"));
    }
  }

  @Test
  public void longAnswersSpanSeveralPdfPages() throws Exception {
    StringBuilder b = new StringBuilder();
    for (int i = 0; i < 200; i++) b.append("Línea número ").append(i).append("\n\n");
    String raw = new String(Exporter.export(b.toString(), "pdf"), StandardCharsets.ISO_8859_1);
    assertFalse(raw.contains("/Count 1 "));
    assertTrue(raw.contains("/Count 4") || raw.contains("/Count 5") || raw.contains("/Count 6"));
  }

  @Test
  public void emptyAnswerStillProducesAnOpenableFile() throws Exception {
    for (String format : new String[] {"html", "docx", "pdf"})
      assertTrue(Exporter.export("", format).length > 0);
    assertEquals(0, Exporter.export("", "md").length);
  }

  @Test
  public void fileNamesAreSafe() {
    assertEquals("a b c.pdf", Exporter.safeName("a/b:c", "pdf"));
    assertEquals("respuesta-auren.md", Exporter.safeName("  ", "md"));
    assertTrue(
        Exporter.safeName(new String(new char[200]).replace('\0', 'x'), "txt").length() <= 64);
  }

  @Test
  public void rawFilesKeepTheirExactContentAndModelChosenName() throws Exception {
    String code = "class A:\n    pass\n\nprint('ñ')\n";
    assertEquals(code, text(Exporter.export(code, "raw")));
    assertEquals("admin_store.py", Exporter.fileName("admin_store.py"));
    assertEquals("a_b.py", Exporter.fileName("a/b.py"));
    assertEquals("passwd", Exporter.fileName("../../.passwd".replace("../", "").replace(".", "")));
    assertEquals("archivo.txt", Exporter.fileName("  "));
    assertEquals("text/html", Exporter.safeMime("text/html"));
    assertEquals("application/octet-stream", Exporter.safeMime("x; rm -rf"));
  }

  @Test(expected = IllegalArgumentException.class)
  public void unknownFormatIsRejected() throws Exception {
    Exporter.export("x", "exe");
  }
}
