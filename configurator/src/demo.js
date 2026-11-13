// DEMO ONLY: stands in for api/save.php so the configurator can be shown without a login. Nothing is sent anywhere and nothing is
// kept: "saved" colors live in this window's memory and vanish on reload. Included only by `build.py --demo` (see build.py).
var DEMO = (function () {
  'use strict';
  var store = {};                                   // market id -> { ffg: {colors}|null, updatedUtc }
  function later(ms, value) { return new Promise(function (resolve) { setTimeout(function () { resolve(value); }, ms); }); }
  function known(id) { return CFG.markets.some(function (m) { return m.id === id; }); }

  // Same rules as the real service (docs/GUI.md): 7 bands, each #rrggbb or "none", at least one visible.
  function errorsFor(body) {
    var err = {};
    if (!body || !known(body.market)) { err.market = 'Pick a market from the list.'; return err; }
    if (body.ffg === null) return err;
    var c = body.ffg && body.ffg.colors;
    if (!Array.isArray(c) || c.length !== 7) { err['ffg.colors'] = 'Exactly 7 colors are needed.'; return err; }
    c.forEach(function (v, i) { if (!LIB.normColor(v)) err['ffg.colors[' + i + ']'] = 'Use a color like #a50f15, or hide the band.'; });
    if (!Object.keys(err).length && c.every(function (v) { return v === LIB.NONE; })) err['ffg.colors'] = 'Show at least one band.';
    return err;
  }

  return {
    get: function (market) {
      var cur = store[market];
      return later(250, { status: 200, body: { ok: true, market: market, ffg: cur ? cur.ffg : null, updatedUtc: cur ? cur.updatedUtc : null } });
    },
    post: function (body) {
      var errs = errorsFor(body);
      if (Object.keys(errs).length) return later(500, { status: 400, body: { ok: false, errors: errs } });
      var cur = store[body.market] || { ffg: null, updatedUtc: null };
      if ((cur.updatedUtc || null) !== (body.expectUpdatedUtc || null)) {
        return later(500, { status: 409, body: { ok: false, error: 'Someone saved this market after you opened the page. Reload to see their colors.', updatedUtc: cur.updatedUtc } });
      }
      var changed = JSON.stringify(cur.ffg) !== JSON.stringify(body.ffg);
      if (changed) store[body.market] = { ffg: body.ffg, updatedUtc: new Date().toISOString().replace(/\.\d+Z$/, 'Z') };
      var saved = store[body.market] || cur;
      return later(700, { status: 200, body: { ok: true, changed: changed, updatedUtc: saved.updatedUtc, urls: {}, goesLive: 'demo' } });
    }
  };
})();
