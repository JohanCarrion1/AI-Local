package com.ailocal.app;

import android.app.*;
import android.os.*;
import android.content.*;
import android.database.Cursor;
import android.graphics.*;
import android.net.Uri;
import android.security.keystore.*;
import android.util.Base64;
import android.webkit.*;
import androidx.webkit.WebViewAssetLoader;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;

public class MainActivity extends Activity {
    private WebView web;
    private JSONArray models;
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private final ExecutorService inference=Executors.newSingleThreadExecutor();
    private android.content.SharedPreferences prefs;
    private DownloadManager dm;
    private String active="", token="";
    private byte[] image;
    private int imageWidth,imageHeight;
    private volatile boolean busy=false;
    private boolean destroyed=false;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable ticker=new Runnable(){public void run(){if(!destroyed){io.execute(()->{try{downloads();}catch(Exception e){event("error",e.getMessage());}}); handler.postDelayed(this,2000);}};
    @Override public void onCreate(Bundle state){
        super.onCreate(state); prefs=getSharedPreferences("local",MODE_PRIVATE); dm=(DownloadManager)getSystemService(DOWNLOAD_SERVICE);
        try { models=new JSONArray(new String(read(getAssets().open("models.json"),1048576),StandardCharsets.UTF_8)); token=readToken(); } catch(Exception e){ models=new JSONArray(); }
        web=new WebView(this); setContentView(web); web.setBackgroundColor(Color.rgb(16,23,19));
        web.getSettings().setJavaScriptEnabled(true); web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false); web.getSettings().setAllowContentAccess(false);
        web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        WebViewAssetLoader loader=new WebViewAssetLoader.Builder().addPathHandler("/assets/",new WebViewAssetLoader.AssetsPathHandler(this)).build();
        web.setWebViewClient(new WebViewClient(){
            @Override public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest r){return loader.shouldInterceptRequest(r.getUrl());}
            @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return true;}
            @Override public void onPageFinished(WebView v,String u){ if(u.equals("https://appassets.androidplatform.net/assets/index.html")) io.execute(()->snapshot()); }
        });
        web.addJavascriptInterface(new Bridge(),"Native");
        web.loadUrl("https://appassets.androidplatform.net/assets/index.html"); handler.post(ticker);
    }
    private void event(String type,Object data){try{String js="window.receive("+JSONObject.quote(type)+","+JSONObject.valueToString(data)+")";runOnUiThread(()->{if(!destroyed)web.evaluateJavascript(js,null);});}catch(Exception ignored){}}
    private static byte[] read(InputStream in,int limit)throws IOException{try(InputStream stream=in;ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] b=new byte[8192];int n;while((n=stream.read(b))!=-1){if(out.size()+n>limit)throw new IOException("Archivo demasiado grande");out.write(b,0,n);}return out.toByteArray();}}
    private JSONObject model(String id)throws Exception{for(int i=0;i<models.length();i++)if(models.getJSONObject(i).getString("id").equals(id))return models.getJSONObject(i);throw new IOException("Modelo desconocido");}
    private File file(JSONObject f)throws Exception{return new File(getExternalFilesDir("models"),f.getString("file"));}
    private File ready(JSONObject f)throws Exception{return new File(file(f).getPath()+".ready");}
    private boolean installed(JSONObject m)throws Exception{JSONArray fs=m.getJSONArray("files");for(int i=0;i<fs.length();i++){JSONObject f=fs.getJSONObject(i);if(!ready(f).exists()||file(f).length()!=f.getLong("size"))return false;}return true;}
    private void snapshot(){try{
        ActivityManager.MemoryInfo mem=new ActivityManager.MemoryInfo();((ActivityManager)getSystemService(ACTIVITY_SERVICE)).getMemoryInfo(mem);
        JSONObject s=new JSONObject().put("models",models).put("ram",mem.totalMem/1073741824.0).put("available",mem.availMem/1073741824.0).put("storage",getExternalFilesDir(null).getUsableSpace()/1073741824.0).put("connected",!token.isEmpty()).put("active",active);
        JSONArray ids=new JSONArray();for(int i=0;i<models.length();i++)if(installed(models.getJSONObject(i)))ids.put(models.getJSONObject(i).getString("id"));s.put("installed",ids);event("state",s);
    }catch(Exception e){event("error",e.getMessage());}}
    private void downloads()throws Exception{
        for(int i=0;i<models.length();i++){JSONObject m=models.getJSONObject(i);JSONArray fs=m.getJSONArray("files");
            for(int j=0;j<fs.length();j++){JSONObject f=fs.getJSONObject(j);String key="download_"+f.getString("file");long id=prefs.getLong(key,-1);if(id==-1)continue;
                try(Cursor c=dm.query(new DownloadManager.Query().setFilterById(id))){
                    if(!c.moveToFirst()){prefs.edit().remove(key).apply();continue;}
                    int status=c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));long bytes=c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR));
                    event("download",new JSONObject().put("id",m.getString("id")).put("file",f.getString("file")).put("bytes",bytes).put("total",f.getLong("size")).put("status",status));
                    if(status==DownloadManager.STATUS_SUCCESSFUL){
                        event("notice","Verificando SHA-256: "+m.getString("name")); MessageDigest digest=MessageDigest.getInstance("SHA-256");byte[] buf=new byte[1024*1024];int n;
                        try(InputStream in=new FileInputStream(file(f))){while((n=in.read(buf))!=-1)digest.update(buf,0,n);}
                        StringBuilder hash=new StringBuilder();for(byte b:digest.digest())hash.append(String.format("%02x",b&255));
                        if(!hash.toString().equals(f.getString("sha256"))||file(f).length()!=f.getLong("size")){dm.remove(id);event("error","Descarga dañada. Vuelve a descargar el modelo.");}
                        else {try(FileOutputStream marker=new FileOutputStream(ready(f))){marker.write(hash.toString().getBytes(StandardCharsets.UTF_8));}event("notice","Archivo verificado: "+m.getString("name"));}
                        prefs.edit().remove(key).apply();snapshot();
                    }else if(status==DownloadManager.STATUS_FAILED){dm.remove(id);prefs.edit().remove(key).apply();event("error","Falló la descarga. Comprueba la red y el espacio; puedes reintentar.");snapshot();}
                }
            }
        }
    }
    private void download(String id)throws Exception{
        JSONObject m=model(id);long needed=0;JSONArray fs=m.getJSONArray("files");
        for(int i=0;i<fs.length();i++)if(!ready(fs.getJSONObject(i)).exists())needed+=fs.getJSONObject(i).getLong("size");
        if(getExternalFilesDir(null).getUsableSpace()<needed+268435456)throw new IOException("No hay espacio suficiente para este modelo.");
        for(int i=0;i<fs.length();i++){JSONObject f=fs.getJSONObject(i);String key="download_"+f.getString("file");if(ready(f).exists()||prefs.contains(key))continue;
            file(f).delete(); DownloadManager.Request req=new DownloadManager.Request(Uri.parse(f.getString("url"))).setTitle("AI Local · "+m.getString("name")).setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setDestinationInExternalFilesDir(this,"models",f.getString("file"));
            prefs.edit().putLong(key,dm.enqueue(req)).apply();
        }event("notice","Descarga iniciada. Android la mantiene aunque salgas de la app.");
    }
    private void cancelDownload(String id)throws Exception{JSONArray fs=model(id).getJSONArray("files");for(int i=0;i<fs.length();i++){JSONObject f=fs.getJSONObject(i);String key="download_"+f.getString("file");long task=prefs.getLong(key,-1);if(task!=-1)dm.remove(task);prefs.edit().remove(key).apply();}event("notice","Descarga cancelada");snapshot();}
    private void saveToken(String value)throws Exception{
        if(value.isEmpty()){prefs.edit().remove("token").remove("iv").apply();token="";return;}
        KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
        if(!ks.containsAlias("github")){KeyGenerator gen=KeyGenerator.getInstance("AES","AndroidKeyStore");gen.init(new KeyGenParameterSpec.Builder("github",KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());gen.generateKey();}
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,ks.getKey("github",null));
        prefs.edit().putString("token",Base64.encodeToString(cipher.doFinal(value.getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP)).putString("iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP)).apply();token=value;
    }
    private String readToken()throws Exception{
        if(!prefs.contains("token"))return "";KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,ks.getKey("github",null),new GCMParameterSpec(128,Base64.decode(prefs.getString("iv",""),Base64.NO_WRAP)));return new String(cipher.doFinal(Base64.decode(prefs.getString("token",""),Base64.NO_WRAP)),StandardCharsets.UTF_8);
    }
    private Object github(String path,String method,JSONObject body,String auth)throws Exception{
        HttpURLConnection c=(HttpURLConnection)new URL("https://api.github.com"+path).openConnection();c.setInstanceFollowRedirects(false);c.setConnectTimeout(20000);c.setReadTimeout(30000);c.setRequestMethod(method);c.setRequestProperty("Accept","application/vnd.github+json");c.setRequestProperty("X-GitHub-Api-Version","2022-11-28");c.setRequestProperty("Authorization","Bearer "+auth);
        try{if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");try(OutputStream out=c.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}}
            int code=c.getResponseCode();if(code<200||code>=300)throw new IOException(code==409||code==422?"El archivo cambió en GitHub. Recárgalo antes de guardar.":"GitHub HTTP "+code+". Revisa token, permisos y repositorio.");
            try(InputStream in=c.getInputStream()){return new JSONTokener(new String(read(in,3*1024*1024),StandardCharsets.UTF_8)).nextValue();}
        }finally{c.disconnect();}
    }
    private static String enc(String s)throws Exception{return java.net.URLEncoder.encode(s,"UTF-8").replace("+","%20");}
    private static String repo(String s)throws Exception{if(!s.matches("[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"))throw new IOException("Usa propietario/repositorio");return s;}
    private static String path(String s)throws Exception{StringBuilder b=new StringBuilder();for(String segment:s.split("/")){if(segment.equals(".."))throw new IOException("Ruta inválida");if(b.length()>0)b.append('/');b.append(enc(segment));}return b.toString();}
    public class Bridge {
        @JavascriptInterface public void command(String action,String payload){
            if(action.equals("stop")){Engine.stop();return;}
            if(action.equals("image")){runOnUiThread(()->{if(busy){event("error","Espera a que termine la respuesta.");return;}Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*").addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(intent,11);});return;}
            if(action.equals("chat")||action.equals("load")||action.equals("delete")){
                synchronized(MainActivity.this){if(busy){event("error","Hay una operación del modelo en curso.");return;}busy=true;}
                inference.execute(()->{try{JSONObject p=new JSONObject(payload);
                    if(action.equals("load")){JSONObject m=model(p.getString("id"));if(!installed(m))throw new IOException("Primero descarga el modelo completo.");active="";snapshot();JSONArray fs=m.getJSONArray("files");Engine.load(file(fs.getJSONObject(0)).getPath(),m.getBoolean("vision")?file(fs.getJSONObject(1)).getPath():"",Math.max(1,Math.min(4,Runtime.getRuntime().availableProcessors()-1)));active=m.getString("id");snapshot();event("loaded",active);}
                    else if(action.equals("delete")){JSONObject m=model(p.getString("id"));if(active.equals(m.getString("id"))){Engine.unload();active="";}cancelDownload(m.getString("id"));JSONArray fs=m.getJSONArray("files");for(int i=0;i<fs.length();i++){file(fs.getJSONObject(i)).delete();ready(fs.getJSONObject(i)).delete();}snapshot();}
                    else {if(active.isEmpty())throw new IOException("Carga un modelo en la Biblioteca.");JSONArray history=p.getJSONArray("messages");if(history.length()>40)throw new IOException("Inicia una conversación nueva.");String[] roles=new String[history.length()],texts=new String[history.length()];for(int i=0;i<history.length();i++){roles[i]=history.getJSONObject(i).getString("role");texts[i]=history.getJSONObject(i).getString("content");}ByteArrayOutputStream output=new ByteArrayOutputStream();Engine.generate(roles,texts,image,imageWidth,imageHeight,bytes->{output.write(bytes,0,bytes.length);event("answer",new String(output.toByteArray(),StandardCharsets.UTF_8));});image=null;event("done",true);}
                }catch(Throwable e){event("error",e.getMessage()==null?"Error del motor local":e.getMessage());event("done",false);}finally{busy=false;event("idle",true);}});return;
            }
            io.execute(()->{try{JSONObject p=new JSONObject(payload);switch(action){
                case "state": snapshot();break;
                case "download":download(p.getString("id"));break;
                case "cancel":cancelDownload(p.getString("id"));break;
                case "clearImage":image=null;event("image",false);break;
                case "connect":{String t=p.getString("token").trim();JSONObject user=(JSONObject)github("/user","GET",null,t);saveToken(t);event("notice","Conectado como "+user.getString("login"));snapshot();break;}
                case "disconnect":saveToken("");snapshot();event("notice","Token eliminado");break;
                case "repos":event("repos",github("/user/repos?per_page=100&sort=updated","GET",null,token));break;
                case "read":{String r=repo(p.getString("repo")),f=path(p.optString("path"));Object result=github("/repos/"+r+"/contents/"+f+"?ref="+enc(p.getString("branch")),"GET",null,token);if(result instanceof JSONObject){JSONObject ob=(JSONObject)result;if(ob.optLong("size")>524288||!ob.optString("encoding").equals("base64"))throw new IOException("Solo se pueden editar archivos de texto de hasta 512 KB.");ob.put("text",new String(Base64.decode(ob.getString("content"),Base64.DEFAULT),StandardCharsets.UTF_8));}event("file",result);break;}
                case "write":{if(p.getString("message").trim().isEmpty())throw new IOException("Escribe un mensaje de commit");String r=repo(p.getString("repo"));JSONObject body=new JSONObject().put("message",p.getString("message")).put("branch",p.getString("branch")).put("sha",p.getString("sha")).put("content",Base64.encodeToString(p.getString("text").getBytes(StandardCharsets.UTF_8),Base64.NO_WRAP));JSONObject result=(JSONObject)github("/repos/"+r+"/contents/"+path(p.getString("path")),"PUT",body,token);event("saved",result.getJSONObject("content").getString("sha"));break;}
            }}catch(Exception e){event("error",e.getMessage());}});
        }
    }
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request!=11||result!=RESULT_OK||data==null)return;Uri uri=data.getData();io.execute(()->{try{
        BitmapFactory.Options opts=new BitmapFactory.Options();opts.inJustDecodeBounds=true;try(InputStream in=getContentResolver().openInputStream(uri)){BitmapFactory.decodeStream(in,null,opts);}if(opts.outWidth<=0||opts.outHeight<=0)throw new IOException("Imagen no compatible");opts.inSampleSize=1;while(Math.max(opts.outWidth,opts.outHeight)/opts.inSampleSize>1024)opts.inSampleSize*=2;opts.inJustDecodeBounds=false;
        Bitmap bitmap;try(InputStream in=getContentResolver().openInputStream(uri)){bitmap=BitmapFactory.decodeStream(in,null,opts);}if(bitmap==null)throw new IOException("No se pudo leer la imagen");imageWidth=bitmap.getWidth();imageHeight=bitmap.getHeight();int[] pixels=new int[imageWidth*imageHeight];bitmap.getPixels(pixels,0,imageWidth,0,0,imageWidth,imageHeight);byte[] bytes=new byte[pixels.length*3];for(int i=0;i<pixels.length;i++){bytes[3*i]=(byte)(pixels[i]>>16);bytes[3*i+1]=(byte)(pixels[i]>>8);bytes[3*i+2]=(byte)pixels[i];}image=bytes;bitmap.recycle();event("image",true);
    }catch(Exception e){event("error",e.getMessage());}});}
    @Override public void onBackPressed(){new AlertDialog.Builder(this).setMessage("¿Salir de AI Local?").setPositiveButton("Salir",(d,w)->finish()).setNegativeButton("Continuar",null).show();}
    @Override protected void onDestroy(){destroyed=true;handler.removeCallbacks(ticker);Engine.stop();inference.execute(()->Engine.unload());inference.shutdown();io.shutdown();web.destroy();super.onDestroy();}
}
