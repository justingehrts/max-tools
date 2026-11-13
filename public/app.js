// The public page: everything a station needs day to day, no login. Uses LIB (configurator/src/lib.js) for the address lists.
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var BASE = CFG.base.replace(/\/$/, '');
  var MARKETS = CFG.markets, byId = {};
  MARKETS.forEach(function (m) { byId[m.id] = m; });
  var STORE = 'maxtools.public.market';
  var market = null;

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function store(get, val) { try { if (get) return localStorage.getItem(STORE); localStorage.setItem(STORE, val); } catch (e) { /* private mode etc. */ } return null; }

  // ---------------------------------------------------------------- copy + toast
  var toastTimer;
  function toast(msg) { var t = $('toast'); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.hidden = true; }, 1800); }
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
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-copy]'); if (b) copy(b.getAttribute('data-copy'), b.getAttribute('data-what'));
  });
  $('copy-all').addEventListener('click', function () { copy(LIB.allRecordUrls(BASE).join('\n'), 'all 28 links'); });

  // ---------------------------------------------------------------- status strip
  function fmtTime(iso) {
    var d = new Date(iso); if (isNaN(d)) return 'unknown';
    var t = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    return d.toDateString() === new Date().toDateString() ? t : d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ', ' + t;
  }
  function loadStatus() {
    var parts = [['FFG', BASE + '/ffg/status.json'], ['Record dots', BASE + '/records/status.json']];
    Promise.all(parts.map(function (p) {
      return fetch(p[1], { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    })).then(function (res) {
      var bad = false, txt = [];
      res.forEach(function (st, i) {
        if (!st) { bad = true; txt.push(parts[i][0] + ": can't reach the status page"); return; }
        var stale = LIB.isStale(st.generatedUtc); bad = bad || stale;
        txt.push(parts[i][0] + ' ' + fmtTime(st.generatedUtc) + (stale ? ' (older than ' + LIB.STALE_HOURS + ' hours)' : ''));
      });
      $('status').textContent = 'Last build: ' + txt.join(' · ');
      $('status').classList.toggle('bad', bad);
    });
  }

  // ---------------------------------------------------------------- tabs
  var tabs = [].slice.call(document.querySelectorAll('[role=tab]'));
  function tabFromHash() { return tabs.filter(function (t) { return '#' + t.getAttribute('data-hash') === location.hash; })[0]; }
  function showTab(t, focus) {
    tabs.forEach(function (x) {
      var on = x === t; x.setAttribute('aria-selected', on ? 'true' : 'false'); x.tabIndex = on ? 0 : -1;
      $(x.getAttribute('aria-controls')).hidden = !on;
    });
    if (focus) t.focus();
    try { history.replaceState(null, '', location.pathname + location.search + '#' + t.getAttribute('data-hash')); } catch (e) { /* file:// etc. */ }
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { showTab(t); });
    t.addEventListener('keydown', function (ev) {
      var k = ev.key, j = k === 'ArrowRight' ? i + 1 : k === 'ArrowLeft' ? i - 1 : k === 'Home' ? 0 : k === 'End' ? tabs.length - 1 : null;
      if (j === null) return; ev.preventDefault(); showTab(tabs[(j + tabs.length) % tabs.length], true);
    });
  });

  // ---------------------------------------------------------------- record dots (the same for everyone)
  $('rec-pattern').textContent = BASE + '/records/default/D<day>_<TYPE>.kmz';
  $('rec-urls').innerHTML = '<tr><th></th>' + LIB.TYPES.map(function (t) { return '<th scope="col">' + t + '</th>'; }).join('') + '</tr>' +
    LIB.DAYS.map(function (d) {
      return '<tr><th scope="row">Day ' + d + '</th>' + LIB.TYPES.map(function (t) {
        var u = LIB.recordUrl(BASE, d, t);
        return '<td><button type="button" class="small" data-copy="' + esc(u) + '" data-what="Day ' + d + ' ' + t + '" aria-label="Copy the Day ' + d + ' ' + t + ' address" title="' + esc(u) + '">Copy</button></td>';
      }).join('') + '</tr>';
    }).join('');

  // ---------------------------------------------------------------- flash flood guidance: pick a market, then its addresses
  function renderPicker() {
    var list = LIB.filterMarkets(MARKETS, $('mq').value);
    $('mlist').innerHTML = list.map(function (m) { return '<li><button type="button" data-id="' + esc(m.id) + '">' + esc(m.name) + '</button></li>'; }).join('');
    $('mnone').hidden = list.length > 0;
  }
  function showPicker(focus) {
    $('picker').hidden = false; $('chosen').hidden = true;
    $('pick-cancel').hidden = !market; $('mq').value = ''; renderPicker();
    if (focus === true) $('mq').focus();                       // only when asked for: never steal focus on page load
  }
  function chooseMarket(id) {
    if (!byId[id]) return;
    market = id; store(false, id);
    $('picker').hidden = true; $('chosen').hidden = false;
    $('ffg-title').textContent = 'Flash flood guidance for ' + byId[id].name;
    $('ffg-urls').innerHTML = LIB.ffgUrls(BASE, id).map(function (u) {
      return '<tr><th>' + u.hours + ' hour</th><td class="url">' + esc(u.url) + '</td><td><button type="button" class="small" data-copy="' + esc(u.url) +
        '" data-what="the ' + u.hours + '-hour address" aria-label="Copy the ' + u.hours + '-hour address">Copy</button></td></tr>';
    }).join('');
    if (CFG.configuratorUrl) {
      $('custom').hidden = false;
      $('customize').href = CFG.configuratorUrl + (CFG.configuratorUrl.indexOf('?') < 0 ? '?' : '&') + 'market=' + encodeURIComponent(id);
    }
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
  $('mlist').addEventListener('click', function (ev) { var b = ev.target.closest('button'); if (b) chooseMarket(b.getAttribute('data-id')); });
  $('change').addEventListener('click', function () { showPicker(true); });
  $('pick-cancel').addEventListener('click', function () { if (market) chooseMarket(market); });

  // ---------------------------------------------------------------- start
  var fromLink = (new URLSearchParams(location.search).get('market') || '').toLowerCase();   // sent by the private configurator
  var remembered = byId[fromLink] ? fromLink : store(true);
  if (remembered && byId[remembered]) chooseMarket(remembered); else showPicker();
  showTab(tabFromHash() || tabs[0]);
  loadStatus(); setInterval(loadStatus, 5 * 60 * 1000);
})();
