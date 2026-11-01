(function () {
  'use strict';
  var STORE_KEY = 'maxtools.record-dots.v1';
  var SHAPE_LABELS = { circle: 'Circle', square: 'Square', diamond: 'Diamond', triangle: 'Triangle' };

  var state = loadSaved() || LIB.defaults();
  var touched = {};      // fields the person has visited
  var attempted = false; // set after the first download click

  /* ---------- helpers ---------- */
  function $(id) { return document.getElementById(id); }
  function getPath(path) { return path.split('.').reduce(function (o, k) { return o[k]; }, state); }
  function setPath(path, val) {
    var parts = path.split('.'), o = state;
    parts.slice(0, -1).forEach(function (k) { o = o[k]; });
    o[parts[parts.length - 1]] = val;
  }
  function saveLocal() { try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) { /* storage can be unavailable */ } }
  function loadSaved() {
    try { var raw = localStorage.getItem(STORE_KEY); return raw ? LIB.fromConfig(JSON.parse(raw)) : null; } catch (e) { return null; }
  }

  /* ---------- tabs ---------- */
  var TABS = ['station', 'dots'];
  function showTab(name) {
    TABS.forEach(function (t) {
      var on = t === name;
      $('tab-' + t).hidden = !on;
      var b = $('tab-btn-' + t);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
    });
    if (name === 'dots') drawPreviews();
  }
  TABS.forEach(function (t) {
    $('tab-btn-' + t).addEventListener('click', function () { showTab(t); });
  });
  document.querySelector('.rail').addEventListener('keydown', function (ev) {
    if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
    var cur = TABS.findIndex(function (t) { return $('tab-btn-' + t).getAttribute('aria-selected') === 'true'; });
    var next = (cur + (ev.key === 'ArrowDown' ? 1 : -1) + TABS.length) % TABS.length;
    showTab(TABS[next]); $('tab-btn-' + TABS[next]).focus(); ev.preventDefault();
  });

  /* ---------- dot rows ---------- */
  function buildDotRows() {
    var host = $('dotRows');
    host.innerHTML = '';
    LIB.TYPES.forEach(function (t) {
      var row = document.createElement('div');
      row.className = 'dot-row';
      var shapeOpts = LIB.SHAPES.map(function (s) { return '<option value="' + s + '">' + SHAPE_LABELS[s] + '</option>'; }).join('');
      row.innerHTML =
        '<div class="name">' + t.title + '<div class="note">' + t.note + '</div></div>' +
        '<div class="pair"><input type="color" id="c-' + t.key + '" aria-label="' + t.title + ' color">' +
        '<input type="text" class="hex" id="h-' + t.key + '" maxlength="7" spellcheck="false" aria-label="' + t.title + ' color as hex"></div>' +
        '<select id="s-' + t.key + '" aria-label="' + t.title + ' shape">' + shapeOpts + '</select>';
      host.appendChild(row);
      $('c-' + t.key).addEventListener('input', function (e) { setIcon(t.key, 'color', e.target.value); });
      $('h-' + t.key).addEventListener('input', function (e) { var v = hexFix(e.target.value); if (v) setIcon(t.key, 'color', v, true); });
      $('s-' + t.key).addEventListener('change', function (e) { setIcon(t.key, 'shape', e.target.value); });
    });
  }
  function hexFix(v) {
    v = String(v).trim();
    if (/^[0-9a-fA-F]{6}$/.test(v)) v = '#' + v;
    return /^#[0-9a-fA-F]{6}$/.test(v) ? v.toLowerCase() : null;
  }
  function setIcon(key, prop, val, fromHex) {
    state.recordDots.icons[key][prop] = val;
    afterChange(fromHex ? 'keep-hex' : null);
  }

  /* ---------- rendering ---------- */
  function syncInputs(skipHex) {
    document.querySelectorAll('[data-path]').forEach(function (el) {
      var v = getPath(el.getAttribute('data-path'));
      if (document.activeElement !== el) el.value = v;
    });
    var ic = state.recordDots.icons;
    LIB.TYPES.forEach(function (t) {
      $('c-' + t.key).value = ic[t.key].color;
      if (!skipHex || document.activeElement !== $('h-' + t.key)) $('h-' + t.key).value = ic[t.key].color;
      $('s-' + t.key).value = ic[t.key].shape;
    });
    $('ring-on').checked = !!ic.ring.enabled;
    $('ring-color').value = ic.ring.color;
    if (!skipHex || document.activeElement !== $('ring-hex')) $('ring-hex').value = ic.ring.color;
    $('ring-color').disabled = $('ring-hex').disabled = !ic.ring.enabled;
  }

  function renderErrors(errors) {
    document.querySelectorAll('[data-err]').forEach(function (el) {
      var key = el.getAttribute('data-err');
      var show = (attempted || touched[key]) && errors[key];
      el.textContent = show ? errors[key] : '';
    });
    document.querySelectorAll('[data-path]').forEach(function (el) {
      var key = el.getAttribute('data-path');
      el.setAttribute('aria-invalid', ((attempted || touched[key]) && errors[key]) ? 'true' : 'false');
    });
  }

  function renderChecklist(errors) {
    var keys = Object.keys(errors);
    var st = keys.some(function (k) { return k.indexOf('station.') === 0; });
    var rd = keys.some(function (k) { return k.indexOf('recordDots.') === 0; });
    setTick('station', !st, 'Station settings', st ? 'needs a name and email' : null);
    setTick('dots', !rd, 'Record dots', rd ? 'needs attention' : null);
  }
  function setTick(id, ok, label, problem) {
    var t = $('tick-' + id);
    t.textContent = ok ? '\u2713' : '!';
    t.className = 'tick ' + (ok ? 'ok' : 'no');
    $('txt-' + id).textContent = label + (problem ? ' (' + problem + ')' : '');
  }

  /* ---------- icon previews ---------- */
  function mulberry(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  function drawPreviews() {
    var ic = state.recordDots.icons, ring = ic.ring;
    var row = $('scopeRow');
    if (!row.children.length) {
      LIB.TYPES.forEach(function (t) {
        var f = document.createElement('figure');
        f.innerHTML = '<canvas class="big" id="pv-' + t.key + '" width="176" height="176" aria-hidden="true"></canvas><figcaption>' + t.title + '</figcaption>';
        row.appendChild(f);
      });
    }
    LIB.TYPES.forEach(function (t) {
      var c = $('pv-' + t.key);
      LIB.drawIcon(c.getContext('2d'), 176, ic[t.key], ring);
    });

    var map = $('scopeMap'), dpr = window.devicePixelRatio || 1;
    var cssW = map.clientWidth || 560, cssH = 118;
    map.width = Math.round(cssW * dpr); map.height = Math.round(cssH * dpr);
    var ctx = map.getContext('2d'), W = map.width, H = map.height;
    var g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, '#26384a'); g.addColorStop(1, '#1b2a37');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(160,185,205,0.13)'; ctx.lineWidth = Math.max(1, dpr);
    var grid = Math.round(40 * dpr), x, y;
    for (x = 0; x < W; x += grid) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (y = 0; y < H; y += grid) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    var rnd = mulberry(7), sz = Math.round(28 * dpr), pad = Math.round(8 * dpr);
    var tile = document.createElement('canvas'); tile.width = tile.height = sz;
    var count = Math.max(18, Math.round(cssW / 11)), pts = [];
    for (var i = 0; i < count; i++) pts.push({ x: pad + rnd() * (W - 2 * pad - sz), y: pad + rnd() * (H - 2 * pad - sz), t: LIB.TYPES[Math.floor(rnd() * 4)].key });
    pts.sort(function (a, b) { return a.y - b.y; });
    pts.forEach(function (p) {
      LIB.drawIcon(tile.getContext('2d'), sz, ic[p.t], ring);
      ctx.drawImage(tile, Math.round(p.x), Math.round(p.y));
    });
  }

  /* ---------- main refresh ---------- */
  function afterChange(mode) {
    saveLocal();
    syncInputs(mode === 'keep-hex');
    var errors = LIB.validate(state);
    renderErrors(errors);
    renderChecklist(errors);
    drawPreviews();
    var st = $('status');
    if (/\bbad\b/.test(st.className) && attempted) {
      var n = Object.keys(errors).length;
      if (!n) setStatus('', '');
      else setStatus(n === 1 ? 'One field needs attention before you can download.' : n + ' fields need attention before you can download.', 'bad');
    }
  }

  /* ---------- wiring ---------- */
  document.querySelectorAll('[data-path]').forEach(function (el) {
    var path = el.getAttribute('data-path');
    el.addEventListener('input', function () {
      var v = el.value;
      setPath(path, el.hasAttribute('data-number') ? Number(v) : v);
      afterChange();
    });
    el.addEventListener('blur', function () { touched[path] = true; afterChange(); });
  });
  $('ring-on').addEventListener('change', function (e) { state.recordDots.icons.ring.enabled = e.target.checked; afterChange(); });
  $('ring-color').addEventListener('input', function (e) { state.recordDots.icons.ring.color = e.target.value; afterChange(); });
  $('ring-hex').addEventListener('input', function (e) { var v = hexFix(e.target.value); if (v) { state.recordDots.icons.ring.color = v; afterChange('keep-hex'); } });
  $('look-current').addEventListener('click', function () { state.recordDots.icons = LIB.look('current'); afterChange(); });
  $('look-distinct').addEventListener('click', function () { state.recordDots.icons = LIB.look('distinct'); afterChange(); });

  $('reset-btn').addEventListener('click', function () {
    if (!window.confirm('Clear everything on this page and start over?')) return;
    state = LIB.defaults(); touched = {}; attempted = false; setStatus('', '');
    afterChange();
  });
  $('load-btn').addEventListener('click', function () { $('load-file').click(); });
  $('load-file').addEventListener('change', function (e) {
    var f = e.target.files && e.target.files[0];
    if (!f) return;
    var r = new FileReader();
    r.onload = function () {
      try {
        var obj = JSON.parse(String(r.result));
        if (!obj || (!obj.station && !obj.recordDots)) throw new Error('not a settings file');
        state = LIB.fromConfig(obj); touched = {}; attempted = false;
        afterChange(); setStatus('Loaded settings from ' + f.name + '.', 'good');
      } catch (err) {
        setStatus('That file is not a config.json from this page.', 'bad');
      }
      e.target.value = '';
    };
    r.readAsText(f);
  });

  function setStatus(msg, kind) { var s = $('status'); s.textContent = msg; s.className = 'status' + (kind ? ' ' + kind : ''); }

  /* ---------- download ---------- */
  function iconPng(spec, ring) {
    return new Promise(function (resolve, reject) {
      var c = document.createElement('canvas'); c.width = c.height = 128;
      LIB.drawIcon(c.getContext('2d'), 128, spec, ring);
      c.toBlob(function (blob) {
        if (!blob) { reject(new Error('The browser could not make the icon images.')); return; }
        blob.arrayBuffer().then(function (ab) { resolve(new Uint8Array(ab)); }, reject);
      }, 'image/png');
    });
  }

  $('download').addEventListener('click', function () {
    attempted = true;
    var errors = LIB.validate(state);
    afterChange();
    var keys = Object.keys(errors);
    if (keys.length) {
      var first = keys[0], tab = first.indexOf('station.') === 0 ? 'station' : 'dots';
      showTab(tab);
      if (first.indexOf('recordDots.installDir') === 0 || first.indexOf('recordDots.kmlFolder') === 0 || first.indexOf('recordDots.navDataFolder') === 0 || first.indexOf('recordDots.taskName') === 0 || first.indexOf('recordDots.scriptsRef') === 0) $('advanced').open = true;
      var target = document.querySelector('[data-path="' + first + '"]');
      if (target) target.focus();
      setStatus(keys.length === 1 ? 'One field needs attention before you can download.' : keys.length + ' fields need attention before you can download.', 'bad');
      return;
    }
    var btn = $('download'); btn.disabled = true; setStatus('Building your package\u2026', '');
    var cfg = LIB.buildConfig(state), ic = cfg.recordDots.icons;
    Promise.all(LIB.TYPES.map(function (t) { return iconPng(ic[t.key], ic.ring); })).then(function (pngs) {
      var files = [
        { name: 'Install.bat', data: LIB.textBytes(PAYLOAD['Install.bat'], false) },
        { name: 'Uninstall.bat', data: LIB.textBytes(PAYLOAD['Uninstall.bat'], false) },
        { name: 'SETUP.txt', data: LIB.textBytes(LIB.setupText(state), false) },
        { name: 'config.json', data: LIB.textBytes(JSON.stringify(cfg, null, 2) + '\n', false) },
        { name: 'install.ps1', data: LIB.textBytes(PAYLOAD['install.ps1'], true) },
        { name: 'uninstall.ps1', data: LIB.textBytes(PAYLOAD['uninstall.ps1'], true) }
      ];
      LIB.TYPES.forEach(function (t, i) { files.push({ name: 'icons/' + t.key + '.png', data: pngs[i] }); });
      var zipName = 'MaxTools-' + LIB.slug(cfg.station.name) + '-record-dots.zip';
      var blob = new Blob([LIB.makeZip(files)], { type: 'application/zip' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = zipName;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 15000);
      setStatus('Downloaded ' + zipName + '. Open SETUP.txt inside for the next steps.', 'good');
    }).catch(function (err) {
      setStatus('Could not build the package: ' + err.message, 'bad');
    }).then(function () { btn.disabled = false; });
  });

  var resizeTimer;
  window.addEventListener('resize', function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(drawPreviews, 120); });

  /* ---------- start ---------- */
  buildDotRows();
  afterChange();
  // expose for automated checks
  window.__maxtools = { getState: function () { return state; } };
})();
