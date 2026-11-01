/* Configurator logic. No DOM access here, so it can be tested in Node. */
(function (root) {
  'use strict';
  var LIB = {};

  LIB.TYPES = [
    { key: 'himax', title: 'Record high', note: 'Forecast high at or near a record high' },
    { key: 'lomax', title: 'Record cool high', note: 'Forecast high at or near the lowest high on record' },
    { key: 'himin', title: 'Record warm low', note: 'Forecast low at or near the highest low on record' },
    { key: 'lomin', title: 'Record low', note: 'Forecast low at or near a record low' }
  ];
  LIB.SHAPES = ['circle', 'square', 'diamond', 'triangle'];
  LIB.INTERVALS = [30, 60, 120];
  LIB.DAYS = 7;

  var LOOKS = {
    current: {
      ring: { enabled: true, color: '#e2e2e2' },
      himax: { shape: 'circle', color: '#e30404' },
      lomax: { shape: 'circle', color: '#8797e8' },
      himin: { shape: 'circle', color: '#ff8c00' },
      lomin: { shape: 'circle', color: '#0021cf' }
    },
    distinct: {
      ring: { enabled: true, color: '#e2e2e2' },
      himax: { shape: 'triangle', color: '#d55e00' },
      lomax: { shape: 'square', color: '#56b4e9' },
      himin: { shape: 'diamond', color: '#e69f00' },
      lomin: { shape: 'circle', color: '#0072b2' }
    }
  };
  LIB.look = function (name) { return JSON.parse(JSON.stringify(LOOKS[name])); };

  LIB.defaults = function () {
    return {
      station: { name: '', contactEmail: '', maxMachine: '' },
      recordDots: {
        intervalMinutes: 60,
        installDir: 'C:\\LOCAL\\Scripts\\daily-records',
        kmlFolder: 'D:\\WSI\\DigitalMedia\\Custom\\KML\\record-dots',
        navDataFolder: 'D:\\WSI\\DigitalMedia\\Custom\\NavImportedData',
        taskName: 'Record Dots - Fetch Daily Records',
        scriptsRef: 'main',
        icons: LIB.look('current')
      }
    };
  };

  /* ---------- validation ---------- */
  var RE_NAME = /^[A-Za-z0-9][A-Za-z0-9 -]{0,29}$/;
  var RE_EMAIL = /^[^\s@"'<>`;,]+@[^\s@"'<>`;,]+\.[A-Za-z]{2,}$/;
  var RE_HOST = /^[A-Za-z0-9][A-Za-z0-9-]{0,62}$/;
  var RE_PATH = /^[A-Za-z]:\\[^<>:"\/|?*'`$;%&^\[\]{}\r\n]*$/;
  var RE_TASK = /^[A-Za-z0-9][A-Za-z0-9 ._-]{0,60}$/;
  var RE_REF = /^[A-Za-z0-9._\/-]{1,64}$/;
  var RE_HEX = /^#[0-9a-fA-F]{6}$/;

  LIB.normalizePath = function (p) {
    p = String(p == null ? '' : p).trim();
    while (p.length > 3 && /\\$/.test(p)) p = p.slice(0, -1);
    return p;
  };

  LIB.validate = function (s) {
    var e = {};
    var st = s.station, rd = s.recordDots;
    if (!st.name.trim()) e['station.name'] = 'Enter your station\'s call letters or name.';
    else if (!RE_NAME.test(st.name.trim())) e['station.name'] = 'Use letters, numbers, spaces and hyphens only (up to 30 characters).';
    if (!st.contactEmail.trim()) e['station.contactEmail'] = 'Enter an email address the National Weather Service can reach.';
    else if (!RE_EMAIL.test(st.contactEmail.trim())) e['station.contactEmail'] = 'That does not look like an email address.';
    if (st.maxMachine.trim() && !RE_HOST.test(st.maxMachine.trim())) e['station.maxMachine'] = 'Use letters, numbers and hyphens only, like WBNS-TVDC-2.';

    [['installDir', 'Script folder'], ['kmlFolder', 'KMZ folder'], ['navDataFolder', 'CSV folder']].forEach(function (p) {
      var v = LIB.normalizePath(rd[p[0]]);
      if (!v) e['recordDots.' + p[0]] = 'Enter a full Windows path, like D:\\Folder.';
      else if (!RE_PATH.test(v)) e['recordDots.' + p[0]] = 'Use a full path starting with a drive letter, without quotes or these characters: < > : | ? * $ ; % & ^ [ ] { }';
    });
    if (!RE_TASK.test(rd.taskName)) e['recordDots.taskName'] = 'Use letters, numbers, spaces, dots, dashes and underscores only.';
    if (!RE_REF.test(rd.scriptsRef)) e['recordDots.scriptsRef'] = 'Use a branch or release name such as main.';
    var iv = Number(rd.intervalMinutes);
    if (!(iv >= 15 && iv <= 1440 && Math.floor(iv) === iv)) e['recordDots.intervalMinutes'] = 'Choose how often to refresh.';

    var ic = rd.icons;
    if (!RE_HEX.test(ic.ring.color)) e['recordDots.icons.ring'] = 'Ring color must look like #e2e2e2.';
    LIB.TYPES.forEach(function (t) {
      var d = ic[t.key];
      if (!RE_HEX.test(d.color)) e['recordDots.icons.' + t.key] = 'Color must look like #e30404.';
      else if (LIB.SHAPES.indexOf(d.shape) < 0) e['recordDots.icons.' + t.key] = 'Pick a shape from the list.';
    });
    return e;
  };

  /* ---------- config.json ---------- */
  LIB.buildConfig = function (s) {
    var rd = s.recordDots, ic = rd.icons, icons = { ring: { enabled: !!ic.ring.enabled, color: ic.ring.color.toLowerCase() } };
    LIB.TYPES.forEach(function (t) { icons[t.key] = { shape: ic[t.key].shape, color: ic[t.key].color.toLowerCase() }; });
    return {
      schemaVersion: 1,
      station: { name: s.station.name.trim(), contactEmail: s.station.contactEmail.trim(), maxMachine: s.station.maxMachine.trim() },
      recordDots: {
        intervalMinutes: Number(rd.intervalMinutes),
        installDir: LIB.normalizePath(rd.installDir),
        kmlFolder: LIB.normalizePath(rd.kmlFolder),
        navDataFolder: LIB.normalizePath(rd.navDataFolder),
        taskName: rd.taskName.trim(),
        scriptsRef: rd.scriptsRef.trim(),
        icons: icons
      }
    };
  };

  /* Tolerant loader for a previously downloaded config.json. Unknown or bad fields keep the defaults. */
  LIB.fromConfig = function (obj) {
    var s = LIB.defaults();
    if (!obj || typeof obj !== 'object') return s;
    var pickStr = function (v, d) { return typeof v === 'string' ? v : d; };
    if (obj.station) {
      s.station.name = pickStr(obj.station.name, s.station.name);
      s.station.contactEmail = pickStr(obj.station.contactEmail, s.station.contactEmail);
      s.station.maxMachine = pickStr(obj.station.maxMachine, s.station.maxMachine);
    }
    var rd = obj.recordDots;
    if (rd && typeof rd === 'object') {
      if (typeof rd.intervalMinutes === 'number') s.recordDots.intervalMinutes = rd.intervalMinutes;
      ['installDir', 'kmlFolder', 'navDataFolder', 'taskName', 'scriptsRef'].forEach(function (k) {
        s.recordDots[k] = pickStr(rd[k], s.recordDots[k]);
      });
      if (rd.icons && typeof rd.icons === 'object') {
        var ic = rd.icons;
        if (ic.ring && typeof ic.ring === 'object') {
          if (typeof ic.ring.enabled === 'boolean') s.recordDots.icons.ring.enabled = ic.ring.enabled;
          if (typeof ic.ring.color === 'string') s.recordDots.icons.ring.color = ic.ring.color;
        }
        LIB.TYPES.forEach(function (t) {
          var d = ic[t.key];
          if (d && typeof d === 'object') {
            if (typeof d.shape === 'string') s.recordDots.icons[t.key].shape = d.shape;
            if (typeof d.color === 'string') s.recordDots.icons[t.key].color = d.color;
          }
        });
      }
    }
    return s;
  };

  /* ---------- names ---------- */
  LIB.kmzNames = function () {
    var out = [];
    for (var d = 1; d <= LIB.DAYS; d++) LIB.TYPES.forEach(function (t) { out.push('D' + d + '_' + t.key.toUpperCase() + '.kmz'); });
    return out;
  };
  LIB.slug = function (name) {
    var x = String(name || '').trim().replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    return x || 'station';
  };

  /* ---------- SETUP.txt ---------- */
  LIB.shareBase = function (s) {
    var kml = LIB.normalizePath(s.recordDots.kmlFolder);
    var root = 'D:\\WSI\\DigitalMedia\\';
    if (kml.toLowerCase().indexOf(root.toLowerCase()) === 0) {
      var m = s.station.maxMachine.trim() || '<NAME-OF-THIS-PC>';
      return '\\\\' + m + '\\DigitalMedia\\' + kml.slice(root.length);
    }
    return null;
  };

  LIB.setupText = function (s) {
    var cfg = LIB.buildConfig(s), rd = cfg.recordDots, L = [];
    var base = LIB.shareBase(s);
    var P = function (x) { L.push(x === undefined ? '' : x); };
    P('RECORD DOTS SETUP FOR ' + cfg.station.name.toUpperCase());
    P('Made with the Max tools configurator.');
    P();
    P('WHAT YOU NEED');
    P('  - The PC that runs the record-dots scripts (it needs internet access).');
    P('  - A Windows account with administrator rights on that PC.');
    P();
    P('1. INSTALL (about 5 minutes)');
    P('  a. Right-click the zip file > Properties > tick Unblock > OK. Then right-click it > Extract All.');
    P('     (Skipping the unblock step only means Windows may show an extra warning.)');
    P('  b. Open the extracted folder and double-click Install.bat.');
    P('     If Windows says "Windows protected your PC", click More info, then Run anyway.');
    P('  c. Click Yes on the administrator prompt.');
    P('  d. Wait for the test run to finish. It ends with a summary and "Press Enter to close".');
    P();
    P('The installer does this, and nothing else:');
    P('  - Creates ' + rd.installDir + ', ' + rd.kmlFolder + ' and ' + rd.navDataFolder + ' if they are missing.');
    P('  - Downloads FetchDailyRecords.ps1, station_manager.ps1 and (if you do not have one yet) stations.csv');
    P('    from github.com/justingehrts/daily-record-dots (' + rd.scriptsRef + ') into ' + rd.installDir + '.');
    P('  - Copies your config.json and your four dot icons next to the script.');
    P('  - Creates a scheduled task named "' + rd.taskName + '" that runs every ' + rd.intervalMinutes + ' minutes,');
    P('    whether or not anyone is logged on, under the account that ran the installer.');
    P('  - Runs the task once and reports how many of the 28 KMZ files it wrote.');
    P('Run Install.bat again at any time to update the scripts or apply new settings.');
    P();
    P('2. CONNECT MAX');
    P('The script writes 28 KMZ files, one for each of 7 forecast days and 4 record types:');
    P('  D1_HIMAX.kmz  D1_LOMAX.kmz  D1_HIMIN.kmz  D1_LOMIN.kmz  ...  D7_HIMAX.kmz ... D7_LOMIN.kmz');
    P('Their names never change, so you enter each address in Max once.');
    if (base) {
      P('If D:\\WSI\\DigitalMedia is shared as "DigitalMedia" (the usual Max setup), the on-air Max PC reaches them at:');
      P('  ' + base + '\\D1_HIMAX.kmz');
      P('  ' + base + '\\D2_HIMIN.kmz');
      if (!s.station.maxMachine.trim()) P('(Replace <NAME-OF-THIS-PC> with the Windows name of the PC you installed on.)');
      P('The on-air Max PC\'s account needs read access to that share.');
    } else {
      P('The files are written to ' + rd.kmlFolder + '. The on-air Max PC needs a network path to that folder.');
    }
    P('A copy of each day/type list is also saved as a CSV in ' + rd.navDataFolder + ' for Max.');
    P();
    P('3. AFTER NEW DATA ARRIVES (manual step in Max)');
    P('The files update by themselves, but the scene in Max does not pick up new stations on its own:');
    P('  a. Select the layer for the day and record type you want to update.');
    P('  b. In Properties > Plot Locations, click the edit pencil.');
    P('  c. Select all locations on the right-hand side and click the left arrow to remove them.');
    P('  d. Select all locations on the left-hand side and click the right arrow.');
    P('  e. Click OK.');
    P();
    P('4. CHECKING THAT IT WORKS');
    P('  - Open ' + rd.installDir + '\\run_log.txt. The last line says how many KMZ files were written.');
    P('  - "DOWNLOAD FAILED" lines mean this PC could not reach www.wpc.ncep.noaa.gov.');
    P('  - Open Task Scheduler and look for "' + rd.taskName + '" to see the last run time and result.');
    P('  - If stations are missing from the map, see missing_log.txt and run station_manager.ps1 in ' + rd.installDir + '.');
    P();
    P('5. REMOVING IT');
    P('Double-click Uninstall.bat. It removes the scheduled task and asks before deleting the script folder.');
    P('It never deletes the KMZ or CSV files that Max reads.');
    P();
    P('NOTES');
    P('  - Requests to the National Weather Service identify your station and ' + cfg.station.contactEmail + '.');
    P('  - If the installer says it cannot create the task, the account may lack the "log on as a batch job" right.');
    P('    Ask your IT group, or run the installer from another administrator account.');
    return L.join('\n') + '\n';
  };

  /* ---------- icons ---------- */
  var RING_R = 59, CENTER_RATIO = 40.8 / 59, NO_RING_RATIO = 0.86;

  function shapePath(ctx, shape, cx, cy, R) {
    ctx.beginPath();
    if (shape === 'square') {
      var h = R * 0.86;
      ctx.rect(cx - h, cy - h, 2 * h, 2 * h);
    } else if (shape === 'diamond') {
      ctx.moveTo(cx, cy - R); ctx.lineTo(cx + R, cy); ctx.lineTo(cx, cy + R); ctx.lineTo(cx - R, cy); ctx.closePath();
    } else if (shape === 'triangle') {
      for (var i = 0; i < 3; i++) {
        var t = -Math.PI / 2 + i * 2 * Math.PI / 3;
        var x = cx + R * Math.cos(t), y = cy + R * Math.sin(t);
        if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
      }
      ctx.closePath();
    } else {
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
    }
  }

  LIB.drawIcon = function (ctx, size, spec, ring) {
    var k = size / 128;
    ctx.save();
    ctx.clearRect(0, 0, size, size);
    ctx.scale(k, k);
    if (ring.enabled) {
      shapePath(ctx, spec.shape, 64, 64, RING_R);
      ctx.fillStyle = ring.color; ctx.fill();
      shapePath(ctx, spec.shape, 64, 64, RING_R * CENTER_RATIO);
      ctx.fillStyle = spec.color; ctx.fill();
    } else {
      shapePath(ctx, spec.shape, 64, 64, RING_R * NO_RING_RATIO);
      ctx.fillStyle = spec.color; ctx.fill();
      ctx.lineWidth = 5; ctx.lineJoin = 'round'; ctx.strokeStyle = 'rgba(0,0,0,0.45)'; ctx.stroke();
    }
    ctx.restore();
  };

  /* ---------- zip (store only; every file here is small or already compressed) ---------- */
  var crcTable = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(buf) {
    var c = 0xFFFFFFFF;
    for (var i = 0; i < buf.length; i++) c = crcTable[(c ^ buf[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  /* files: [{ name: 'icons/a.png', data: Uint8Array }]; returns a Uint8Array */
  LIB.makeZip = function (files, when) {
    var enc = new TextEncoder(), d = when || new Date();
    var dosTime = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
    var dosDate = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    var parts = [], central = [], offset = 0;
    files.forEach(function (f) {
      var name = enc.encode(f.name), crc = crc32(f.data), size = f.data.length;
      var lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true);
      lh.setUint16(10, dosTime, true); lh.setUint16(12, dosDate, true); lh.setUint32(14, crc, true);
      lh.setUint32(18, size, true); lh.setUint32(22, size, true); lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
      parts.push(new Uint8Array(lh.buffer), name, f.data);
      var ch = new DataView(new ArrayBuffer(46));
      ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true);
      ch.setUint16(10, 0, true); ch.setUint16(12, dosTime, true); ch.setUint16(14, dosDate, true); ch.setUint32(16, crc, true);
      ch.setUint32(20, size, true); ch.setUint32(24, size, true); ch.setUint16(28, name.length, true);
      ch.setUint32(42, offset, true);
      central.push(new Uint8Array(ch.buffer), name);
      offset += 30 + name.length + size;
    });
    var cdSize = central.reduce(function (a, p) { return a + p.length; }, 0);
    var end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
    var all = parts.concat(central, [new Uint8Array(end.buffer)]);
    var total = all.reduce(function (a, p) { return a + p.length; }, 0), out = new Uint8Array(total), pos = 0;
    all.forEach(function (p) { out.set(p, pos); pos += p.length; });
    return out;
  };

  /* Text helpers for Windows: CRLF line endings, optional UTF-8 BOM (scripts), returned as bytes. */
  LIB.textBytes = function (text, bom) {
    var body = new TextEncoder().encode(String(text).replace(/\r?\n/g, '\r\n'));
    if (!bom) return body;
    var out = new Uint8Array(body.length + 3);
    out.set([0xEF, 0xBB, 0xBF], 0); out.set(body, 3);
    return out;
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = LIB; else root.LIB = LIB;
})(typeof window !== 'undefined' ? window : this);
