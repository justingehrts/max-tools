Max tools configurator - source
================================
src/lib.js        Logic: defaults, validation, config.json + SETUP.txt builders, icon drawing, zip writer (no DOM, testable in Node)
src/app.js        Page behavior (tabs, form binding, previews, download)
src/template.html Markup and styles
payload/          Files shipped inside every package: install.ps1, uninstall.ps1, Install.bat, Uninstall.bat
build.py          Inlines everything into one self-contained out/index.html:   python3 build.py
test_lib.js       Node checks for validation and the zip writer:                node test_lib.js
Upload out/index.html to the web space. Edit installer behavior in payload/*.ps1, then rebuild.
Keep payload/*.ps1 ASCII-only (Windows PowerShell 5.1 misreads non-ASCII in BOM-less files).
