#include <jni.h>
#include <atomic>
#include <chrono>
#include <sstream>
#include <string>
#include <vector>
#include <stdexcept>
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
static std::string str(JNIEnv * e, jstring s) { auto cls=e->GetObjectClass(s); auto method=e->GetMethodID(cls,"getBytes","(Ljava/lang/String;)[B"); auto charset=e->NewStringUTF("UTF-8"); auto bytes=(jbyteArray)e->CallObjectMethod(s,method,charset); auto p=e->GetByteArrayElements(bytes,nullptr); std::string v((char*)p,e->GetArrayLength(bytes)); e->ReleaseByteArrayElements(bytes,p,JNI_ABORT); e->DeleteLocalRef(bytes); e->DeleteLocalRef(charset); e->DeleteLocalRef(cls); return v; }
static void fail(JNIEnv * e, const char * msg) { e->ThrowNew(e->FindClass("java/lang/IllegalStateException"),msg); }
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_stop(JNIEnv *,jclass) { cancelled=true; }
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_unload(JNIEnv *,jclass) {
    if(vision) mtmd_free(vision); if(ctx) llama_free(ctx); if(model) llama_model_free(model);
    vision=nullptr; ctx=nullptr; model=nullptr;
}
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_load(JNIEnv * e,jclass c,jstring path,jstring projector,jint threads,jint context) {
    cancelled=false; Java_com_ailocal_app_Engine_unload(e,c); llama_backend_init();
    auto mp=llama_model_default_params(); mp.n_gpu_layers=0; mp.load_mode=LLAMA_LOAD_MODE_MMAP; mp.progress_callback=[](float,void*){return !cancelled.load();};
    model=llama_model_load_from_file(str(e,path).c_str(),mp);
    if(!model) { fail(e,cancelled?"Carga detenida.":"No se pudo abrir el GGUF. Comprueba el archivo y la RAM disponible."); return; }
    auto cp=llama_context_default_params(); cp.n_ctx=std::max(512,std::min(4096,(int)context)); cp.n_batch=128; cp.n_ubatch=64; cp.type_k=GGML_TYPE_Q8_0; cp.type_v=GGML_TYPE_F16; cp.n_threads=threads; cp.n_threads_batch=threads;
    compact_kv=true;
    ctx=llama_init_from_model(model,cp);
    if(!ctx) { cp.type_k=GGML_TYPE_F16; compact_kv=false; ctx=llama_init_from_model(model,cp); }
    if(!ctx) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"RAM insuficiente para crear el contexto."); return; }
    if(cancelled) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"Carga detenida."); return; }
    auto p=str(e,projector);
    if(!p.empty()) { auto vp=mtmd_context_params_default(); vp.use_gpu=false; vp.n_threads=threads; vp.image_max_tokens=512;
        vision=mtmd_init_from_file(p.c_str(),model,vp);
        if(!vision) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"No se pudo cargar el proyector visual."); }
    }
}
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_generate(JNIEnv * e,jclass,jobjectArray roles,jobjectArray texts,jbyteArray rgb,jint width,jint height,jint maxTokens,jobject sink) {
    if(!ctx) { fail(e,"Selecciona y carga un modelo."); return; }
    auto started=std::chrono::steady_clock::now(); generated_tokens=0; generation_ms=0;
    const int context_size=(int)llama_n_ctx(ctx);
    int output_limit=std::max(1,std::min((int)maxTokens,2048));
    cancelled=false; llama_memory_clear(llama_get_memory(ctx),true);
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
        auto data=e->GetByteArrayElements(rgb,nullptr); auto bitmap=mtmd_bitmap_init(width,height,(unsigned char*)data); e->ReleaseByteArrayElements(rgb,data,JNI_ABORT);
        auto chunks=mtmd_input_chunks_init(); mtmd_input_text text{formatted.data(),(size_t)n,true,true}; const mtmd_bitmap * bitmaps[]={bitmap};
        int code=mtmd_tokenize(vision,chunks,&text,bitmaps,1);
        size_t tokens=0; for(size_t i=0;i<mtmd_input_chunks_size(chunks);i++) tokens+=mtmd_input_chunk_get_n_tokens(mtmd_input_chunks_get(chunks,i));
        if(!code && tokens+8<(size_t)context_size) code=mtmd_helper_eval_chunks(vision,ctx,chunks,0,0,256,true,&past); else code=1;
        mtmd_input_chunks_free(chunks); mtmd_bitmap_free(bitmap);
        if(!code) output_limit=std::min(output_limit,std::max(1,context_size-(int)past-1));
        if(code) { fail(e,"No se pudo procesar la imagen o el contexto es demasiado largo. Inicia un chat nuevo."); return; }
    } else {
        int nt=-llama_tokenize(vocab,formatted.data(),n,nullptr,0,true,true);
        if(nt<=0 || nt+8>=context_size) { fail(e,"Contexto completo. Inicia un chat nuevo."); return; }
        output_limit=std::min(output_limit,context_size-nt-1);
        std::vector<llama_token> tokens(nt); llama_tokenize(vocab,formatted.data(),n,tokens.data(),nt,true,true);
        for(int i=0;i<nt;i+=256) { int len=std::min(256,nt-i); auto batch=llama_batch_get_one(tokens.data()+i,len); if(cancelled) return; if(llama_decode(ctx,batch)) { fail(e,"Error al procesar el contexto."); return; } } past=nt;
    }
    auto sampler=llama_sampler_chain_init(llama_sampler_chain_default_params());
    llama_sampler_chain_add(sampler,llama_sampler_init_top_k(40)); llama_sampler_chain_add(sampler,llama_sampler_init_top_p(0.9f,1)); llama_sampler_chain_add(sampler,llama_sampler_init_temp(0.7f)); llama_sampler_chain_add(sampler,llama_sampler_init_dist(LLAMA_DEFAULT_SEED));
    auto cls=e->GetObjectClass(sink); auto method=e->GetMethodID(cls,"onToken","([B)V");
    for(int i=0;i<output_limit && !cancelled && past<context_size;i++,past++) {
        auto token=llama_sampler_sample(sampler,ctx,-1); if(llama_vocab_is_eog(vocab,token)) break;
        generated_tokens++; llama_sampler_accept(sampler,token); char piece[1024]; int len=llama_token_to_piece(vocab,token,piece,sizeof(piece),0,false);
        if(len>0) { auto bytes=e->NewByteArray(len); e->SetByteArrayRegion(bytes,0,len,(jbyte*)piece); e->CallVoidMethod(sink,method,bytes); e->DeleteLocalRef(bytes); if(e->ExceptionCheck()) break; }
        auto batch=llama_batch_get_one(&token,1); if(llama_decode(ctx,batch)) { fail(e,"Error durante la generación."); break; }
    }
    generation_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
    llama_sampler_free(sampler); e->DeleteLocalRef(cls);
}

extern "C" JNIEXPORT jstring JNICALL Java_com_ailocal_app_Engine_stats(JNIEnv * e,jclass) {
    std::ostringstream out;
    out << "{\"context\":" << (ctx?llama_n_ctx(ctx):0)
        << ",\"modelBytes\":" << (model?llama_model_size(model):0)
        << ",\"cancelled\":" << (cancelled?"true":"false")
        << ",\"compactKv\":" << (compact_kv?"true":"false")
        << ",\"generatedTokens\":" << generated_tokens
        << ",\"generationMs\":" << generation_ms << "}";
    return e->NewStringUTF(out.str().c_str());
}
