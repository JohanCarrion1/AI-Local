"""Exercise the real offline UI with a mock native boundary; no external writes."""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1] / 'app/src/main/assets'
server = http.server.ThreadingHTTPServer(('127.0.0.1', 8765), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
models = json.loads((root / 'models.json').read_text())
state = dict(models=models, installed=['qwen05', 'qwen7', 'smol'], ram=7.2, available=3, budget=2.7, reserve=.3, storage=99, connected=False, active='qwen7', activeContext=1024, device='Samsung SM-A366E', lowMemory=False, pressure=False, source='ActivityManager + /proc/meminfo', usage=[])

def navigate(page, destination):
    page.locator('#menuToggle').click()
    page.locator(f'#drawer [data-page="{destination}"]').click()

def settings(page):
    page.locator('#menuToggle').click()
    page.locator('#profileButton').click()

def deliver(page, text):
    page.evaluate('(text)=>{receive("answer",text);receive("done",true);}', text)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':390,'height':844}, device_scale_factor=1)
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.add_init_script('window.calls=[];window.Native={command:(a,d)=>calls.push([a,JSON.parse(d)])};')
    page.goto('http://127.0.0.1:8765')
    assert page.locator('#chat').is_visible() and not page.locator('#library').is_visible()
    assert not page.locator('#chatHint').is_visible()
    assert 'puede cometer errores' not in page.locator('body').inner_text()
    assert page.evaluate('prefs.accent') == '#e5a078'
    assert page.locator('#prompt').bounding_box()['y'] > 650
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.evaluate('(s)=>receive("state",s)', state)
    assert not page.evaluate('calls.some(c=>c[0]==="load")'), 'Loading requires intent unless auto-load was enabled'

    # Drawer navigation and dismissal preserve focus and main-page isolation.
    page.locator('#menuToggle').click()
    assert page.locator('#menuToggle').get_attribute('aria-expanded') == 'true'
    assert page.evaluate('document.getElementById("app").inert')
    assert page.locator('#drawer [data-page]').count() == 3
    page.keyboard.press('Escape')
    assert not page.locator('#drawer').is_visible()
    assert page.locator('#menuToggle').get_attribute('aria-expanded') == 'false'

    settings(page)
    page.locator('#displayName').fill('<img src=x onerror=alert(1)>')
    assert page.locator('#messages h1 img').count() == 0
    assert page.locator('.brand-mark img').get_attribute('src')=='auren-mark.png'
    page.locator('#displayName').fill('Johan')
    page.get_by_role('button', name='Violeta', exact=True).click()
    page.select_option('#themeMode', 'light')
    assert page.locator('html').get_attribute('data-mode') == 'light'
    assert page.evaluate('calls.filter(c=>c[0]==="appearance").at(-1)[1].light')
    page.locator('#customAccent').evaluate("e=>{e.value='#0a2244';e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert page.evaluate('prefs.accent') == '#0a2244'
    assert page.evaluate("contrast(rgb(prefs.accent),[0,0,0]) < contrast(rgb(prefs.accent),[255,255,255])")
    # The full palette works by touch/mouse and keyboard, without a native color dialog.
    page.locator('#colorHue').fill('210')
    page.locator('#colorSaturation').fill('100')
    page.locator('#colorValue').fill('100')
    assert page.evaluate('prefs.accent') == '#0080ff', page.evaluate('JSON.stringify({palette,accent:prefs.accent})')
    plane = page.locator('#colorPlane').bounding_box()
    page.mouse.click(plane['x']+plane['width']/2, plane['y']+plane['height']/2)
    assert page.evaluate('Math.abs(palette.s-.5)<.02 && Math.abs(palette.v-.5)<.02')
    page.locator('#customAccent').fill('#123abc')
    assert page.evaluate('prefs.accent') == '#123abc'
    page.locator('#customAccent').fill('invalid')
    assert page.evaluate('prefs.accent') == '#123abc'
    page.get_by_role('button', name='Naranja', exact=True).click()
    page.select_option('#themeMode','dark')
    page.select_option('#defaultModel','qwen7')
    page.select_option('#contextTokens','2048')
    page.select_option('#responseTokens','1024')
    page.locator('#instructions').fill('Responde en español, con ejemplos claros.')
    page.locator('#closeSettings').click()
    page.reload()
    page.evaluate('(s)=>receive("state",s)', state)
    assert page.evaluate('prefs.name') == 'Johan'
    assert page.evaluate('prefs.accent') == '#e5a078'
    assert page.locator('#contextTokens').input_value() == '2048'
    assert page.locator('#responseTokens').input_value() == '1024'
    assert page.locator('#chat').is_visible()
    assert not page.evaluate('calls.some(c=>c[0]==="load")')
    greeting = page.locator('.welcome h1')
    assert float(greeting.evaluate('e=>getComputedStyle(e).fontSize').replace('px','')) <= 26
    assert greeting.evaluate('e=>getComputedStyle(e).textAlign') == 'center'
    box = greeting.bounding_box()
    assert abs(box['x']+box['width']/2-195) < 2
    page.screenshot(path='/tmp/auren-chat-preview.png')

    # Native chat payload, user text escaping, history and separate conversations.
    first = 'Mi primera conversación <img src=x onerror=alert(1)>'
    page.locator('#prompt').fill(first)
    page.locator('#send').click()
    call=page.evaluate('calls.at(-1)')
    assert call[0]=='chat' and call[1]['maxTokens']==1024
    assert call[1]['messages'][0]['content']=='Responde en español, con ejemplos claros.'
    assert page.locator('#messages img').count()==0
    assert page.locator('#newChat').is_disabled()
    deliver(page, 'Primera respuesta guardada.')
    first_id=page.evaluate('current.id')
    page.locator('#newChat').click()
    assert page.locator('.bubble').count()==0
    page.locator('#prompt').fill('Segunda conversación')
    page.locator('#send').click()
    deliver(page, 'Segunda respuesta.')
    assert page.evaluate('store.sessions.length')==2
    page.locator('#menuToggle').click()
    page.locator('#historySearch').fill('primera')
    assert page.locator('.history-item').count()==1
    page.locator('.history-item').click()
    assert page.locator('.bubble.assistant').inner_text().endswith('Primera respuesta guardada.\nCopiar')
    assert page.evaluate('current.id')==first_id
    page.reload();page.evaluate('(s)=>receive("state",s)', state)
    assert page.evaluate('store.sessions.length')==2
    assert page.evaluate('current.id')==first_id

    # Existing model catalog and realistic resource estimates remain functional.
    navigate(page,'library')
    assert page.locator('#models article').count()==sum(3<=m['parameters']<=6 for m in models)>=10
    assert page.locator('[data-model="qwen3"]').is_visible(), 'The existing Coder 3B must no longer be hidden'
    assert page.locator('[data-model="qwenvl3"]').is_visible()
    assert page.locator('[data-model="qwen3vl4"]').is_visible()
    assert not page.locator('[data-model="qwen7"]').count()
    page.locator('[data-filter="code"]').click()
    assert page.locator('[data-model="qwen3-instruct4"]').is_visible()
    assert page.locator('[data-model="qwen3-4"]').is_visible(), 'Code-capable reasoning models are included'
    page.locator('[data-filter="all"]').click()
    page.locator('#modelSearch').fill('Llama')
    assert page.locator('#models article').count()>=2
    page.locator('#modelSearch').fill('')
    page.locator('[data-filter="vision"]').click()
    assert page.locator('#models article').count()==sum(m['vision'] for m in models)
    page.locator('[data-filter="powerful"]').click()
    # Changing context causes a real reload; an estimate never adds a benchmark gate.
    page.locator('[data-model="qwen7"] .actions button').click()
    call=page.evaluate('calls.at(-1)')
    assert call[0]=='load' and call[1]['id']=='qwen7' and call[1]['context']==2048
    assert call[1]['requestId'] and call[1]['sessionId']==page.evaluate('current.id')
    assert not page.locator('#confirm').is_visible()
    page.evaluate('receive("error","No se pudo cargar");receive("done",false);receive("idle",true)')
    assert page.evaluate('messages.length')==2, 'A load failure must not erase a saved conversation'
    settings(page)
    page.locator('.device-settings>summary').click()
    assert page.locator('#ramTotal').inner_text()=='7.2 GiB'
    assert page.locator('#ramFree').inner_text()=='3.0 GiB'
    page.locator('#closeSettings').click()
    five=dict(ram=7.2,available=5,budget=4.75,storage=100,installed=[])
    assert page.evaluate('(d)=>assessModel(state.models.find(m=>m.id==="qwen7"),d).level',five)!='large'
    assert page.evaluate('(d)=>assessModel(state.models.find(m=>m.id==="qwen7-q3"),d).recommended',five)

    # Explicit preferred-model auto-loading is persistent and happens only once per launch.
    settings(page)
    page.locator('#autoLoad').check()
    page.locator('#closeSettings').click()
    page.reload()
    unloaded={**state,'active':'','activeContext':0}
    page.evaluate('(s)=>receive("state",s)', unloaded)
    assert len(page.evaluate('calls.filter(c=>c[0]==="load")'))==1
    page.evaluate('(s)=>receive("state",s)', unloaded)
    assert len(page.evaluate('calls.filter(c=>c[0]==="load")'))==1
    loaded={**state,'activeContext':2048}
    page.evaluate('(s)=>receive("state",s)', loaded);page.evaluate('receive("loaded","qwen7")')
    assert page.evaluate('messages.length')==2

    # GitHub editing still requires review and sends the exact branch and original SHA.
    connected={**loaded,'connected':True}
    page.evaluate('(s)=>receive("state",s)',connected)
    page.evaluate('receive("repos",[{full_name:"owner/repo",default_branch:"dev"}])')
    navigate(page,'github')
    page.select_option('#repoSelect','owner/repo')
    assert page.locator('#branch').input_value()=='dev'
    page.locator('#filepath').fill('README.md');page.locator('#read').click()
    page.evaluate('receive("file",{repo:"owner/repo",branch:"dev",path:"README.md",result:{sha:"abc",text:"old"}})')
    page.locator('#editor').fill('new');page.locator('#commit').fill('Update README');page.locator('#save').click()
    assert page.evaluate('calls.at(-1)[0]')=='read'
    page.locator('#confirmYes').click();call=page.evaluate('calls.at(-1)')
    assert call[0]=='write' and call[1]['sha']=='abc' and call[1]['branch']=='dev'
    page.evaluate('receive("error","Conflicto SHA")');assert not page.locator('#save').is_disabled()
    navigate(page,'chat')
    page.locator('#prompt').fill('Escribe el código')
    page.locator('#send').click()
    deliver(page, '```js\nconst x = 1;\n```')
    page.locator('.to-github').last.click();page.locator('#confirmYes').click()
    assert page.locator('#editor').input_value()=='const x = 1;'

    # Back returns to chat, then closes drawer/settings without leaving the app.
    assert page.evaluate('handleBack()')
    assert page.locator('#chat').is_visible()
    page.locator('#menuToggle').click();assert page.evaluate('handleBack()')
    settings(page);assert page.evaluate('handleBack()')
    assert not page.evaluate('handleBack()')

    # Deletion is explicit and does not resurrect a legacy chat on reload.
    settings(page);page.locator('#clearHistory').click();page.locator('#confirmNo').click()
    assert page.evaluate('store.sessions.length')==2
    page.locator('#clearHistory').click();page.locator('#confirmYes').click()
    assert page.evaluate('store.sessions.length')==1 and page.locator('.bubble').count()==0
    page.reload();page.evaluate('(s)=>receive("state",s)',loaded)
    assert page.locator('.bubble').count()==0
    assert page.evaluate('store.sessions.length')==1
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors

    # Worker ordering, long-prefill feedback and recoverable empty responses.
    recovery=browser.new_page(viewport={'width':390,'height':844})
    recovery.add_init_script('window.calls=[];window.Native={command:(a,d)=>calls.push([a,JSON.parse(d)])};')
    recovery.goto('http://127.0.0.1:8765')
    recovery.evaluate('(s)=>receive("state",s)',state)
    recovery.locator('#prompt').fill('Hola que tal')
    recovery.locator('#send').click()
    recovery.evaluate('receive("idle",true)')
    assert recovery.locator('#stop').is_visible(), 'A stale idle event must not erase an active reply'
    recovery.evaluate('receive("progress",{action:"chat",phase:"prompt",current:128,total:230})')
    assert '128/230 tokens' in recovery.locator('.streaming').inner_text()
    recovery.evaluate('receive("done",true)')
    assert recovery.locator('.operation-error').is_visible(), 'Empty inference cannot silently succeed'
    assert recovery.evaluate('messages.length')==1
    recovery.locator('.retry-operation').click()
    assert recovery.evaluate('calls.at(-1)[1].messages.filter(m=>m.role==="user").length')==1
    recovery.evaluate('receive("operationError",{action:"chat",message:"Fallo del contexto local"});receive("done",false)')
    assert 'Fallo del contexto local' in recovery.locator('.operation-error').inner_text()
    recovery.reload();recovery.evaluate('(s)=>receive("state",s)',state)
    assert recovery.locator('.retry-operation').is_visible()
    recovery.locator('.retry-operation').click()
    recovery.reload();recovery.evaluate('(s)=>receive("state",s)',unloaded)
    recovery.evaluate('receive("inference",{active:"",activeContext:0,busy:false,job:{}})')
    assert 'se interrumpió' in recovery.locator('.operation-error').inner_text()
    recovery.locator('.retry-operation').click()
    assert recovery.evaluate('calls.at(-1)[0]')=='load'
    recovery.evaluate('receive("progress",{action:"load",phase:"weights",current:64,total:100})')
    assert '64%' in recovery.locator('.model-progress').inner_text()
    recovery.evaluate('(s)=>receive("state",s)',state)
    recovery.evaluate('receive("loaded","qwen7")')
    assert recovery.evaluate('calls.at(-1)[0]')=='chat'
    deliver(recovery,'¡Hola! ¿En qué puedo ayudarte?')
    assert recovery.locator('.bubble.assistant .message-text').inner_text().startswith('¡Hola!')
    assert not recovery.locator('.operation-error').count()
    assert not recovery.locator('#chatHint').is_visible()
    navigate(recovery,'library')
    recovery.locator('[data-filter="all"]').click()
    recovery.locator('[data-model="qwen7"] button').filter(has_text='Eliminar del teléfono').click()
    recovery.locator('#confirmYes').click()
    assert recovery.evaluate('running && operationKind === "delete"')
    recovery.evaluate('receive("idle",true)')
    assert not recovery.evaluate('running')
    navigate(recovery,'chat')
    settings(recovery);recovery.locator('#showStats').check();recovery.locator('#closeSettings').click()
    recovery.evaluate('receive("metrics",{context:1024,tps:3.5,stopped:false})')
    assert recovery.locator('#chatHint').inner_text()=='1024 contexto · 3.5 tokens/s'
    settings(recovery);recovery.locator('#showStats').uncheck();recovery.locator('#closeSettings').click()
    assert not recovery.locator('#chatHint').is_visible()

    # Activity/WebView reload attaches to the real native job instead of declaring interruption.
    bg=browser.new_page(viewport={'width':390,'height':844})
    bg.add_init_script('window.calls=[];window.Native={command:(a,d)=>calls.push([a,JSON.parse(d)])};')
    bg.goto('http://127.0.0.1:8765');bg.evaluate('(s)=>receive("state",s)',state)
    bg.locator('#prompt').fill('Sigue trabajando cuando cambie de app');bg.locator('#send').click()
    req=bg.evaluate('calls.at(-1)[1]')
    assert req['sessionId']==bg.evaluate('current.id') and req['requestId']
    job=dict(id=req['requestId'],sessionId=req['sessionId'],action='chat',status='running',modelId='qwen7',answer='Respuesta en curso',startedAt=1780000000000,progress=dict(phase='generate',current=0,total=512))
    live=dict(active='qwen7',activeContext=1024,busy=True,foreground=True,instanceId='service-a',revision=1,job=job)
    bg.evaluate('(s)=>receive("inference",s)',live)
    bg.reload();bg.evaluate('(s)=>receive("state",s)',{**state,'inference':live})
    assert not bg.locator('.operation-error').count()
    assert bg.locator('.streaming').inner_text()=='Respuesta en curso'
    complete={**live,'busy':False,'revision':2,'job':{**job,'status':'success','answer':'Respuesta completa en segundo plano.'}}
    bg.evaluate('(s)=>receive("inference",s)',complete)
    assert bg.locator('.bubble.assistant').count()==1
    bg.reload();bg.evaluate('(s)=>receive("state",s)',{**state,'inference':complete})
    assert bg.locator('.bubble.assistant').count()==1, 'A completed native response is imported exactly once'
    bg.evaluate('(s)=>receive("inference",s)',live)
    assert not bg.evaluate('running'), 'A delayed running snapshot cannot overwrite completion'
    assert bg.locator('.bubble.assistant').count()==1
    bg.locator('#prompt').fill('Segundo mensaje');bg.locator('#send').click()
    req2=bg.evaluate('calls.at(-1)[1]')
    interrupted={**live,'active':'','busy':False,'revision':3,'job':{**job,'id':req2['requestId'],'status':'interrupted','answer':'Una parte recuperada.','error':'Android interrumpió la ejecución anterior.'}}
    bg.evaluate('(s)=>receive("inference",s)',interrupted)
    assert 'Una parte recuperada.' in bg.locator('#messages').inner_text()
    assert bg.locator('.retry-operation').is_visible()
    assert bg.evaluate('messages.at(-1).incomplete')
    bg.locator('.retry-operation').click()
    assert bg.evaluate('calls.at(-1)[0]')=='load'
    assert bg.evaluate('messages.at(-1).role')=='user', 'Retry replaces the partial attempt, without duplicating the user'

    # Limited answers are distinguished from Android interruption and can be continued.
    limited=browser.new_page(viewport={'width':390,'height':844})
    limited.add_init_script('window.calls=[];window.Native={command:(a,d)=>calls.push([a,JSON.parse(d)])};')
    limited.goto('http://127.0.0.1:8765');limited.evaluate('(s)=>receive("state",s)',state)
    limited.locator('#prompt').fill('Escribe un programa completo');limited.locator('#send').click()
    limited.evaluate('continuationRounds=3')  # automatic continuation already exhausted
    limited.evaluate('receive("metrics",{finishReason:"length",context:1024,tps:1,stopped:false})')
    deliver(limited, '**Código**\n```python\nprint("<script>alert(1)</script>")\n```\nFin.')
    assert limited.locator('.message-code code').inner_text() == 'print("<script>alert(1)</script>")'
    assert limited.locator('.message-text script').count()==0
    assert limited.locator('.message-text strong').inner_text()=='Código'
    assert limited.locator('.continue-answer').is_visible()
    limited.reload();limited.evaluate('(s)=>receive("state",s)',state)
    assert limited.locator('.continue-answer').is_visible(), 'Finish reason survives reload'
    limited.locator('.continue-answer').click()
    assert limited.evaluate('running && calls.at(-1)[0] === "chat"')
    assert 'Continúa' in limited.evaluate('calls.at(-1)[1].messages.at(-1).content')
    calls_before=limited.evaluate('calls.length')
    limited.evaluate('window.dispatchEvent(new Event("focus"))')
    assert limited.evaluate('calls.at(-1)[0]')=='inferenceState'
    assert limited.evaluate('calls.length') > calls_before

    # Cut answers continue by themselves and are merged into one message with whole code blocks.
    auto=browser.new_page(viewport={'width':390,'height':844})
    auto.add_init_script('window.calls=[];window.Native={command:(a,d)=>calls.push([a,JSON.parse(d)])};')
    auto.goto('http://127.0.0.1:8765');auto.evaluate('(s)=>receive("state",s)',state)
    auto.locator('#prompt').fill('Haz un programa');auto.locator('#send').click()
    auto.evaluate('receive("metrics",{finishReason:"length",context:2048,tps:1,stopped:false})')
    deliver(auto, 'Aquí va:\n```python\ndef a():\n    if x_precio')
    auto.wait_for_function('calls.filter(c=>c[0]==="chat").length===2')
    sent=auto.evaluate('calls.at(-1)[1].messages.at(-1).content')
    assert 'x_precio' in sent and 'sin repetir' in sent
    assert auto.locator('.bubble.user').count()==1, 'The synthetic continuation prompt is hidden'
    auto.evaluate('receive("metrics",{finishReason:"stop",context:2048,tps:1,stopped:false})')
    deliver(auto, 'if x_precio > 0:\n        return 1\n```\nListo.')
    assert auto.locator('.bubble.assistant').count()==1, 'Continuation joins the previous answer'
    assert auto.locator('.message-code').count()==1, 'One uninterrupted code block'
    code=auto.locator('.message-code code').inner_text()
    assert code=='def a():\n    if x_precio > 0:\n        return 1', code
    assert not auto.locator('.continue-answer').count()
    assert auto.evaluate('calls.filter(c=>c[0]==="chat").length')==2

    # GitHub onboarding is an actual app action, available before loading a model.
    git=browser.new_page(viewport={'width':390,'height':844})
    git.add_init_script('window.calls=[];window.Native={command:(a,d)=>calls.push([a,JSON.parse(d)])};')
    git.goto('http://127.0.0.1:8765');git.evaluate('(s)=>receive("state",s)',unloaded)
    git.locator('#prompt').fill('Conéctate a GitHub; necesito que edites un código.')
    git.locator('#send').click()
    assert git.locator('.github-setup').inner_text()=='Conectar GitHub'
    assert not git.evaluate('calls.some(c=>c[0]==="chat" || c[0]==="load")')
    git.locator('.github-setup').click()
    assert git.locator('#github').is_visible() and git.locator('#token').evaluate('e=>document.activeElement===e')
    git.locator('#createToken').click();assert git.evaluate('calls.at(-1)[0]')=='tokenHelp'
    # A PAT accidentally pasted into chat is moved to the private field, never stored or sent to inference.
    secret='github_pat_'+'x'*50
    navigate(git,'chat');git.locator('#prompt').fill('Este es mi token: '+secret);git.locator('#send').click()
    assert git.locator('#token').input_value()==secret
    assert secret not in git.evaluate('JSON.stringify(store)')
    assert not git.evaluate('calls.some(c=>c[0]==="chat")')
    git.locator('#connect').click()
    assert git.evaluate('calls.at(-1)[0]')=='connect' and git.locator('#token').input_value()==''
    git.evaluate('receive("githubError",{action:"connect",message:"Token no aceptado"})')
    assert not git.locator('#connect').is_disabled() and git.locator('#connection').inner_text()=='Token no aceptado'
    # Real account/file state supplies a selected reference to the model, without reusing a wrong file.
    git.evaluate('(s)=>receive("state",s)',{**state,'connected':True,'githubLogin':'johan'})
    git.evaluate('receive("repos",[{full_name:"owner/repo",default_branch:"dev"}]);receive("file",{repo:"owner/repo",branch:"dev",path:"main.js",result:{sha:"v1",text:"const x = 1;"}})')
    git.locator('#askFile').click()
    assert git.locator('#workspaceContext').is_visible()
    git.locator('#prompt').fill('Cambia x a 2 y entrega el archivo completo');git.locator('#send').click()
    payload=git.evaluate('calls.at(-1)[1]')
    assert payload['workspace']==dict(repo='owner/repo',branch='dev',path='main.js',sha='v1',text='const x = 1;')
    assert not any('Conéctate a GitHub' in m['content'] for m in payload['messages'])
    deliver(git,'Aquí está el archivo:\n```js\nconst x = 2;\n```')
    git.locator('.to-github').last.click();git.locator('#confirmYes').click()
    assert git.locator('#editor').input_value()=='const x = 2;'
    git.evaluate('receive("file",{repo:"owner/repo",branch:"dev",path:"other.js",result:{sha:"z1",text:"keep this"}})')
    navigate(git,'chat');git.locator('.to-github').last.click()
    assert not git.locator('#confirm').is_visible() and git.locator('#editor').input_value()=='keep this'
    git.evaluate('receive("file",{repo:"owner/repo",branch:"dev",path:"main.js",result:{sha:"v2",text:"new revision"}})')
    navigate(git,'chat');git.locator('.to-github').last.click()
    assert not git.locator('#confirm').is_visible() and git.locator('#editor').input_value()=='new revision'

    # Photos are prepared before sending, previewed, session-owned and identified at JNI boundary.
    vision=browser.new_page(viewport={'width':390,'height':844})
    vision.add_init_script('window.calls=[];window.Native={command:(a,d)=>calls.push([a,JSON.parse(d)])};')
    vision.goto('http://127.0.0.1:8765')
    vision_state={**state,'active':'smol','activeContext':2048}
    vision.evaluate('(s)=>receive("state",s)',vision_state)
    vision.locator('#attach').click()
    session=vision.evaluate('current.id')
    assert vision.evaluate('calls.at(-1)')==['image',dict(sessionId=session)]
    # Cancellation leaves the composer usable; loading and decode errors cannot send a text-only turn.
    vision.evaluate('receive("image",null)')
    assert not vision.locator('#send').is_disabled()
    vision.evaluate('(s)=>receive("image",{sessionId:s,status:"loading"})',session)
    assert vision.locator('#send').is_disabled() and 'Preparando' in vision.locator('#attachmentLabel').inner_text()
    vision.evaluate('(s)=>receive("image",{sessionId:s,status:"error",error:"No se pudo leer la foto"})',session)
    assert vision.locator('#send').is_disabled() and 'No se pudo leer' in vision.locator('#attachmentLabel').inner_text()
    vision.locator('#removeImage').click()
    assert not vision.locator('#send').is_disabled()
    preview=vision.evaluate("(()=>{let c=document.createElement('canvas');c.width=c.height=8;let x=c.getContext('2d');x.fillStyle='red';x.fillRect(0,0,8,8);return c.toDataURL('image/jpeg');})()")
    photo=dict(id='photo-red',sessionId=session,status='ready',name='foto.jpg',width=224,height=224,thumbnail=preview)
    root=dict(active='smol',activeContext=2048,busy=False,instanceId='photo-service',revision=1,selectedImage=photo,job={})
    vision.evaluate('(s)=>receive("inference",s)',root)
    vision.wait_for_function('document.getElementById("attachmentPreview").naturalWidth>0')
    # Recreating WebView recovers the prepared photo from the independent service.
    vision.reload();vision.evaluate('(s)=>receive("state",s)',{**vision_state,'inference':root})
    assert vision.evaluate('attachment.id')=='photo-red'
    vision.locator('#prompt').fill('¿Qué ves?');vision.locator('#send').click()
    payload=vision.evaluate('calls.at(-1)[1]')
    assert payload['imageId']=='photo-red' and payload['expectsImage']
    assert payload['messages'][-1]['imageId']=='photo-red'
    assert vision.locator('.message-photo img').count()==1
    deliver(vision,'Un cuadro rojo.')
    vision.locator('#prompt').fill('¿De qué color era?');vision.locator('#send').click()
    payload=vision.evaluate('calls.at(-1)[1]')
    assert payload['imageId']=='photo-red' and payload['messages'][-3]['imageId']=='photo-red'
    assert 'imageId' not in payload['messages'][-1], 'A follow-up must preserve the actual image turn'
    deliver(vision,'Rojo.')
    vision.locator('#newChat').click()
    vision.evaluate('(s)=>receive("image",s)',photo)
    assert not vision.evaluate('attachment'), 'A photo from another conversation must not be attached'
    assert not vision.locator('.message-photo img').count()
    assert not errors, errors

    # Upgrade migration from the 2.2 single-chat store preserves the original messages.
    legacy=browser.new_page(viewport={'width':360,'height':760})
    legacy.add_init_script('''if(!localStorage.getItem('seeded')){localStorage.setItem('chat',JSON.stringify([{role:'user',content:'Chat anterior'},{role:'assistant',content:'Respuesta anterior'}]));localStorage.setItem('chatModel','qwen7');localStorage.setItem('seeded','1');}window.Native={command:()=>{}};''')
    legacy.goto('http://127.0.0.1:8765')
    assert legacy.locator('.bubble.user').inner_text()=='Chat anterior'
    assert legacy.evaluate('store.sessions.length')==1
    legacy.reload();assert legacy.evaluate('store.sessions.length')==1
    assert legacy.locator('.bubble.assistant .message-text').inner_text()=='Respuesta anterior'
    browser.close()
server.shutdown()
print('PASS: chat-first UI, drawer, profile/themes, persistent history/migration, model loads, memory estimates and reviewed GitHub editing')
