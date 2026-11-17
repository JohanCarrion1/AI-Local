package com.ailocal.app;
import java.io.*;
import java.nio.charset.StandardCharsets;
public class Smoke {
  public static void main(String[] args) {
    Engine.load(args[0],args.length>1?args[1]:"",4);
    ByteArrayOutputStream text=new ByteArrayOutputStream();
    final int[] n={0};byte[] rgb=null;
    if(args.length>1){rgb=new byte[224*224*3];for(int i=0;i<rgb.length;i+=3)rgb[i]=(byte)255;}
    Engine.generate(new String[]{"user"},new String[]{rgb==null?"Responde en español: ¿cuánto es 2 + 2? 👋":"What is the main color of this image?"},rgb,224,224,bytes->{text.write(bytes,0,bytes.length);if(++n[0]>=35)Engine.stop();});
    String answer=new String(text.toByteArray(),StandardCharsets.UTF_8);
    if(answer.isBlank())throw new AssertionError("Empty inference");
    System.out.println("SMOKE_OK: "+answer);
    Engine.unload();
  }
}
