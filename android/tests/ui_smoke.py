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
    assert page.locator('#messages img').count() == 0
    page.locator('#displayName').fill('Johan')
    page.get_by_role('button', name='Violeta', exact=True).click()
    page.select_option('#themeMode', 'light')
    assert page.locator('html').get_attribute('data-mode') == 'light'
    assert page.evaluate('calls.filter(c=>c[0]==="appearance").at(-1)[1].light')
    page.locator('#customAccent').evaluate("e=>{e.value='#0a2244';e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert page.evaluate('prefs.accent') == '#0a2244'
    assert page.evaluate("contrast(rgb(prefs.accent),[0,0,0]) < contrast(rgb(prefs.accent),[255,255,255])")
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
    assert page.locator('#models article').count()==sum(m['parameters']>=5 for m in models)>10
    page.locator('#modelSearch').fill('Llama')
    assert page.locator('#models article').count()>=2
    page.locator('#modelSearch').fill('')
    page.locator('[data-filter="vision"]').click()
    assert page.locator('#models article').count()==sum(m['vision'] for m in models)
    page.locator('[data-filter="powerful"]').click()
    # Changing context causes a real reload; an estimate never adds a benchmark gate.
    page.locator('[data-model="qwen7"] .actions button').click()
    assert page.evaluate('calls.at(-1)')==['load',{'id':'qwen7','context':2048}]
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
