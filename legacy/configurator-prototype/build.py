import json, pathlib
root = pathlib.Path(__file__).parent
def safe(s): return s.replace('</', '<\\/')
payload = {}
for name in ['install.ps1','uninstall.ps1','Install.bat','Uninstall.bat']:
    txt = (root/'payload'/name).read_text(encoding='ascii')
    payload[name] = txt
html = (root/'src/template.html').read_text(encoding='utf-8')
html = html.replace('/*LIB*/', safe((root/'src/lib.js').read_text(encoding='utf-8')))
html = html.replace('/*PAYLOAD*/', safe(json.dumps(payload, indent=1)))
html = html.replace('/*APP*/', safe((root/'src/app.js').read_text(encoding='utf-8')))
(root/'out').mkdir(exist_ok=True)
(root/'out/index.html').write_text(html, encoding='utf-8')
print('built out/index.html', len(html), 'bytes')
