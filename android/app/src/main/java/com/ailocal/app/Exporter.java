package com.ailocal.app;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Turns a Markdown answer into a downloadable document without any third-party library. */
final class Exporter {
  private Exporter() {}

  static final String[] FORMATS = {"md", "txt", "html", "docx", "pdf"};

  static String mime(String format) {
    switch (format) {
      case "raw":
        return "application/octet-stream";
      case "md":
        return "text/markdown";
      case "txt":
        return "text/plain";
      case "html":
        return "text/html";
      case "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
      case "pdf":
        return "application/pdf";
      default:
        throw new IllegalArgumentException("Formato no admitido: " + format);
    }
  }

  /** Name for a raw file such as admin_store.py; keeps the extension the model chose. */
  static String fileName(String name) {
    String base = name == null ? "" : name.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", "_").trim();
    base = base.replaceAll("^\\.+", "");
    if (base.length() > 80) base = base.substring(base.length() - 80);
    return base.isEmpty() ? "archivo.txt" : base;
  }

  static String safeMime(String mime) {
    return mime != null && mime.matches("[a-z]+/[a-z0-9.+-]+") ? mime : "application/octet-stream";
  }

  static String safeName(String title, String format) {
    String base = title == null ? "" : title.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", " ").trim();
    base = base.replaceAll("\\s+", " ");
    if (base.length() > 60) base = base.substring(0, 60).trim();
    if (base.isEmpty()) base = "respuesta-auren";
    return base + "." + format;
  }

  static byte[] export(String markdown, String format) throws IOException {
    String text = markdown == null ? "" : markdown.replace("\r\n", "\n");
    switch (format) {
      case "raw":
      case "md":
        return (format.equals("raw") ? markdown : text).getBytes(StandardCharsets.UTF_8);
      case "txt":
        return plain(text).getBytes(StandardCharsets.UTF_8);
      case "html":
        return html(text).getBytes(StandardCharsets.UTF_8);
      case "docx":
        return docx(text);
      case "pdf":
        return pdf(text);
      default:
        throw new IllegalArgumentException("Formato no admitido: " + format);
    }
  }

  // ---------- block model shared by txt/docx/pdf ----------

  private static final class Block {
    final String kind; // h1 h2 h3 p li code
    final String text;

    Block(String kind, String text) {
      this.kind = kind;
      this.text = text;
    }
  }

  private static String inline(String s) {
    return s.replaceAll("\\*\\*(.+?)\\*\\*", "$1")
        .replaceAll("__(.+?)__", "$1")
        .replaceAll("`([^`]+)`", "$1")
        .replaceAll("\\[([^\\]]+)\\]\\(([^)]+)\\)", "$1 ($2)");
  }

  private static List<Block> blocks(String markdown) {
    List<Block> out = new ArrayList<>();
    boolean code = false;
    StringBuilder paragraph = new StringBuilder();
    for (String line : markdown.split("\n", -1)) {
      if (line.startsWith("```")) {
        flush(out, paragraph);
        code = !code;
        continue;
      }
      if (code) {
        out.add(new Block("code", line));
        continue;
      }
      String t = line.trim();
      if (t.isEmpty()) {
        flush(out, paragraph);
      } else if (t.matches("#{1,6} .*")) {
        flush(out, paragraph);
        int level = Math.min(3, t.indexOf(' '));
        out.add(new Block("h" + level, inline(t.substring(t.indexOf(' ') + 1))));
      } else if (t.matches("([-*+]|\\d+[.)]) .*")) {
        flush(out, paragraph);
        String marker =
            t.startsWith("-") || t.startsWith("*") || t.startsWith("+")
                ? "• "
                : t.substring(0, t.indexOf(' ') + 1);
        out.add(new Block("li", marker + inline(t.substring(t.indexOf(' ') + 1))));
      } else {
        if (paragraph.length() > 0) paragraph.append(' ');
        paragraph.append(inline(t));
      }
    }
    flush(out, paragraph);
    return out;
  }

  private static void flush(List<Block> out, StringBuilder paragraph) {
    if (paragraph.length() > 0) {
      out.add(new Block("p", paragraph.toString()));
      paragraph.setLength(0);
    }
  }

  // ---------- txt ----------

