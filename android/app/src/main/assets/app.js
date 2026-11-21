'use strict';
const $=id=>document.getElementById(id), command=(action,data={})=>{if(window.Native)Native.command(action,JSON.stringify(data));};
let conversationModel=localStorage.getItem('chatModel')||'';
let state={models:[],installed:[],ram:0,available:0},filter='powerful',messages=[],running=false,attachment=false,answer='',fileSha='',opened=null,pending=null;
try{messages=JSON.parse(localStorage.getItem('chat')||'[]');if(!Array.isArray(messages))messages=[];}catch(_){messages=[];}
function assessModel(model, device=state) {
 const reasons=[];
 const installed=(device.installed||[]).includes(model.id);
 if(device.lowMemory) reasons.push('Android informa de memoria baja.');
 if(device.pressure) reasons.push('Se detecta presión de memoria en el sistema.');
 const bytes=model.files.reduce((sum,file)=>sum+file.size,0);
 if(!Number.isFinite(device.ram)||!Number.isFinite(device.budget)) reasons.push('No se pudieron comprobar los recursos.');
 else {
  if(device.ram<model.ram) reasons.push('RAM total: '+device.ram.toFixed(1)+' / '+model.ram+' GB mínimos.');
  if(device.budget<model.memory) reasons.push('Presupuesto IA: '+device.budget.toFixed(1)+' / '+model.memory+' GB estimados.');
 }
 if(!installed&&(!Number.isFinite(device.storage)||device.storage*1073741824<bytes+268435456)) reasons.push('Espacio insuficiente: se necesitan '+((bytes+268435456)/1073741824).toFixed(1)+' GB libres.');
 return {recommended:reasons.length===0,reasons,bytes};
}
function visibleModels(){
 const query=$('modelSearch').value.trim().toLocaleLowerCase('es');
 return state.models.filter(m=>(filter==='all'||filter==='powerful'&&m.parameters>=5||filter===m.kind||filter==='installed'&&state.installed.includes(m.id))&&(!query||(m.name+' '+m.repo+' '+m.description).toLocaleLowerCase('es').includes(query)));
}
$('modelSearch').oninput=()=>renderModels();
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function toast(text,error=false){$('toast').textContent=text||'Ocurrió un error';$('toast').className=error?'error':'';clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').className='hidden',7500);}
function confirmAction(title,text,fn){$('confirmTitle').textContent=title;$('confirmText').textContent=text;pending=fn;$('confirm').showModal();}
$('confirmNo').onclick=()=>{$('confirm').close();pending=null;};$('confirmYes').onclick=()=>{$('confirm').close();if(pending)pending();pending=null;};
function page(id){document.querySelectorAll('.page').forEach(p=>p.classList.toggle('hidden',p.id!==id));document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('current',b.dataset.page===id));window.scrollTo(0,0);}
document.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>page(b.dataset.page));document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('selected',x===b));renderModels();});
function renderModels(){
 const root=$('models');root.replaceChildren();
 const visible=visibleModels();
 $('catalogCount').textContent=state.models.length+' modelos · '+state.models.filter(m=>m.parameters>=5).length+' de 5B+';
 $('resultCount').textContent=visible.length+' modelos en esta vista';
 visible.forEach(m=>{
  const assessment=assessModel(m),available=state.installed.includes(m.id);
  const card=el('article','card'+(m.vision?' visual':''));card.dataset.model=m.id;
  const top=el('div','modeltop'),icon=el('div','modelicon',m.vision?'◉':m.kind==='reasoning'?'◇':'⌘'),title=el('div');
  const category={vision:'IMAGEN + TEXTO',code:'CÓDIGO',reasoning:'RAZONAMIENTO',chat:'CONVERSACIÓN'}[m.kind];
  title.append(el('h3','',m.name),el('small','',category+' · '+m.parameters+'B · '+m.quant));top.append(icon,title);
  card.append(top,el('p','',m.description));
  const stats=el('div','stats');stats.append(el('span','',(assessment.bytes/1e9).toFixed(2)+' GB de descarga'),el('span','',m.ram+' GB RAM total mínima'),el('span','',m.memory+' GB de presupuesto IA estimado'));card.append(stats);
  const status=el('div','recommendation'+(!assessment.recommended?' not-recommended':''));
  status.append(el('strong','',assessment.recommended?'Dentro de recursos estimados':'No recomendado'));
  if(!assessment.recommended)status.append(el('small','',assessment.reasons.join(' ')));
  else status.append(el('small','','La velocidad y el consumo real dependen del procesador y del contexto.'));
  card.append(status);
  const actions=el('div','actions'),btn=el('button',available?'secondary':'primary',available?(state.active===m.id?'En uso ✓':'Usar modelo'):'Descargar ↓');
  btn.onclick=()=>{
   if(available){
    if(running)return;
    const load=()=>{setBusy(true);toast('Cargando modelo en memoria…');command('load',{id:m.id});};
    if(!assessment.recommended)confirmAction('No recomendado para tu dispositivo',assessment.reasons.join('\n')+'\nSe volverán a medir los recursos antes de cargarlo. Si el presupuesto IA sigue siendo insuficiente, se conservará la descarga sin cargar el modelo.',load);else load();
   }else{
    const warning=assessment.recommended?'': 'No recomendado para tu dispositivo.\n'+assessment.reasons.join('\n')+'\n\n';
    confirmAction('Descargar '+m.name,warning+(assessment.bytes/1e9).toFixed(2)+' GB. Se recomienda Wi-Fi. La descarga no garantiza que el teléfono pueda ejecutar el modelo.',()=>command('download',{id:m.id}));
   }
  };
  actions.append(btn);card.append(actions);
  const progress=el('div','hidden');progress.id='progress-'+m.id;card.append(progress);
  if(available){const remove=el('button','quiet','Eliminar del teléfono');remove.onclick=()=>confirmAction('Eliminar modelo','Se borrarán los archivos descargados de '+m.name+'.',()=>command('delete',{id:m.id}));card.append(remove);}
  root.append(card);
 });
 if(!root.children.length)root.append(el('div','empty','No hay modelos que coincidan con estos filtros.'));
}
function renderChat(){const root=$('messages');if(!messages.length&&!running){root.innerHTML='<div class="empty">Un espacio para pensar, escribir y construir.<small>Carga un modelo desde la Biblioteca para empezar.</small></div>';return;}root.replaceChildren();for(const m of messages){if(m.role==='system')continue;const b=el('div','bubble '+m.role);b.append(el('small','',m.role==='user'?'Tú':'AI Local'),el('span','',m.content));if(m.role==='assistant'){const edit=el('button','quiet','Llevar al editor GitHub ↗');edit.onclick=()=>{if(!opened||!fileSha)return toast('Primero abre el archivo que deseas editar en GitHub.',true);confirmAction('Copiar al editor','La respuesta sustituirá el contenido del editor. Podrás revisarlo antes de guardar.',()=>{const match=m.content.match(/^```[^\n]*\n([\s\S]*?)\n```\s*$/);$('editor').value=match?match[1]:m.content;page('github');toast('Contenido en el editor. Revísalo antes de guardar.');});};b.append(edit);}root.append(b);}if(running){const b=el('div','bubble assistant');b.append(el('small','','AI Local'),el('span','',answer||'Pensando en tu dispositivo…'));root.append(b);}}
function persist(){localStorage.setItem('chat',JSON.stringify(messages));if(state.active)conversationModel=state.active;localStorage.setItem('chatModel',conversationModel);}
function setBusy(value){running=value;$('send').disabled=value;$('attach').disabled=value;$('newChat').disabled=value;$('stop').classList.toggle('hidden',!value);$('send').classList.toggle('hidden',value);}
$('send').onclick=()=>{const text=$('prompt').value.trim();if(!text||running)return;if(!state.active)return toast('Carga un modelo desde la Biblioteca.',true);const m=state.models.find(m=>m.id===state.active);if(attachment&&!m.vision)return toast('Selecciona un modelo de Visión para interpretar imágenes.',true);messages.push({role:'user',content:text});persist();$('prompt').value='';answer='';setBusy(true);renderChat();command('chat',{messages:[{role:'system',content:'Eres un asistente útil. Responde en español con precisión.'},...messages]});};
$('stop').onclick=()=>{command('stop');toast('Deteniendo la generación…');};$('newChat').onclick=()=>confirmAction('Nueva conversación','Se borrará el historial de este chat del teléfono.',()=>{messages=[];persist();command('clearImage');renderChat();});
$('attach').onclick=()=>{const m=state.models.find(m=>m.id===state.active);if(!m?.vision)return toast('Carga un modelo de Visión en la Biblioteca para enviar imágenes.',true);command('image');};$('removeImage').onclick=()=>command('clearImage');
$('connect').onclick=()=>{const token=$('token').value;if(!token.trim())return toast('Introduce un token de GitHub.',true);command('connect',{token});$('token').value='';};$('disconnect').onclick=()=>command('disconnect');$('repos').onclick=()=>command('repos');
$('repoSelect').onchange=()=>{const opt=$('repoSelect').selectedOptions[0];$('branch').value=opt.dataset.branch||'main';fileSha='';opened=null;$('editorArea').classList.add('hidden');$('directory').replaceChildren();};
$('read').onclick=()=>{fileSha='';opened={repo:$('repoSelect').value,branch:$('branch').value,path:$('filepath').value};$('editorArea').classList.add('hidden');command('read',opened);};
$('save').onclick=()=>{if(!fileSha||!opened)return toast('Abre el archivo antes de guardarlo.',true);if(!($('commit').value.trim()))return toast('Escribe el mensaje del commit.',true);const data={...opened,sha:fileSha,text:$('editor').value,message:$('commit').value};confirmAction('Guardar en GitHub',data.repo+' · '+data.branch+'\n'+data.path+'\n\n'+data.message+'\n\nSe creará un commit con el contenido visible en el editor.',()=>{ $('save').disabled=true;command('write',data);});};
window.receive=(type,data)=>{switch(type){
 case 'state':{const was=state.connected;state=data;renderResources(data);$('activeModel').textContent=data.models.find(m=>m.id===data.active)?.name||'Sin modelo cargado';$('repoArea').classList.toggle('hidden',!data.connected);$('connection').textContent=data.connected?'Cuenta conectada · token cifrado en Android Keystore':'El token se cifra con Android Keystore. Nunca se envía al modelo.';if(data.connected&&!was)command('repos');if(!data.connected){$('editorArea').classList.add('hidden');$('repoSelect').replaceChildren();$('directory').replaceChildren();$('editor').value='';fileSha='';opened=null;}renderModels();break;}
 case 'resources':state={...state,...data};renderResources(state);renderModels();break;
 case 'notice':toast(data);break;
 case 'error':toast(data,true);$('save').disabled=false;break;
 case 'loaded':if(conversationModel&&conversationModel!==data)messages=[];conversationModel=data;persist();setBusy(false);renderChat();page('chat');toast('Modelo listo. Ya puedes conversar sin internet.');break;
 case 'answer':answer=data;renderChat();break;
 case 'done':if(answer){messages.push({role:'assistant',content:answer});persist();}else if(data===false&&messages.at(-1)?.role==='user'){const failed=messages.pop();$('prompt').value=failed.content;persist();}answer='';setBusy(false);attachment=false;$('attachment').classList.add('hidden');renderChat();break;
 case 'idle':setBusy(false);break;
 case 'image':attachment=data;$('attachment').classList.toggle('hidden',!data);break;
 case 'download':{const p=$('progress-'+data.id);if(!p)break;p.className='';p.replaceChildren();const progress=el('progress');progress.max=data.total;progress.value=data.bytes;p.append(el('small','',Math.min(100,100*data.bytes/data.total).toFixed(0)+'% · '+data.file),progress);const cancel=el('button','quiet','Cancelar descarga');cancel.onclick=()=>command('cancel',{id:data.id});p.append(cancel);break;}
 case 'repos':{const select=$('repoSelect'),old=select.value;select.replaceChildren(el('option','','Selecciona un repositorio'));select.firstChild.value='';for(const r of data){const opt=el('option','',r.full_name);opt.value=r.full_name;opt.dataset.branch=r.default_branch;select.append(opt);}select.value=old;break;}
 case 'file':opened={repo:data.repo,branch:data.branch,path:data.path};$('repoSelect').value=data.repo;$('branch').value=data.branch;$('filepath').value=data.path;data=data.result;if(Array.isArray(data)){const root=$('directory');root.replaceChildren();for(const f of data){const b=el('button','', (f.type==='dir'?'▦ ':'↳ ')+f.name);b.onclick=()=>{$('filepath').value=f.path;$('read').click();};root.append(b);}}else{fileSha=data.sha;$('editor').value=data.text;$('editorArea').classList.remove('hidden');$('directory').replaceChildren();}break;
 case 'saved':if(opened&&opened.repo===data.repo&&opened.path===data.path&&opened.branch===data.branch)fileSha=data.sha;$('save').disabled=false;toast('Commit guardado en GitHub.');break;
}};
renderChat();

