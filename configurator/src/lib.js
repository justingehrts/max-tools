// Pure helpers for the configurator (no DOM). Tested by configurator/test_lib.js under Node.
var LIB = (function () {
  'use strict';
  // Must match tools/build_ffg.py (STANDARD, BOUNDS) and the server's rules (configurator/api/lib.php).
  var STANDARD = ['#67000d', '#a50f15', '#cb181d', '#ef3b2c', '#fc9272', '#fff5f0', '#d9d9d9'];
  var BOUNDS = [0, 0.5, 0.75, 1, 1.5, 2, 3];
  var HOURS = [1, 3, 6];
  var TYPES = ['HIMAX', 'LOMAX', 'HIMIN', 'LOMIN'];
  var DAYS = [1, 2, 3, 4, 5, 6, 7];
  var STALE_HOURS = 3;
  // Ramp presets, most dangerous band first. Checked by tools/check_ramps.py (lightness changes in one direction; every
  // neighbouring pair stays distinguishable for normal, protan, deutan and tritan vision; Rosen et al. 2026, JOM 14(13)).
  // "legacy": true = shown for continuity but does not pass those checks.
  var PRESETS = /*PRESETS*/[
    {"id": "standard", "name": "Standard", "legacy": true,
     "note": "Today's look. The two lightest bands are hard to tell apart for some color-blind viewers.",
     "colors": ["#67000d", "#a50f15", "#cb181d", "#ef3b2c", "#fc9272", "#fff5f0", "#d9d9d9"]},
    {"id": "standard-refined", "name": "Standard, refined",
     "note": "Nearly the same look, with even lightness steps so every band stays distinct for color-blind viewers.",
     "colors": ["#6d001a", "#a20015", "#cf2920", "#ef5b3d", "#ee977e", "#ecc8c3", "#f3f3f3"]},
    {"id": "reds", "name": "Reds",
     "note": "One hue from dark red to near white. Best on light or satellite maps.",
     "colors": ["#790010", "#aa1017", "#d53222", "#f35f40", "#ff9171", "#ffc1ab", "#ffede5"]},
    {"id": "blues", "name": "Blues",
     "note": "One hue from navy to near white. Reads as water.",
     "colors": ["#003577", "#0053a3", "#0075c5", "#0095d9", "#62b6e9", "#a5d5f4", "#e2f3fe"]},
    {"id": "dark-maps", "name": "For dark maps",
     "note": "The most urgent band is the brightest (yellow), fading to deep purple, so it stands out on dark basemaps.",
     "colors": ["#fffb81", "#ffc81e", "#fc932c", "#e26341", "#ba3b49", "#8a1d45", "#4d1249"]}
  ]/*END PRESETS*/;

  function bandLabel(i) {
    var f = function (x) { return x.toFixed(2); };
    if (i === 0) return 'Under ' + f(BOUNDS[1]) + ' in';
    if (i === BOUNDS.length - 1) return f(BOUNDS[i]) + ' in and up';
    return f(BOUNDS[i]) + ' to ' + f(BOUNDS[i + 1]) + ' in';
  }

  /** '#A50F15', 'a50f15', ' #a50f15 ' -> '#a50f15'; anything else -> null. Same rule as the server (no newlines etc.). */
  function normHex(v) {
    if (typeof v !== 'string') return null;
    var s = v.trim();
    if (s.charAt(0) !== '#') s = '#' + s;
    return /^#[0-9a-fA-F]{6}$/.test(s) ? s.toLowerCase() : null;
  }

  function sameColors(a, b) {
    if (!a || !b || a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) if (normHex(a[i]) !== normHex(b[i])) return false;
    return true;
  }

  function isStandard(colors) { return sameColors(colors, STANDARD); }

  /** What to send: null when the colors are the standard ones (the server then removes the override). */
  function savePayload(market, colors, expectUpdatedUtc) {
    var clean = colors.map(normHex);
    return { market: market, ffg: isStandard(clean) ? null : { colors: clean }, expectUpdatedUtc: expectUpdatedUtc || null };
  }

  /** Per-row errors for the editor: { index: message }. */
  function colorErrors(colors) {
    var err = {};
    colors.forEach(function (c, i) { if (!normHex(c)) err[i] = 'Use a color like #a50f15.'; });
    return err;
  }

  /** Map server field errors ("ffg.colors[3]") to editor rows; others go to 'form'. */
  function serverErrors(errors) {
    var out = { rows: {}, form: [] };
    Object.keys(errors || {}).forEach(function (k) {
      var m = /^ffg\.colors\[(\d)\]$/.exec(k);
      if (m) out.rows[+m[1]] = errors[k]; else out.form.push(errors[k]);
    });
    return out;
  }

  function ffgUrls(base, market) {
    return HOURS.map(function (h) { return { hours: h, url: base + '/markets/' + market + '/Custom_FFG_' + h + 'hr.kmz' }; });
  }
  function recordUrl(base, day, type) { return base + '/records/default/D' + day + '_' + type + '.kmz'; }
  function allRecordUrls(base) {
    var out = [];
    DAYS.forEach(function (d) { TYPES.forEach(function (t) { out.push(recordUrl(base, d, t)); }); });
    return out;
  }

  function hoursOld(isoUtc, nowMs) {
    var t = Date.parse(isoUtc);
    return isNaN(t) ? Infinity : ((nowMs === undefined ? Date.now() : nowMs) - t) / 3600000;
  }
  function isStale(isoUtc, nowMs) { return !(hoursOld(isoUtc, nowMs) <= STALE_HOURS); }

  /**
   * Recolor a bin map. bins: RGBA bytes of the grayscale bin PNG (R = band 0..6, 255 = none).
   * Returns RGBA bytes: band colors fully opaque, everything else transparent. Same colors the KMZ would use.
   */
  function recolor(bins, colors, out) {
    var rgb = colors.map(function (c) { var h = normHex(c) || '#000000'; return [parseInt(h.substr(1, 2), 16), parseInt(h.substr(3, 2), 16), parseInt(h.substr(5, 2), 16)]; });
    out = out || new Uint8ClampedArray(bins.length);
    for (var i = 0; i < bins.length; i += 4) {
      var b = bins[i];
      if (b < rgb.length && bins[i + 3] > 0) { out[i] = rgb[b][0]; out[i + 1] = rgb[b][1]; out[i + 2] = rgb[b][2]; out[i + 3] = 255; }
      else { out[i] = out[i + 1] = out[i + 2] = out[i + 3] = 0; }
    }
    return out;
  }

  /** Markets whose name or call letters contain the query (case-insensitive). */
  function filterMarkets(markets, q) {
    q = (q || '').trim().toLowerCase();
    if (!q) return markets.slice();
    return markets.filter(function (m) { return (m.name + ' ' + (m.stations || []).join(' ')).toLowerCase().indexOf(q) >= 0; });
  }

  /** The preset whose colors equal these, or null. */
  function matchPreset(colors) { for (var i = 0; i < PRESETS.length; i++) if (sameColors(colors, PRESETS[i].colors)) return PRESETS[i]; return null; }

  return { STANDARD: STANDARD, PRESETS: PRESETS, matchPreset: matchPreset, BOUNDS: BOUNDS, HOURS: HOURS, TYPES: TYPES, DAYS: DAYS, STALE_HOURS: STALE_HOURS,
           bandLabel: bandLabel, normHex: normHex, sameColors: sameColors, isStandard: isStandard, savePayload: savePayload,
           colorErrors: colorErrors, serverErrors: serverErrors, ffgUrls: ffgUrls, recordUrl: recordUrl,
           allRecordUrls: allRecordUrls, hoursOld: hoursOld, isStale: isStale, recolor: recolor, filterMarkets: filterMarkets };
})();
if (typeof module !== 'undefined') module.exports = LIB;
