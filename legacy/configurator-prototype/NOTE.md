This is the configurator built for the *old* local-installer approach. Reuse `src/lib.js`, `src/app.js` patterns and
`src/template.html` styles for the rework described in ../docs/GUI.md. Build with `python3 build.py`, test with `node test_lib.js`.
`payload/` (Install.bat, install.ps1, uninstall.ps1) is the legacy Windows installer: parses under PowerShell 7, never run on Windows.