  static String plain(String markdown) {
    StringBuilder b = new StringBuilder();
    String previous = "";
    for (Block block : blocks(markdown)) {
      if (!block.kind.equals("code") && !block.kind.equals("li") && b.length() > 0) b.append('\n');
      if (block.kind.equals("li") && !previous.equals("li") && b.length() > 0) b.append('\n');
      if (block.kind.equals("code") && !previous.equals("code") && b.length() > 0) b.append('\n');
      b.append(block.kind.equals("code") ? "    " + block.text : block.text).append('\n');
      previous = block.kind;
    }
    return b.toString();
  }

  // ---------- html ----------

  static String esc(String s) {
    return s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;");
  }

  private static String inlineHtml(String raw) {
    String s = esc(raw);
    s = s.replaceAll("`([^`]+)`", "<code>$1</code>");
    s = s.replaceAll("\\*\\*(.+?)\\*\\*", "<strong>$1</strong>");
    s = s.replaceAll("__(.+?)__", "<strong>$1</strong>");
    s =
        s.replaceAll(
            "\\[([^\\]]+)\\]\\((https?://[^)\\s]+)\\)", "<a href=\"$2\" rel=\"noopener\">$1</a>");
    return s;
  }

  static String html(String markdown) {
    StringBuilder b = new StringBuilder();
    b.append("<!doctype html>\n<html lang=\"es\"><head><meta charset=\"utf-8\">")
        .append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
        .append("<title>Respuesta de Auren</title><style>")
        .append("body{font:16px/1.6 system-ui,sans-serif;max-width:46rem;margin:2rem auto;")
        .append("padding:0 1rem;color:#1b1f23}pre{background:#f3f4f6;padding:.8rem;")
        .append("border-radius:8px;overflow:auto}code{font-family:ui-monospace,monospace;")
        .append("background:#f3f4f6;padding:.1rem .3rem;border-radius:4px}pre code{padding:0}")
        .append("</style></head><body>\n");
    boolean code = false, list = false;
    StringBuilder paragraph = new StringBuilder();
    for (String line : markdown.split("\n", -1)) {
      if (line.startsWith("```")) {
        closeParagraph(b, paragraph);
        if (list) {
          b.append("</ul>\n");
          list = false;
        }
        b.append(code ? "</code></pre>\n" : "<pre><code>");
        code = !code;
        continue;
      }
      if (code) {
        b.append(esc(line)).append('\n');
        continue;
      }
      String t = line.trim();
      boolean item = t.matches("([-*+]|\\d+[.)]) .*");
      if (!item && list) {
        b.append("</ul>\n");
        list = false;
      }
      if (t.isEmpty()) {
        closeParagraph(b, paragraph);
      } else if (t.matches("#{1,6} .*")) {
        closeParagraph(b, paragraph);
        int level = t.indexOf(' ');
        b.append("<h")
            .append(level)
            .append('>')
            .append(inlineHtml(t.substring(level + 1)))
            .append("</h")
            .append(level)
            .append(">\n");
      } else if (item) {
        closeParagraph(b, paragraph);
        if (!list) {
          b.append("<ul>\n");
          list = true;
        }
        b.append("<li>").append(inlineHtml(t.substring(t.indexOf(' ') + 1))).append("</li>\n");
      } else {
        if (paragraph.length() > 0) paragraph.append(' ');
        paragraph.append(t);
      }
    }
    closeParagraph(b, paragraph);
    if (list) b.append("</ul>\n");
    if (code) b.append("</code></pre>\n");
    return b.append("</body></html>\n").toString();
  }

  private static void closeParagraph(StringBuilder b, StringBuilder paragraph) {
    if (paragraph.length() > 0) {
      b.append("<p>").append(inlineHtml(paragraph.toString())).append("</p>\n");
      paragraph.setLength(0);
    }
  }

  // ---------- docx ----------