$('askFile').onclick=()=>{if(!state.active)return toast('Carga primero un modelo de código.',true);if(!opened)return;const text=$('editor').value;if(text.length>10000)return toast('El archivo es largo. Copia solo el fragmento que necesitas al chat.',true);$('prompt').value='Revisa este archivo y explica las mejoras que propones.\n'+opened.repo+'/'+opened.path+'\n\n'+text;page('chat');toast('Archivo preparado en el chat. Añade tu petición y pulsa Enviar.');};

function renderResources(data){
 $('deviceTitle').textContent=data.device||'Tu dispositivo';
 $('deviceDetail').textContent='Presupuesto IA: '+data.budget.toFixed(1)+' GB · '+data.storage.toFixed(1)+' GB de espacio';
 $('ramTotal').textContent=data.ram.toFixed(1)+' GB';
 $('ramFree').textContent=data.available.toFixed(1)+' GB';
 $('ramBudget').textContent=data.budget.toFixed(1)+' GB';
 $('ramReserve').textContent=data.reserve.toFixed(1)+' GB';
 $('resourceSource').textContent=(data.source||'Medición del sistema')+' · '+(data.lowMemory?'Memoria baja':data.pressure?'Presión de memoria':data.pressureKnown===false?'Presión de memoria no accesible':'Sin presión detectada')+(data.pssMiB!==undefined?' · App PSS '+data.pssMiB.toFixed(0)+' MiB':'')+'. El presupuesto IA es una estimación prudente, no toda la RAM física.';
}
$('refreshResources').onclick=()=>{command('state');toast('Actualizando recursos del teléfono…');};
