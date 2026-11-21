#include <jni.h>
#include <atomic>
#include <chrono>
#include <sstream>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstdio>
#ifdef __ANDROID__
#include <android/log.h>
#endif
#include "llama.h"
#include "mtmd.h"
#include "mtmd-helper.h"
static llama_model * model = nullptr;
static llama_context * ctx = nullptr;
static mtmd_context * vision = nullptr;
static std::atomic<bool> cancelled{false};
static int generated_tokens = 0;
static double generation_ms = 0;
static bool compact_kv = false;
static std::vector<llama_token> prompt_cache;
static int reused_tokens = 0;
static void clear_cache() {
    prompt_cache.clear();
    if(ctx) llama_memory_clear(llama_get_memory(ctx),true);
}
// Callbacks are local to the serialized JNI operation; never retain an Activity.
struct Progress {
    JNIEnv * env;
    jobject sink;
    jmethodID method = nullptr;
    int last = -1;
    Progress(JNIEnv * e, jobject s): env(e), sink(s) {
        if(s) { auto cls=e->GetObjectClass(s); method=e->GetMethodID(cls,"onProgress","(Ljava/lang/String;II)V"); e->DeleteLocalRef(cls); }
    }
    void emit(const char * phase, int current, int total) {
        if(!sink || env->ExceptionCheck()) return;
        auto text=env->NewStringUTF(phase);
        env->CallVoidMethod(sink,method,text,current,total);
        env->DeleteLocalRef(text);
    }
};
static std::string str(JNIEnv * e, jstring s) { auto cls=e->GetObjectClass(s); auto method=e->GetMethodID(cls,"getBytes","(Ljava/lang/String;)[B"); auto charset=e->NewStringUTF("UTF-8"); auto bytes=(jbyteArray)e->CallObjectMethod(s,method,charset); auto p=e->GetByteArrayElements(bytes,nullptr); std::string v((char*)p,e->GetArrayLength(bytes)); e->ReleaseByteArrayElements(bytes,p,JNI_ABORT); e->DeleteLocalRef(bytes); e->DeleteLocalRef(charset); e->DeleteLocalRef(cls); return v; }
static void fail(JNIEnv * e, const char * msg) { e->ThrowNew(e->FindClass("java/lang/IllegalStateException"),msg); }
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_stop(JNIEnv *,jclass) { cancelled=true; }
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_unload(JNIEnv *,jclass) {
    if(vision) mtmd_free(vision); if(ctx) llama_free(ctx); if(model) llama_model_free(model);
    vision=nullptr; ctx=nullptr; model=nullptr;
    prompt_cache.clear(); reused_tokens=0;
}
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_loadNative(JNIEnv * e,jclass c,jstring path,jstring projector,jint threads,jint context,jobject observer) {
    cancelled=false; Java_com_ailocal_app_Engine_unload(e,c); llama_backend_init();
    llama_log_set([](enum ggml_log_level level,const char * text,void*) {
        if(level<GGML_LOG_LEVEL_INFO || level==GGML_LOG_LEVEL_CONT) return;
#ifdef __ANDROID__
        __android_log_write(level>=GGML_LOG_LEVEL_ERROR?ANDROID_LOG_ERROR:ANDROID_LOG_INFO,"AILocalEngine",text);
#else
        std::fputs(text,stderr);
#endif
    },nullptr);
    Progress progress(e,observer);
    progress.emit("weights",0,100);
    // Avoid an extra repacked copy of weights on memory-constrained phones.
    auto mp=llama_model_default_params(); mp.n_gpu_layers=0; mp.load_mode=LLAMA_LOAD_MODE_MMAP; mp.use_extra_bufts=false;
    mp.progress_callback_user_data=&progress;
    mp.progress_callback=[](float fraction,void * data) {
        auto & p=*static_cast<Progress*>(data); int percent=(int)(fraction*100);
        if(percent!=p.last) { p.last=percent; p.emit("weights",percent,100); }
        return !cancelled.load() && !p.env->ExceptionCheck();
    };
    model=llama_model_load_from_file(str(e,path).c_str(),mp);
    if(!model) { fail(e,cancelled?"Carga detenida.":"No se pudo abrir el GGUF. Comprueba el archivo y la RAM disponible."); return; }
    if(cancelled) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"Carga detenida."); return; }
    auto cp=llama_context_default_params(); cp.n_ctx=std::max(512,std::min(4096,(int)context)); cp.n_batch=128; cp.n_ubatch=64; cp.type_k=GGML_TYPE_Q8_0; cp.type_v=GGML_TYPE_F16; cp.n_threads=threads; cp.n_threads_batch=threads;
    cp.abort_callback=[](void*){ return cancelled.load(); };
    progress.emit("context",0,0);
    compact_kv=true;
    ctx=llama_init_from_model(model,cp);
    if(!ctx) { cp.type_k=GGML_TYPE_F16; compact_kv=false; ctx=llama_init_from_model(model,cp); }
    if(!ctx) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"El motor no pudo crear el contexto. Intenta un contexto menor."); return; }
    if(cancelled) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"Carga detenida."); return; }
    auto p=str(e,projector);
    if(!p.empty()) { auto vp=mtmd_context_params_default(); vp.use_gpu=false; vp.n_threads=threads; vp.image_max_tokens=512;
        progress.emit("vision",0,0);
        vision=mtmd_init_from_file(p.c_str(),model,vp);
        if(!vision) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"No se pudo cargar el proyector visual."); }
    }
}
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_generateNative(JNIEnv * e,jclass,jobjectArray roles,jobjectArray texts,jbyteArray rgb,jint width,jint height,jint maxTokens,jobject sink,jobject observer) {
    if(!ctx) { fail(e,"Selecciona y carga un modelo."); return; }
    auto started=std::chrono::steady_clock::now(); generated_tokens=0; generation_ms=0; reused_tokens=0;
    const int context_size=(int)llama_n_ctx(ctx);
    int output_limit=std::max(1,std::min((int)maxTokens,2048));
    cancelled=false;
    Progress progress(e,observer);
    std::vector<std::string> rs,ts; int count=e->GetArrayLength(texts);
    for(int i=0;i<count;i++) { auto r=(jstring)e->GetObjectArrayElement(roles,i); auto t=(jstring)e->GetObjectArrayElement(texts,i); rs.push_back(str(e,r)); ts.push_back(str(e,t)); e->DeleteLocalRef(r); e->DeleteLocalRef(t); }
    if(rgb) { if(!vision) { fail(e,"Este modelo solo admite texto. Selecciona un modelo de visión para imágenes."); return; } ts.back()=std::string(mtmd_default_marker())+"\n"+ts.back(); }
    std::vector<llama_chat_message> messages; for(int i=0;i<count;i++) messages.push_back({rs[i].c_str(),ts[i].c_str()});
    const char * tmpl=llama_model_chat_template(model,nullptr);
    int n=llama_chat_apply_template(tmpl,messages.data(),messages.size(),true,nullptr,0);
    if(n<0) { fail(e,"Plantilla de chat incompatible con el motor."); return; }
    std::vector<char> formatted(n+1); llama_chat_apply_template(tmpl,messages.data(),messages.size(),true,formatted.data(),formatted.size());
    auto vocab=llama_model_get_vocab(model); llama_pos past=0;
    if(rgb) {
        // Image embeddings do not have a safe token-only reusable prefix.
        clear_cache();
        auto data=e->GetByteArrayElements(rgb,nullptr); auto bitmap=mtmd_bitmap_init(width,height,(unsigned char*)data); e->ReleaseByteArrayElements(rgb,data,JNI_ABORT);
        auto chunks=mtmd_input_chunks_init(); mtmd_input_text text{formatted.data(),(size_t)n,true,true}; const mtmd_bitmap * bitmaps[]={bitmap};
        int code=mtmd_tokenize(vision,chunks,&text,bitmaps,1);
        size_t tokens=0; for(size_t i=0;i<mtmd_input_chunks_size(chunks);i++) tokens+=mtmd_input_chunk_get_n_tokens(mtmd_input_chunks_get(chunks,i));
        progress.emit("image",0,(int)tokens);
        if(!code && tokens+8<(size_t)context_size) code=mtmd_helper_eval_chunks(vision,ctx,chunks,0,0,llama_n_batch(ctx),true,&past); else code=1;
        mtmd_input_chunks_free(chunks); mtmd_bitmap_free(bitmap);
        if(!code) output_limit=std::min(output_limit,std::max(1,context_size-(int)past-1));
        if(cancelled) return;
        if(code) { fail(e,"No se pudo procesar la imagen o el contexto es demasiado largo. Inicia un chat nuevo."); return; }
    } else {
        int nt=-llama_tokenize(vocab,formatted.data(),n,nullptr,0,true,true);
        if(nt<=0 || nt+8>=context_size) { fail(e,"Contexto completo. Inicia un chat nuevo."); return; }
        output_limit=std::min(output_limit,context_size-nt-1);
        std::vector<llama_token> tokens(nt); llama_tokenize(vocab,formatted.data(),n,tokens.data(),nt,true,true);
        // Reuse only the exact token prefix already present in KV, retaining at
        // least one fresh input token to produce valid logits for sampling.
        int common=0;
        while(common<nt-1 && common<(int)prompt_cache.size() && tokens[common]==prompt_cache[common]) common++;
        if(!common || !llama_memory_seq_rm(llama_get_memory(ctx),0,common,-1)) {
            clear_cache(); common=0;
        } else prompt_cache.resize(common);
        reused_tokens=common;
        // Never submit more than n_batch: llama.cpp aborts the process otherwise.
        const int batch_size=(int)llama_n_batch(ctx);
        progress.emit("prompt",common,nt);
        for(int i=common;i<nt;i+=batch_size) {
            int len=std::min(batch_size,nt-i); auto batch=llama_batch_get_one(tokens.data()+i,len);
            if(cancelled) { clear_cache(); return; }
            int code=llama_decode(ctx,batch);
            if(cancelled) { clear_cache(); return; }
            if(code) { clear_cache(); fail(e,"Error al procesar el contexto. Intenta un contexto menor."); return; }
            prompt_cache.insert(prompt_cache.end(),tokens.begin()+i,tokens.begin()+i+len);
            progress.emit("prompt",i+len,nt);
        } past=nt;
    }
    progress.emit("generate",0,output_limit);
    auto sampler=llama_sampler_chain_init(llama_sampler_chain_default_params());
    llama_sampler_chain_add(sampler,llama_sampler_init_top_k(40)); llama_sampler_chain_add(sampler,llama_sampler_init_top_p(0.9f,1)); llama_sampler_chain_add(sampler,llama_sampler_init_temp(0.7f)); llama_sampler_chain_add(sampler,llama_sampler_init_dist(LLAMA_DEFAULT_SEED));
    auto cls=e->GetObjectClass(sink); auto method=e->GetMethodID(cls,"onToken","([B)V");
    bool emitted=false;
    for(int i=0;i<output_limit && !cancelled && past<context_size;i++,past++) {
        auto token=llama_sampler_sample(sampler,ctx,-1); if(llama_vocab_is_eog(vocab,token)) break;
        generated_tokens++; llama_sampler_accept(sampler,token); std::vector<char> piece(1024); int len=llama_token_to_piece(vocab,token,piece.data(),piece.size(),0,false);
        if(len<0) { piece.resize(-len); len=llama_token_to_piece(vocab,token,piece.data(),piece.size(),0,false); }
        if(len>0) { emitted=true; auto bytes=e->NewByteArray(len); e->SetByteArrayRegion(bytes,0,len,(jbyte*)piece.data()); e->CallVoidMethod(sink,method,bytes); e->DeleteLocalRef(bytes); if(e->ExceptionCheck()) break; }
        if(cancelled || i+1==output_limit) break;
        auto batch=llama_batch_get_one(&token,1); int code=llama_decode(ctx,batch);
        if(cancelled) { clear_cache(); break; }
        if(code) { clear_cache(); fail(e,"Error durante la generación."); break; }
        if(!rgb) prompt_cache.push_back(token);
    }
    generation_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
    llama_sampler_free(sampler); e->DeleteLocalRef(cls);
    if(!emitted && !cancelled && !e->ExceptionCheck())
        fail(e,"El modelo terminó sin devolver texto. Reintenta el mensaje o vuelve a cargar el modelo.");
}

extern "C" JNIEXPORT jstring JNICALL Java_com_ailocal_app_Engine_stats(JNIEnv * e,jclass) {
    std::ostringstream out;
    out << "{\"context\":" << (ctx?llama_n_ctx(ctx):0)
        << ",\"modelBytes\":" << (model?llama_model_size(model):0)
        << ",\"cancelled\":" << (cancelled?"true":"false")
        << ",\"compactKv\":" << (compact_kv?"true":"false")
        << ",\"cachedTokens\":" << reused_tokens
        << ",\"generatedTokens\":" << generated_tokens
        << ",\"generationMs\":" << generation_ms << "}";
    return e->NewStringUTF(out.str().c_str());
}
