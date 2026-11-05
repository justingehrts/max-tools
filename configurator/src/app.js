(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var BASE = CFG.pagesBase.replace(/\/$/, '');
  var MARKETS = CFG.markets;
  var byId = {}; MARKETS.forEach(function (m) { byId[m.id] = m; });
  var STORE = 'maxtools.market';

  var S = {
    market: null,
    saved: null,          // saved colors (null = standard)
    updatedUtc: null,     // when the saved custom colors were saved (server time)
    loaded: false,        // saved colors loaded from the server
    blocked: '',          // why saving is off (e.g. could not load)
    savedThisVisit: false,
    edit: LIB.STANDARD.slice(),
    hour: 1,
    saving: false,
    status: { ffg: null, records: null },
    bins: {},             // hour -> ImageData of the bin map
    lines: null,          // county/state lines for the preview ({w,h,county,state}) or 'error'
    keep: []              // last color of each hidden band, restored when it is shown again
  };

  // ---------------------------------------------------------------- small utilities
  function store(get, val) {
    try { if (get) return localStorage.getItem(STORE); localStorage.setItem(STORE, val); } catch (e) { /* private mode etc. */ }
    return null;
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmtTime(iso) {
    var d = new Date(iso); if (isNaN(d)) return 'unknown';
    var t = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    return d.toDateString() === new Date().toDateString() ? t : d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ', ' + t;
  }
  function fmtDate(iso) { var d = new Date(iso); return isNaN(d) ? 'earlier' : d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }); }
  var toastTimer;
  function toast(msg) {
    var t = $('toast'); t.textContent = msg; t.hidden = false; $('announce').textContent = msg;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.hidden = true; }, 1800);
  }
  function copy(text, what) {
    function ok() { toast('Copied ' + what); }
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); ok(); } catch (e) { toast('Copy failed. Select the text and press Ctrl+C.'); }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(ok, fallback); else fallback();
  }
  function getJSON(url) {
    return fetch(url, { cache: 'no-store', credentials: 'same-origin' }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) { return { status: r.status, body: body }; });
    });
  }

  // ---------------------------------------------------------------- status strip
  function loadStatus() {
    var parts = [['ffg', 'FFG', BASE + '/ffg/status.json'], ['records', 'Record dots', BASE + '/records/status.json']];
    Promise.all(parts.map(function (p) {
      return fetch(p[2], { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    })).then(function (res) {
      var bad = false, txt = [];
      res.forEach(function (st, i) {
        S.status[parts[i][0]] = st;
        if (!st) { bad = true; txt.push(parts[i][1] + ': can\'t reach the status page'); return; }
        var stale = LIB.isStale(st.generatedUtc);
        bad = bad || stale;
        txt.push(parts[i][1] + ' ' + fmtTime(st.generatedUtc) + (stale ? ' (older than ' + LIB.STALE_HOURS + ' hours)' : ''));
      });
      $('status').textContent = 'Last build: ' + txt.join(' · ');
      $('status').classList.toggle('bad', bad);
      if (S.market) loadPreview();
    });
  }

  // ---------------------------------------------------------------- market picker
  function renderPicker() {
    var list = LIB.filterMarkets(MARKETS, $('mq').value);
    $('mlist').innerHTML = list.map(function (m) {
      // market names only; call letters still match in the search box (LIB.filterMarkets)
      return '<li><button type="button" data-id="' + esc(m.id) + '">' + esc(m.name) + '</button></li>';
    }).join('');
    $('mnone').hidden = list.length > 0;
  }
  function showPicker() {
    $('picker').hidden = false; $('tools').hidden = true; $('chip').hidden = true;
    $('pick-cancel').hidden = !S.market;
    $('mq').value = ''; renderPicker(); $('mq').focus();
  }
  $('mq').addEventListener('input', renderPicker);
  $('mq').addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') { var b = $('mlist').querySelector('button'); if (b) b.click(); }
    if (ev.key === 'ArrowDown') { var f = $('mlist').querySelector('button'); if (f) { ev.preventDefault(); f.focus(); } }
  });
  $('mlist').addEventListener('keydown', function (ev) {
    var btns = [].slice.call($('mlist').querySelectorAll('button')), i = btns.indexOf(document.activeElement);
    if (ev.key === 'ArrowDown' && i < btns.length - 1) { ev.preventDefault(); btns[i + 1].focus(); }
    if (ev.key === 'ArrowUp') { ev.preventDefault(); (i > 0 ? btns[i - 1] : $('mq')).focus(); }
  });
  $('mlist').addEventListener('click', function (ev) {
    var b = ev.target.closest('button'); if (b) chooseMarket(b.getAttribute('data-id'));
  });
  $('pick-cancel').addEventListener('click', function () { if (S.market) chooseMarket(S.market); });
  $('change').addEventListener('click', function () {
    if (isDirty() && !window.confirm('You have unsaved color changes. Change market and lose them?')) return;
    showPicker();
  });

  function chooseMarket(id) {
    if (!byId[id]) return;
    S.market = id; store(false, id);
    S.bins = {}; S.savedThisVisit = false;
    $('picker').hidden = true; $('tools').hidden = false; $('chip').hidden = false;
    $('chip-name').textContent = byId[id].name;
    S.lines = null; renderUrls(); loadSaved(); loadPreview(); loadLines();
    showTab(tabFromHash() || $('tab-ffg'));
  }

  // ---------------------------------------------------------------- tabs
  // One tab per web app listed in content/apps.json (name, link and tagline are embedded at build time; the write-up is
  // fetched from the Pages site like the other help texts).
  (CFG.apps || []).forEach(function (a) {
    var b = document.createElement('button');
    b.setAttribute('role', 'tab'); b.type = 'button'; b.id = 'tab-' + a.id; b.setAttribute('data-hash', a.id);
    b.setAttribute('aria-controls', 'panel-' + a.id); b.textContent = a.name;
    document.querySelector('[role=tablist]').appendChild(b);
    var d = document.createElement('div');
    d.setAttribute('role', 'tabpanel'); d.id = 'panel-' + a.id; d.setAttribute('aria-labelledby', 'tab-' + a.id); d.hidden = true;
    d.innerHTML = '<p class="muted">' + esc(a.tagline || '') + '</p><a class="open-app" target="_blank" rel="noopener" href="' + esc(a.url) + '">Open ' + esc(a.name) + '</a><div class="appdoc" id="appdoc-' + a.id + '"></div>';
    $('tools').appendChild(d);
  });
  var tabs = [].slice.call(document.querySelectorAll('[role=tab]'));
  function tabFromHash() { return tabs.filter(function (t) { return '#' + t.getAttribute('data-hash') === location.hash; })[0]; }
  function showTab(t, focus) {
    tabs.forEach(function (x) {
      var on = x === t; x.setAttribute('aria-selected', on ? 'true' : 'false'); x.tabIndex = on ? 0 : -1;
      $(x.getAttribute('aria-controls')).hidden = !on;
    });
    if (focus) t.focus();
    try { history.replaceState(null, '', '#' + t.getAttribute('data-hash')); } catch (e) { /* file:// etc. */ }
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { showTab(t); });
    t.addEventListener('keydown', function (ev) {
      var k = ev.key, j = k === 'ArrowRight' ? i + 1 : k === 'ArrowLeft' ? i - 1 : k === 'Home' ? 0 : k === 'End' ? tabs.length - 1 : null;
      if (j === null) return; ev.preventDefault(); showTab(tabs[(j + tabs.length) % tabs.length], true);
    });
  });

  // ---------------------------------------------------------------- URLs
  function renderUrls() {
    $('ffg-urls').innerHTML = LIB.ffgUrls(BASE, S.market).map(function (u) {
      return '<tr><th>' + u.hours + ' hour</th><td class="url">' + esc(u.url) + '</td><td><button type="button" class="small" data-copy="' + esc(u.url) +
        '" data-what="the ' + u.hours + '-hour URL" aria-label="Copy the ' + u.hours + '-hour URL">Copy</button></td></tr>';
    }).join('');
    $('rec-pattern').textContent = BASE + '/records/default/D<day>_<TYPE>.kmz';
    $('rec-urls').innerHTML = '<tr><th></th>' + LIB.TYPES.map(function (t) { return '<th scope="col">' + t + '</th>'; }).join('') + '</tr>' +
      LIB.DAYS.map(function (d) {
        return '<tr><th scope="row">Day ' + d + '</th>' + LIB.TYPES.map(function (t) {
          var u = LIB.recordUrl(BASE, d, t);
          return '<td><button type="button" class="small" data-copy="' + esc(u) + '" data-what="Day ' + d + ' ' + t + '" aria-label="Copy the Day ' + d + ' ' + t + ' link" title="' + esc(u) + '">Copy</button></td>';
        }).join('') + '</tr>';
      }).join('');
  }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-copy]'); if (b) copy(b.getAttribute('data-copy'), b.getAttribute('data-what'));
  });
  $('copy-all').addEventListener('click', function () { copy(LIB.allRecordUrls(BASE).join('\n'), 'all 28 links'); });

  // ---------------------------------------------------------------- saved colors
  function savedColors() { return S.saved || LIB.STANDARD; }
  function isDirty() { return S.market && !LIB.sameColors(S.edit, savedColors()); }

  function loadSaved() {
    S.loaded = false; S.blocked = ''; S.saved = null; S.updatedUtc = null;
    setEdit(LIB.STANDARD.slice());
    setState('Loading your saved colors...', '');
    var m = S.market;
    getJSON(CFG.api + '?market=' + encodeURIComponent(m)).then(function (r) {
      if (m !== S.market) return;
      if (r.status === 200 && r.body.ok) {
        S.saved = r.body.ffg ? r.body.ffg.colors : null; S.updatedUtc = r.body.updatedUtc; S.loaded = true;
        setEdit(savedColors().slice()); setState('', '');
      } else {
        S.blocked = (r.body && r.body.error) || 'The save service answered with an error (' + r.status + ').';
        setState('Could not load your saved colors, so saving is off. ' + S.blocked, 'bad');
      }
      refresh();
    }, function () {
      if (m !== S.market) return;
      S.blocked = 'Could not reach the save service.';
      setState('Could not reach the save service, so saving is off. Reload the page to try again.', 'bad'); refresh();
    });
  }

  // ---------------------------------------------------------------- editor
  function buildRows() {
    $('rows').innerHTML = LIB.STANDARD.map(function (_, i) {
      var lab = LIB.bandLabel(i);
      return '<li><span id="lab-' + i + '">' + lab + '</span>' +
        '<label class="show"><input type="checkbox" id="v-' + i + '" checked aria-describedby="lab-' + i + '"> Show</label>' +
        '<input type="color" id="c-' + i + '" aria-labelledby="lab-' + i + '" title="Pick a color for ' + lab + '">' +
        '<input type="text" class="hex" id="h-' + i + '" maxlength="7" spellcheck="false" autocomplete="off" aria-label="' + lab + ' color code" aria-describedby="e-' + i + '">' +
        '<span class="err" id="e-' + i + '"></span></li>';
    }).join('');
    LIB.STANDARD.forEach(function (_, i) {
      $('c-' + i).addEventListener('input', function (ev) { S.edit[i] = ev.target.value; $('h-' + i).value = ev.target.value; refresh(); });
      $('h-' + i).addEventListener('input', function (ev) {
        S.edit[i] = ev.target.value; var v = LIB.normHex(ev.target.value); if (v) $('c-' + i).value = v; refresh();
      });
      $('h-' + i).addEventListener('blur', function (ev) { if (S.edit[i] === LIB.NONE) return; var v = LIB.normHex(ev.target.value); if (v) { ev.target.value = v; S.edit[i] = v; } refresh(); });
      $('v-' + i).addEventListener('change', function (ev) {
        if (ev.target.checked) { S.edit[i] = S.keep[i] || LIB.STANDARD[i]; }
        else { S.keep[i] = LIB.normHex($('h-' + i).value) || LIB.STANDARD[i]; S.edit[i] = LIB.NONE; }
        syncRow(i); refresh();
      });
    });
  }
  // A hidden band keeps showing its last color (greyed out) so un-hiding brings it back.
  function syncRow(i) {
    var hidden = S.edit[i] === LIB.NONE, c = hidden ? (S.keep[i] || LIB.STANDARD[i]) : S.edit[i];
    $('v-' + i).checked = !hidden;
    $('h-' + i).value = c; $('c-' + i).value = LIB.normHex(c) || '#000000';
    $('h-' + i).disabled = hidden; $('c-' + i).disabled = hidden;
    $('h-' + i).closest('li').classList.toggle('hidden-band', hidden);
  }
  function setEdit(colors) {
    S.edit = colors.slice();
    S.edit.forEach(function (c, i) { syncRow(i); $('e-' + i).textContent = ''; });
    refresh();
  }
  function setState(msg, kind) { var e = $('ffg-state'); e.textContent = msg; e.className = 'state' + (kind ? ' ' + kind : ''); }

  function refresh() {
    var errs = LIB.colorErrors(S.edit);
    S.edit.forEach(function (_, i) {
      $('h-' + i).setAttribute('aria-invalid', errs[i] ? 'true' : 'false');
      if (errs[i] || $('e-' + i).getAttribute('data-server') !== 'y') $('e-' + i).textContent = errs[i] || '';
    });
    $('rows-err').textContent = errs.all || '';
    var dirty = isDirty(), valid = Object.keys(errs).length === 0;
    $('save').disabled = !dirty || !valid || S.saving || !!S.blocked || !S.loaded;
    $('discard').hidden = !dirty || S.saving;
    $('standard').disabled = LIB.isStandard(S.edit) || S.saving;
    var shown = valid ? S.edit : savedColors();
    function swatch(c) { return c === LIB.NONE ? ' class="hid"' : ' style="background:' + LIB.normHex(c) + '"'; }
    $('ramp').innerHTML = shown.map(function (c) { return '<span' + swatch(c) + '></span>'; }).join('');
    $('legend').innerHTML = shown.map(function (c, i) { return '<li><i' + swatch(c) + '></i>' + LIB.bandLabel(i) + (c === LIB.NONE ? ' (hidden)' : '') + '</li>'; }).join('');
    var name = S.market ? byId[S.market].name : '';
    $('ffg-title').textContent = S.saved ? 'Custom colors for ' + name : 'Standard colors for ' + name;
    var pm = LIB.matchPreset(S.edit);
    [].forEach.call(document.querySelectorAll('[data-preset]'), function (b) { b.setAttribute('aria-pressed', pm && pm.id === b.getAttribute('data-preset') ? 'true' : 'false'); });
    $('preset-note').textContent = pm ? pm.name + ': ' + pm.note : 'Your own colors.';
    if (S.loaded && !S.saving && !S.blocked && $('ffg-state').className.indexOf('bad') < 0 && $('ffg-state').className.indexOf('good') < 0) {
      setState(dirty ? 'Unsaved changes.' + (LIB.isStandard(S.edit) ? ' Saving switches ' + name + ' back to the standard colors.' : '') :
               (S.saved ? 'These are your saved colors (saved ' + fmtDate(S.updatedUtc) + ').' : 'These are the standard colors.'), '');
    }
    draw();
  }
  function clearMessages() { setState('', ''); [].forEach.call(document.querySelectorAll('.rows .err'), function (e) { e.removeAttribute('data-server'); }); }

  $('standard').addEventListener('click', function () { clearMessages(); setEdit(LIB.STANDARD.slice()); });
  $('discard').addEventListener('click', function () { clearMessages(); setEdit(savedColors().slice()); });
  // Capture phase: clear an old 'Saved'/'Not saved' message before the field's own handler refreshes the state line.
  ['input', 'change'].forEach(function (evn) { $('rows').addEventListener(evn, function () { if ($('ffg-state').className !== 'state') clearMessages(); }, true); });

  $('save').addEventListener('click', function () {
    if ($('save').disabled) return;
    // Replacing a custom look someone saved earlier: ask first (not again for one saved during this visit).
    if (S.saved && !S.savedThisVisit) {
      $('confirm-text').textContent = byId[S.market].name + ' already has custom colors, saved ' + fmtDate(S.updatedUtc) +
        '. Every station in the market uses them. Replace them?';
      var dlg = $('confirm');
      if (typeof dlg.showModal === 'function') { dlg.showModal(); $('confirm-no').focus(); return; }
      if (!window.confirm($('confirm-text').textContent)) return;
    }
    doSave();
  });
  $('confirm-yes').addEventListener('click', function () { $('confirm').close(); doSave(); });
  $('confirm-no').addEventListener('click', function () { $('confirm').close(); $('save').focus(); });

  function doSave() {
    var m = S.market, body = LIB.savePayload(m, S.edit, S.updatedUtc);
    S.saving = true; setState('Saving...', ''); refresh();
    fetch(CFG.api, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
                     headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'configurator' }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (b) { return { status: r.status, body: b }; }); })
      .then(function (r) {
        S.saving = false;
        if (m !== S.market) return;
        if (r.status === 200 && r.body.ok) {
          S.saved = body.ffg ? body.ffg.colors : null; S.updatedUtc = r.body.updatedUtc; S.savedThisVisit = true;
          setEdit(savedColors().slice());
          if (!r.body.changed) setState('Nothing to save: these colors are already saved.', 'good');
          else setStateHtml('Saved. The new colors go live ' + esc(r.body.goesLive) + '. The URLs stay the same. ' +
                            '<a href="' + esc(CFG.buildsUrl) + '" target="_blank" rel="noopener">Build status</a>', 'good');
        } else if (r.status === 400 && r.body.errors) {
          var e = LIB.serverErrors(r.body.errors);
          Object.keys(e.rows).forEach(function (i) { $('e-' + i).textContent = e.rows[i]; $('e-' + i).setAttribute('data-server', 'y'); $('h-' + i).setAttribute('aria-invalid', 'true'); });
          setState('Not saved. ' + (e.form.join(' ') || 'Fix the colors marked below.'), 'bad');
        } else if (r.status === 409) {
          setStateHtml('Not saved. ' + esc(r.body.error || 'Someone else saved this market after you opened the page.') +
                       ' <button type="button" class="link" id="reload-saved">Load their colors</button>', 'bad');
          $('reload-saved').addEventListener('click', loadSaved);
        } else if (r.status === 401) {
          setState('Not saved. Your login expired. Reload the page and sign in again.', 'bad');
        } else {
          setState('Not saved. ' + (r.body.error || 'The save service answered with an error (' + r.status + '). Try again in a minute.'), 'bad');
        }
        refresh();
      }, function () {
        S.saving = false; setState('Not saved. Could not reach the save service. Check your connection and try again.', 'bad'); refresh();
      });
  }
  function setStateHtml(html, kind) { var e = $('ffg-state'); e.innerHTML = html; e.className = 'state' + (kind ? ' ' + kind : ''); }

  // ---------------------------------------------------------------- preview
  function buildDurations() {
    $('dur').innerHTML = LIB.HOURS.map(function (h) {
      return '<label><input type="radio" name="dur" value="' + h + '"' + (h === S.hour ? ' checked' : '') + '><span>' + h + ' hour</span></label>';
    }).join('');
    $('dur').addEventListener('change', function (ev) { S.hour = +ev.target.value; loadPreview(); });
  }
  function loadPreview() {
    if (!S.market) return;
    var m = S.market, h = S.hour;
    if (S.bins[h]) { draw(); return; }
    var st = S.status.ffg, v = st ? encodeURIComponent(st.generatedUtc) : Date.now();
    var img = new Image(); img.crossOrigin = 'anonymous';
    img.onload = function () {
      if (m !== S.market) return;
      var c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
      var cx = c.getContext('2d'); cx.drawImage(img, 0, 0);
      try { S.bins[h] = cx.getImageData(0, 0, c.width, c.height); } catch (e) { S.bins[h] = 'error'; }
      if (h === S.hour) draw();
    };
    img.onerror = function () { if (m === S.market) { S.bins[h] = 'error'; if (h === S.hour) draw(); } };
    img.src = BASE + '/markets/' + m + '/bins_' + h + 'hr.png?v=' + v;
    $('pv-note').textContent = 'Loading the preview...';
  }
  var off = document.createElement('canvas');
  function draw() {
    var cv = $('pv'), cx = cv.getContext('2d'), b = S.bins[S.hour];
    cx.fillStyle = '#24313c'; cx.fillRect(0, 0, cv.width, cv.height);
    cx.strokeStyle = 'rgba(255,255,255,0.06)'; cx.lineWidth = 1;
    for (var x = 0; x <= cv.width; x += 60) { cx.beginPath(); cx.moveTo(x + .5, 0); cx.lineTo(x + .5, cv.height); cx.stroke(); }
    for (var y = 0; y <= cv.height; y += 60) { cx.beginPath(); cx.moveTo(0, y + .5); cx.lineTo(cv.width, y + .5); cx.stroke(); }
    if (!b) { drawLines(cx, cv); return; }
    if (b === 'error') { drawLines(cx, cv); $('pv-note').textContent = 'The preview is not available right now. The colors and URLs work as usual.'; return; }
    var errs = LIB.colorErrors(S.edit), colors = Object.keys(errs).length ? savedColors() : S.edit;
    off.width = b.width; off.height = b.height;
    var oc = off.getContext('2d'), out = oc.createImageData(b.width, b.height);
    LIB.recolor(b.data, colors, out.data); oc.putImageData(out, 0, 0);
    cx.drawImage(off, 0, 0, cv.width, cv.height);
    drawLines(cx, cv);
    var st = S.status.ffg;
    $('pv-note').textContent = byId[S.market].name + ', ' + S.hour + '-hour guidance' + (st ? ', built ' + fmtTime(st.generatedUtc) : '') +
      '. Same map box and shapes as the layer in Max; no basemap here.';
  }

  function loadLines() {
    var m = S.market;
    fetch(BASE + '/lines/' + m + '.json').then(function (r) { if (!r.ok) throw r; return r.json(); })
      .then(function (d) { if (m === S.market) { S.lines = d; draw(); } }, function () { if (m === S.market) S.lines = 'error'; });
  }
  function drawLines(cx, cv) {
    var L = S.lines;
    if (!$('lines').checked || !L || L === 'error') return;
    var k = cv.width / L.w;
    function stroke(list, color, width) {
      cx.strokeStyle = color; cx.lineWidth = width; cx.lineJoin = 'round';
      list.forEach(function (p) {
        cx.beginPath(); cx.moveTo(p[0] * k, p[1] * k);
        for (var i = 2; i < p.length; i += 2) cx.lineTo(p[i] * k, p[i + 1] * k);
        cx.stroke();
      });
    }
    // a faint light halo under a dark line reads on both light and dark bands
    stroke(L.county, 'rgba(255,255,255,0.35)', 2.2); stroke(L.county, 'rgba(20,24,28,0.55)', 0.9);
    stroke(L.state, 'rgba(255,255,255,0.5)', 3.4); stroke(L.state, 'rgba(10,12,14,0.85)', 1.6);
  }
  $('lines').addEventListener('change', draw);

  // ---------------------------------------------------------------- presets
  function buildPresets() {
    $('presets').innerHTML = LIB.PRESETS.map(function (p) {
      return '<button type="button" data-preset="' + esc(p.id) + '" aria-pressed="false" title="' + esc(p.note) + '"><span class="mini" aria-hidden="true">' +
        p.colors.map(function (c) { return '<span style="background:' + c + '"></span>'; }).join('') + '</span><b>' + esc(p.name) + '</b></button>';
    }).join('');
    $('presets').addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-preset]'); if (!b) return;
      var p = LIB.PRESETS.filter(function (x) { return x.id === b.getAttribute('data-preset'); })[0];
      clearMessages(); setEdit(p.colors.slice());
    });
  }

  // ---------------------------------------------------------------- help text (written by Justin in content/*.md)
  function loadHelp(name, el, title) {
    fetch(BASE + '/help/' + name + '.html', { cache: 'no-store' }).then(function (r) { if (!r.ok) throw r; return r.text(); })
      .then(function (html) { $(el).innerHTML = html; }, function () {
        $(el).innerHTML = '<h2>' + esc(title) + '</h2><p>Help is on the <a href="' + esc(BASE) + '/" target="_blank" rel="noopener">public URL page</a>.</p>';
      });
  }

  // ---------------------------------------------------------------- start
  buildRows(); buildDurations(); buildPresets();
  window.addEventListener('beforeunload', function (ev) { if (isDirty() && !S.saving) { ev.preventDefault(); ev.returnValue = ''; } });
  loadStatus(); setInterval(loadStatus, 5 * 60 * 1000);
  loadHelp('record-dots-in-max', 'rec-help', 'Changing how the dots look in Max');
  loadHelp('add-layer-in-max', 'add-help', 'Adding a layer in Max');
  (CFG.apps || []).forEach(function (a) { loadHelp('app-' + a.id, 'appdoc-' + a.id, a.name); });
  var remembered = store(true);
  if (remembered && byId[remembered]) chooseMarket(remembered); else showPicker();
})();