  private static String xml(String s) {
    StringBuilder b = new StringBuilder();
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      if (c == '&') b.append("&amp;");
      else if (c == '<') b.append("&lt;");
      else if (c == '>') b.append("&gt;");
      else if (c == '\t' || c == '\n' || c == '\r' || c >= 0x20 && c != 0xFFFE && c != 0xFFFF)
        b.append(c);
    }
    return b.toString();
  }

  static byte[] docx(String markdown) throws IOException {
    StringBuilder body = new StringBuilder();
    for (Block block : blocks(markdown)) {
      String style = "";
      String run = "";
      switch (block.kind) {
        case "h1":
          style = "<w:pStyle w:val=\"Heading1\"/>";
          break;
        case "h2":
          style = "<w:pStyle w:val=\"Heading2\"/>";
          break;
        case "h3":
          style = "<w:pStyle w:val=\"Heading3\"/>";
          break;
        case "li":
          style = "<w:ind w:left=\"360\"/>";
          break;
        case "code":
          style = "<w:spacing w:after=\"0\"/>";
          run =
              "<w:rPr><w:rFonts w:ascii=\"Courier New\" w:hAnsi=\"Courier New\"/>"
                  + "<w:sz w:val=\"20\"/></w:rPr>";
          break;
        default:
      }
      body.append("<w:p><w:pPr>")
          .append(style)
          .append("</w:pPr><w:r>")
          .append(run)
          .append("<w:t xml:space=\"preserve\">")
          .append(xml(block.text))
          .append("</w:t></w:r></w:p>");
    }
    String ns = "xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"";
    String document =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><w:document "
            + ns
            + "><w:body>"
            + body
            + "<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1134\""
            + " w:right=\"1134\" w:bottom=\"1134\" w:left=\"1134\" w:header=\"708\""
            + " w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>";
    String styles =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><w:styles "
            + ns
            + "><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii=\"Calibri\""
            + " w:hAnsi=\"Calibri\"/><w:sz"
            + " w:val=\"22\"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing"
            + " w:after=\"120\" w:line=\"276\" w:lineRule=\"auto\"/></w:pPr></w:pPrDefault>"
            + "</w:docDefaults>"
            + heading("Heading1", "heading 1", 36)
            + heading("Heading2", "heading 2", 30)
            + heading("Heading3", "heading 3", 26)
            + "</w:styles>";
    String types =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types"
            + " xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default"
            + " Extension=\"rels\""
            + " ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default"
            + " Extension=\"xml\" ContentType=\"application/xml\"/><Override"
            + " PartName=\"/word/document.xml\""
            + " ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/><Override"
            + " PartName=\"/word/styles.xml\""
            + " ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml\"/>"
            + "</Types>";
    String rels =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships"
            + " xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship"
            + " Id=\"rId1\""
            + " Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\""
            + " Target=\"word/document.xml\"/></Relationships>";
    String docRels =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships"
            + " xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship"
            + " Id=\"rId1\""
            + " Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\""
            + " Target=\"styles.xml\"/></Relationships>";
    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
    try (ZipOutputStream zip = new ZipOutputStream(bytes)) {
      put(zip, "[Content_Types].xml", types);
      put(zip, "_rels/.rels", rels);
      put(zip, "word/document.xml", document);
      put(zip, "word/styles.xml", styles);
      put(zip, "word/_rels/document.xml.rels", docRels);
    }
    return bytes.toByteArray();
  }

  private static String heading(String id, String name, int size) {
    return "<w:style w:type=\"paragraph\" w:styleId=\""
        + id
        + "\"><w:name w:val=\""
        + name
        + "\"/><w:pPr><w:keepNext/><w:spacing w:before=\"240\" w:after=\"120\"/></w:pPr>"
        + "<w:rPr><w:b/><w:sz w:val=\""
        + size
        + "\"/></w:rPr></w:style>";
  }

  private static void put(ZipOutputStream zip, String name, String content) throws IOException {
    zip.putNextEntry(new ZipEntry(name));
    zip.write(content.getBytes(StandardCharsets.UTF_8));
    zip.closeEntry();
  }

  // ---------- pdf ----------

  private static final Charset WIN_ANSI = Charset.forName("windows-1252");
  private static final int PAGE_W = 595, PAGE_H = 842, MARGIN = 56;

  private static String pdfString(String s) {
    byte[] raw = s.getBytes(WIN_ANSI); // unmappable characters become '?'
    StringBuilder b = new StringBuilder("(");
    for (byte value : raw) {
      int c = value & 0xFF;
      if (c == '(' || c == ')' || c == '\\') b.append('\\').append((char) c);
      else if (c < 32 || c > 126) b.append(String.format("\\%03o", c));
      else b.append((char) c);
    }
    return b.append(')').toString();
  }

  private static List<String> wrap(String text, int max) {
    List<String> lines = new ArrayList<>();
    String rest = text;
    while (rest.length() > max) {
      int cut = rest.lastIndexOf(' ', max);
      if (cut <= 0) cut = max;
      lines.add(rest.substring(0, cut).trim());
      rest = rest.substring(cut).trim();
    }
    lines.add(rest);
    return lines;
  }

  static byte[] pdf(String markdown) throws IOException {
    List<StringBuilder> pages = new ArrayList<>();
    StringBuilder page = null;
    double y = 0;
    for (Block block : blocks(markdown)) {
      String font = "F1";
      int size = 11, chars = 88;
      double lead = 15, before = 4;
      switch (block.kind) {
        case "h1":
          font = "F2";
          size = 18;
          chars = 52;
          lead = 24;
          before = 12;
          break;
        case "h2":
          font = "F2";
          size = 15;
          chars = 62;
          lead = 20;
          before = 10;
          break;
        case "h3":
          font = "F2";
          size = 12;
          chars = 76;
          lead = 17;
          before = 8;
          break;
        case "code":
          font = "F3";
          size = 9;
          chars = 92;
          lead = 12;
          before = 0;
          break;
        default:
      }
      for (String line : wrap(block.text, chars)) {
        if (page == null || y - lead < MARGIN) {
          page = new StringBuilder();
          pages.add(page);
          y = PAGE_H - MARGIN;
        }
        y -= lead;
        page.append("BT /")
            .append(font)
            .append(' ')
            .append(size)
            .append(" Tf ")
            .append(MARGIN)
            .append(' ')
            .append(String.format(java.util.Locale.ROOT, "%.1f", y))
            .append(" Td ")
            .append(pdfString(line))
            .append(" Tj ET\n");
      }
      y -= before;
    }
    if (pages.isEmpty()) pages.add(new StringBuilder());

    // Objects: 1 catalog, 2 pages, 3-5 fonts, then (page, content) pairs.
    List<String> objects = new ArrayList<>();
    objects.add("<< /Type /Catalog /Pages 2 0 R >>");
    StringBuilder kids = new StringBuilder();
    for (int i = 0; i < pages.size(); i++) kids.append(6 + i * 2).append(" 0 R ");
    objects.add("<< /Type /Pages /Kids [" + kids + "] /Count " + pages.size() + " >>");
    objects.add(
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");
    objects.add(
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
    objects.add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>");
    for (int i = 0; i < pages.size(); i++) {
      int content = 7 + i * 2;
      objects.add(
          "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
              + PAGE_W
              + " "
              + PAGE_H
              + "] /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents "
              + content
              + " 0 R >>");
      byte[] stream = pages.get(i).toString().getBytes(StandardCharsets.ISO_8859_1);
      objects.add(
          "<< /Length "
              + stream.length
              + " >>\nstream\n"
              + new String(stream, StandardCharsets.ISO_8859_1)
              + "endstream");
    }
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    List<Integer> offsets = new ArrayList<>();
    out.write("%PDF-1.4\n".getBytes(StandardCharsets.ISO_8859_1));
    for (int i = 0; i < objects.size(); i++) {
      offsets.add(out.size());
      out.write(
          ((i + 1) + " 0 obj\n" + objects.get(i) + "\nendobj\n")
              .getBytes(StandardCharsets.ISO_8859_1));
    }
    int xref = out.size();
    StringBuilder table = new StringBuilder("xref\n0 " + (objects.size() + 1) + "\n");
    table.append("0000000000 65535 f \n");
    for (int offset : offsets) table.append(String.format("%010d 00000 n \n", offset));
    table
        .append("trailer\n<< /Size ")
        .append(objects.size() + 1)
        .append(" /Root 1 0 R >>\nstartxref\n")
        .append(xref)
        .append("\n%%EOF\n");
    out.write(table.toString().getBytes(StandardCharsets.ISO_8859_1));
    return out.toByteArray();
  }
}
