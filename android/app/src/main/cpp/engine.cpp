#include <jni.h>
#include <atomic>
#include <chrono>
#include <sstream>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstdio>
#include <fstream>
#include <algorithm>
#include "ggml-backend.h"
#if defined(__linux__)
#include <sched.h>
#endif
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
static std::string finish_reason = "";
static int context_shifts = 0, trimmed_tokens = 0;
static double generation_ms = 0;
static bool compact_kv = false;
static std::vector<llama_token> prompt_cache;
static int reused_tokens = 0;
static std::string projector_path, vision_base;
static uint64_t vision_hash = 0;
static llama_pos vision_past = 0;
static int vision_budget = 256, thread_count = 1, prompt_tokens = 0, image_tokens = 0;
static double prompt_ms = 0, image_ms = 0, decode_ms = 0, first_token_ms = 0;
static bool reused_image = false, image_processed = false;
static ggml_threadpool_t threadpool = nullptr;
static void (*free_pool)(ggml_threadpool_t) = nullptr;
static double elapsed(std::chrono::steady_clock::time_point start) {
    return std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
}
static std::string cpu_features() {
    auto reg=ggml_backend_reg_by_name("CPU"); if(!reg) return "missing";
    auto fn=(ggml_backend_get_features_t)ggml_backend_reg_get_proc_address(reg,"ggml_backend_get_features");
    std::string features;
    if(fn) for(auto p=fn(reg);p && p->name;p++) if(std::string(p->value)=="1") {
        if(!features.empty()) features+=" "; features+=p->name;
    }
    return features;
}
static int usable_threads(int requested) {
    int allowed = std::max(1, requested);
#if defined(__linux__)
    cpu_set_t mask; CPU_ZERO(&mask);
    if(sched_getaffinity(0,sizeof(mask),&mask)==0) allowed=std::min(allowed,CPU_COUNT(&mask));
    std::ifstream quota("/sys/fs/cgroup/cpu.max"); std::string limit; long period;
    if(quota>>limit>>period && limit!="max" && period>0) {
        try { allowed=std::min(allowed,(int)std::max(1L,std::stol(limit)/period)); } catch(...) {}
    }
#endif
    return std::max(1,allowed);
}
static void clear_cache() {
    prompt_cache.clear();
    vision_base.clear(); vision_hash=0; vision_past=0;
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
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_configureBackends(JNIEnv * e,jclass,jstring directory) {
    static bool loaded=false;
    if(!loaded) { ggml_backend_load_all_from_path(str(e,directory).c_str()); loaded=true; }
    if(!ggml_backend_reg_by_name("CPU")) fail(e,"Falta el backend CPU en el APK. Reinstala la actualización completa.");
}
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_stop(JNIEnv *,jclass) { cancelled=true; }
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_unload(JNIEnv *,jclass) {
    if(vision) mtmd_free(vision); if(ctx) llama_free(ctx);
    if(threadpool && free_pool) free_pool(threadpool); threadpool=nullptr;
    if(model) llama_model_free(model);
    vision=nullptr; ctx=nullptr; model=nullptr;
    prompt_cache.clear(); reused_tokens=0;
    projector_path.clear(); vision_base.clear(); vision_hash=0; vision_past=0;
}
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_loadConfigured(JNIEnv * e,jclass c,jstring path,jstring projector,jint threads,jint context,jint imageBudget,jobject observer) {
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
    thread_count=usable_threads(threads);
    auto cp=llama_context_default_params(); cp.n_ctx=std::max(512,std::min(4096,(int)context)); cp.n_batch=128; cp.n_ubatch=64; cp.type_k=GGML_TYPE_Q8_0; cp.type_v=GGML_TYPE_F16; cp.n_threads=thread_count; cp.n_threads_batch=thread_count;
    cp.abort_callback=[](void*){ return cancelled.load(); };
    progress.emit("context",0,0);
    compact_kv=true;
    ctx=llama_init_from_model(model,cp);
    if(!ctx) { cp.type_k=GGML_TYPE_F16; compact_kv=false; ctx=llama_init_from_model(model,cp); }
    if(!ctx) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"El motor no pudo crear el contexto. Intenta un contexto menor."); return; }
    auto reg=ggml_backend_reg_by_name("CPU");
    if(reg) {
        auto create=(ggml_threadpool_t(*)(ggml_threadpool_params*))ggml_backend_reg_get_proc_address(reg,"ggml_threadpool_new");
        free_pool=(void(*)(ggml_threadpool_t))ggml_backend_reg_get_proc_address(reg,"ggml_threadpool_free");
        if(create && free_pool) {
            auto params=ggml_threadpool_params_default(thread_count); params.poll=0;
            threadpool=create(&params); if(threadpool) llama_attach_threadpool(ctx,threadpool,threadpool);
        }
    }
    if(cancelled) { Java_com_ailocal_app_Engine_unload(e,c); fail(e,"Carga detenida."); return; }
    // Keep the ~0.85 GB Qwen visual encoder out of RAM during text generation.
    // It is loaded lazily for image encoding and released before sampling.
    projector_path=str(e,projector); vision_budget=std::max(128,std::min(512,(int)imageBudget));
}
extern "C" JNIEXPORT void JNICALL Java_com_ailocal_app_Engine_generateImage(JNIEnv * e,jclass,jobjectArray roles,jobjectArray texts,jbyteArray rgb,jint width,jint height,jint maxTokens,jobject sink,jobject observer,jint imageIndex,jboolean allowHistoryWindow) {
    if(!ctx) { fail(e,"Selecciona y carga un modelo."); return; }
    auto started=std::chrono::steady_clock::now(); finish_reason="error"; context_shifts=trimmed_tokens=0; generated_tokens=0; generation_ms=0; reused_tokens=0;
    prompt_ms=image_ms=decode_ms=first_token_ms=0; prompt_tokens=image_tokens=0; reused_image=image_processed=false;
    const int context_size=(int)llama_n_ctx(ctx);
    const int requested_limit=std::max(1,std::min((int)maxTokens,2048));
    int output_limit=requested_limit;
    cancelled=false;
    Progress progress(e,observer);
    std::vector<std::string> rs,ts; int count=e->GetArrayLength(texts);
    for(int i=0;i<count;i++) { auto r=(jstring)e->GetObjectArrayElement(roles,i); auto t=(jstring)e->GetObjectArrayElement(texts,i); rs.push_back(str(e,r)); ts.push_back(str(e,t)); e->DeleteLocalRef(r); e->DeleteLocalRef(t); }
    if(rgb) {
        if(projector_path.empty()) { fail(e,"Este modelo solo admite texto. Selecciona un modelo de visión para imágenes."); return; }
        if(imageIndex<0 || imageIndex>=count || width<=0 || height<=0 || e->GetArrayLength(rgb)!=(jlong)width*height*3) {
            fail(e,"La imagen no llegó completa al motor. Vuelve a adjuntarla."); return;
        }
        ts[imageIndex]=std::string(mtmd_default_marker())+"\n"+ts[imageIndex];
    }
    std::vector<llama_chat_message> messages; for(int i=0;i<count;i++) messages.push_back({rs[i].c_str(),ts[i].c_str()});
    const char * tmpl=llama_model_chat_template(model,nullptr);
    int n=llama_chat_apply_template(tmpl,messages.data(),messages.size(),true,nullptr,0);
    if(n<0) { fail(e,"Plantilla de chat incompatible con el motor."); return; }
    std::vector<char> formatted(n+1); llama_chat_apply_template(tmpl,messages.data(),messages.size(),true,formatted.data(),formatted.size());
    auto vocab=llama_model_get_vocab(model); llama_pos past=0;
    auto decode_text=[&](const char * data,int size,bool special,int start)->bool {
        int nt=-llama_tokenize(vocab,data,size,nullptr,0,special,true);
        if(nt<=0 || nt+start+8>=context_size) { fail(e,"Contexto completo. Reduce el historial o aumenta el contexto en el perfil."); return false; }
        std::vector<llama_token> tokens(nt); llama_tokenize(vocab,data,size,tokens.data(),nt,special,true);
        progress.emit("prompt",0,nt);
        for(int i=0;i<nt;i+=(int)llama_n_batch(ctx)) {
            int len=std::min((int)llama_n_batch(ctx),nt-i); auto batch=llama_batch_get_one(tokens.data()+i,len);
            if(cancelled) { clear_cache(); return false; }
            int code=llama_decode(ctx,batch);
            if(cancelled) { clear_cache(); return false; }
            if(code) { clear_cache(); fail(e,"No se pudo procesar el mensaje."); return false; }
            progress.emit("prompt",i+len,nt);
        }
        prompt_tokens=nt; past=start+nt; return true;
    };
    if(rgb) {
        auto image_started=std::chrono::steady_clock::now();
        auto data_hash=e->GetByteArrayElements(rgb,nullptr); uint64_t hash=1469598103934665603ULL;
        for(jsize i=0;i<e->GetArrayLength(rgb);i++) { hash^=(unsigned char)data_hash[i]; hash*=1099511628211ULL; }
        e->ReleaseByteArrayElements(rgb,data_hash,JNI_ABORT); hash^=((uint64_t)width<<32)|(uint32_t)height;
        if(hash==vision_hash && !vision_base.empty() && (size_t)n>vision_base.size()
            && std::string(formatted.data(),n).compare(0,vision_base.size(),vision_base)==0
            && llama_memory_seq_rm(llama_get_memory(ctx),0,vision_past,-1)) {
            reused_image=true; auto base=vision_base.size(); int prefix=vision_past;
            if(!decode_text(formatted.data()+base,n-base,false,prefix)) return;
            prompt_ms=elapsed(image_started);
        } else {
        clear_cache(); progress.emit("vision",0,0);
        auto vp=mtmd_context_params_default(); vp.use_gpu=false; vp.n_threads=thread_count;
        vp.image_min_tokens=64; vp.image_max_tokens=vision_budget; vp.warmup=false;
        vp.progress_callback=[](float,void*){return !cancelled.load();};
        vision=mtmd_init_from_file(projector_path.c_str(),model,vp);
        if(!vision) { fail(e,cancelled?"Procesamiento detenido.":"No se pudo abrir el proyector de la imagen."); return; }
        auto data=e->GetByteArrayElements(rgb,nullptr); auto bitmap=mtmd_bitmap_init(width,height,(unsigned char*)data); e->ReleaseByteArrayElements(rgb,data,JNI_ABORT);
        auto chunks=mtmd_input_chunks_init(); mtmd_input_text text{formatted.data(),(size_t)n,true,true}; const mtmd_bitmap * bitmaps[]={bitmap};
        int code=mtmd_tokenize(vision,chunks,&text,bitmaps,1);
        size_t tokens=0; for(size_t i=0;i<mtmd_input_chunks_size(chunks);i++) tokens+=mtmd_input_chunk_get_n_tokens(mtmd_input_chunks_get(chunks,i));
        for(size_t i=0;i<mtmd_input_chunks_size(chunks);i++) {
            auto chunk=mtmd_input_chunks_get(chunks,i);
            if(mtmd_input_chunk_get_type(chunk)==MTMD_INPUT_CHUNK_TYPE_IMAGE) image_tokens+=(int)mtmd_input_chunk_get_n_tokens(chunk);
        }
        progress.emit("image",0,(int)tokens);
        if(!code && tokens+8<(size_t)context_size) code=mtmd_helper_eval_chunks(vision,ctx,chunks,0,0,llama_n_batch(ctx),true,&past); else code=1;
        mtmd_input_chunks_free(chunks); mtmd_bitmap_free(bitmap);
        mtmd_free(vision); vision=nullptr;
        if(!code) output_limit=std::min(output_limit,std::max(1,context_size-(int)past-1));
        if(cancelled) return;
        if(code) { fail(e,"No se pudo procesar la imagen o el contexto es demasiado largo. Inicia un chat nuevo."); return; }
        image_ms=elapsed(image_started); vision_base.assign(formatted.data(),n); vision_hash=hash; vision_past=past;
        }
    } else {
        int nt=-llama_tokenize(vocab,formatted.data(),n,nullptr,0,true,true);
        if(nt<=0) { fail(e,"No se pudo preparar el mensaje."); return; }
        std::vector<llama_token> tokens(nt); llama_tokenize(vocab,formatted.data(),n,tokens.data(),nt,true,true);
        if(nt+8>=context_size) {
            if(!allowHistoryWindow) { fail(e,"El archivo y el historial exceden el contexto. Aumenta el contexto o selecciona un fragmento menor del archivo."); return; }
            // Keep the system prefix and the newest conversation tail. Never
            // silently truncate an oversized new user message or workspace.
            int keep=std::min(256,context_size/4), tail=context_size-keep-128;
            int latest=0;
            for(int i=count-1;i>=0;i--) if(rs[i]=="user") {
                latest=-llama_tokenize(vocab,ts[i].data(),ts[i].size(),nullptr,0,false,true); break;
            }
            if(latest>=tail || count<=2) { fail(e,"Contexto completo. Reduce el mensaje o aumenta el contexto en el perfil."); return; }
            trimmed_tokens=nt-keep-tail;
            tokens.erase(tokens.begin()+keep,tokens.end()-tail);
            nt=(int)tokens.size();
        }
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
        prompt_tokens=nt; auto prompt_started=std::chrono::steady_clock::now();
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
        prompt_ms=elapsed(prompt_started);
    }
    image_processed=rgb!=nullptr;
    if(rgb) output_limit=std::min(output_limit,context_size-(int)past-1);
    finish_reason=rgb && output_limit<requested_limit ? "context" : "length";
    progress.emit("generate",0,output_limit);
    auto sampler=llama_sampler_chain_init(llama_sampler_chain_default_params());
    // Image reading/OCR should use the highest-probability interpretation,
    // rather than randomly choosing another color or word at temperature 0.7.
    if(rgb) llama_sampler_chain_add(sampler,llama_sampler_init_greedy());
    else {
        llama_sampler_chain_add(sampler,llama_sampler_init_top_k(40)); llama_sampler_chain_add(sampler,llama_sampler_init_top_p(0.9f,1)); llama_sampler_chain_add(sampler,llama_sampler_init_temp(0.7f)); llama_sampler_chain_add(sampler,llama_sampler_init_dist(LLAMA_DEFAULT_SEED));
    }
    auto cls=e->GetObjectClass(sink); auto method=e->GetMethodID(cls,"onToken","([B)V");
    bool emitted=false;
    auto decode_started=std::chrono::steady_clock::now();
    for(int i=0;i<output_limit && !cancelled && past<context_size;i++,past++) {
        auto token=llama_sampler_sample(sampler,ctx,-1); if(llama_vocab_is_eog(vocab,token)) { finish_reason="eos"; break; }
        generated_tokens++; llama_sampler_accept(sampler,token); std::vector<char> piece(1024); int len=llama_token_to_piece(vocab,token,piece.data(),piece.size(),0,false);
        if(len<0) { piece.resize(-len); len=llama_token_to_piece(vocab,token,piece.data(),piece.size(),0,false); }
        if(len>0) { if(!emitted) first_token_ms=elapsed(started); emitted=true; auto bytes=e->NewByteArray(len); e->SetByteArrayRegion(bytes,0,len,(jbyte*)piece.data()); e->CallVoidMethod(sink,method,bytes); e->DeleteLocalRef(bytes); if(e->ExceptionCheck()) break; }
        if(cancelled || i+1==output_limit) break;
        if(past+1>=context_size) {
            auto memory=llama_get_memory(ctx);
            const int keep=std::min(256,context_size/4);
            const int discard=((int)past-keep)/2;
            if(rgb || !llama_memory_can_shift(memory) || discard<=0
                || !llama_memory_seq_rm(memory,0,keep,keep+discard)) {
                finish_reason="context"; break;
            }
            llama_memory_seq_add(memory,0,keep+discard,past,-discard);
            past-=discard;
            context_shifts++;
            // A shifted KV no longer represents an exact original prefix.
            prompt_cache.clear(); vision_base.clear(); vision_hash=0; vision_past=0;
        }
        auto batch=llama_batch_get_one(&token,1); int code=llama_decode(ctx,batch);
        if(cancelled) { clear_cache(); break; }
        if(code) { clear_cache(); fail(e,"Error durante la generación."); break; }
        if(!rgb && !context_shifts) prompt_cache.push_back(token);
    }
    generation_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
    decode_ms=elapsed(decode_started);
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
        << ",\"finishReason\":\"" << (cancelled ? "cancelled" : finish_reason) << "\""
        << ",\"contextShifts\":" << context_shifts << ",\"trimmedTokens\":" << trimmed_tokens
        << ",\"threads\":" << thread_count << ",\"promptTokens\":" << prompt_tokens
        << ",\"cpuFeatures\":\"" << cpu_features() << "\""
        << ",\"imageTokens\":" << image_tokens << ",\"imageReused\":" << (reused_image?"true":"false")
        << ",\"imageProcessed\":" << (image_processed?"true":"false")
        << ",\"promptMs\":" << prompt_ms << ",\"imageMs\":" << image_ms
        << ",\"decodeMs\":" << decode_ms << ",\"firstTokenMs\":" << first_token_ms
        << ",\"generationMs\":" << generation_ms << "}";
    return e->NewStringUTF(out.str().c_str());
}
