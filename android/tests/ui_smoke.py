import json,threading,http.server,functools
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1] / 'app/src/main/assets'
server=http.server.ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
models=json.loads((root/'models.json').read_text())
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':390,'height':844},device_scale_factor=2)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script('window.calls=[];window.Native={command:(a,d)=>window.calls.push([a,JSON.parse(d)])};')
 page.goto('http://127.0.0.1:8765')
 state=dict(models=models,installed=['qwen05','smol'],ram=7.2,available=2.5,budget=2.25,reserve=.25,storage=103.3,connected=False,active='qwen05',device='Teléfono de prueba',lowMemory=False,pressure=False,source='ActivityManager + /proc/meminfo')
 page.evaluate('(s)=>receive("state",s)',state)
 assert page.locator('#models article').count()==sum(m['parameters']>=5 for m in models)>10
 assert page.locator('#ramTotal').inner_text()=='7.2 GiB'
 assert page.locator('#ramFree').inner_text()=='2.5 GiB'
 assert '7.2' not in page.locator('#deviceTitle').inner_text()
 five=dict(ram=7.2,available=5,budget=4.75,storage=100,installed=[])
 # 7.2 GiB physical RAM does not fail an arbitrary nominal 8 GB minimum.
 q4=page.evaluate('(d)=>assessModel(state.models.find(m=>m.id==="qwen7"),d)',five)
 assert q4['level']=='caution' and q4['label']=='Posible con margen ajustado'
 assert all('8 GB' not in reason and 'mínimos' not in reason for reason in q4['reasons'])
 for model in ('qwen7-q3','qwen3-8-q3'):
  assert page.evaluate('(x)=>assessModel(state.models.find(m=>m.id===x.id),x.device).recommended',dict(id=model,device=five))
 page.select_option('#contextTokens','512')
 short=page.evaluate('memoryEstimate(state.models.find(m=>m.id==="qwen7")).upper')
 page.select_option('#contextTokens','4096')
 assert page.evaluate('memoryEstimate(state.models.find(m=>m.id==="qwen7")).upper')>short
 page.select_option('#contextTokens','1024')
 # A low-memory estimate does not gate normal model loading with a benchmark or popup.
 state['installed'].append('qwen7')
 page.evaluate('(s)=>receive("state",s)',state)
 page.locator('[data-model="qwen7"] .actions button').click()
 assert not page.locator('#confirm').is_visible()
 call=page.evaluate('calls.at(-1)')
 assert call==['load',{'id':'qwen7','context':1024}]
 page.evaluate('receive("idle",true)')
 page.locator('#modelSearch').fill('Llama')
 assert page.locator('#models article').count()>=2
 page.locator('#modelSearch').fill('')
 page.locator('[data-filter="all"]').click()
 assert page.locator('#models article').count()==len(models)
 assert not page.evaluate('assessModel(state.models.find(m=>m.id==="qwen05"),{ram:8,available:5,budget:4.75,storage:0,installed:[]}).recommended')
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.get_by_role('button',name='Visión',exact=True).click();assert page.locator('#models article').count()==sum(m['vision'] for m in models)
 page.locator('nav [data-page="chat"]').click();page.locator('#prompt').fill('Hola <img src=x onerror=alert(1)> 👋');page.locator('#send').click()
 assert page.evaluate('calls.at(-1)[0]')=='chat'
 assert page.evaluate('calls.at(-1)[1].maxTokens')==512
 assert page.locator('#messages img').count()==0
 page.evaluate('receive("answer","¡Hola! Puedo ayudarte con código.");receive("done",true)')
 assert page.locator('.bubble.assistant').count()==1
 page.reload();page.evaluate('(s)=>receive("state",s)',state);assert page.locator('.bubble.assistant').count()==1
 page.locator('nav [data-page="chat"]').click()
 state['connected']=True;page.evaluate('(s)=>receive("state",s)',state)
 page.evaluate('receive("repos",[{full_name:"owner/repo",default_branch:"dev"}])');page.locator('nav [data-page="github"]').click();page.select_option('#repoSelect','owner/repo');assert page.input_value('#branch')=='dev'
 page.locator('#filepath').fill('README.md');page.locator('#read').click()
 page.evaluate('receive("file",{repo:"owner/repo",branch:"dev",path:"README.md",result:{sha:"abc",text:"old"}})');page.locator('#editor').fill('new');page.locator('#commit').fill('Update README');page.locator('#save').click()
 assert page.evaluate('calls.at(-1)[0]')=='read'
 page.locator('#confirmYes').click();call=page.evaluate('calls.at(-1)');assert call[0]=='write' and call[1]['sha']=='abc' and call[1]['branch']=='dev'
 page.evaluate('receive("error","Conflicto SHA")');assert not page.locator('#save').is_disabled()
 # A model reload preserves this model's conversation.
 page.evaluate('receive("loaded","qwen05")')
 assert page.locator('.bubble.assistant').count()==1
 # Copying a response to a GitHub file requires an explicit review step.
 page.locator('.bubble.assistant button').click()
 assert page.input_value('#editor')=='new'
 page.locator('#confirmYes').click()
 assert page.input_value('#editor')=='¡Hola! Puedo ayudarte con código.'
 assert not errors, errors
 print('PASS: responsive gallery, filters, chat, persistence, resource budget, 5B+ catalog, warnings, output escaping, GitHub review and conflict retry')
 b.close()
server.shutdown()
