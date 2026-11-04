#!/usr/bin/env python3
"""Check FFG color ramps (7 colors, most dangerous band first) against the guidance in Rosen et al. 2026
(J. Operational Meteor. 14(13), doi:10.15191/nwajom.2026.1413) and the usual colormap literature:

  * lightness (CIELAB L*) changes in one direction across the bands (perceptual order),
  * neighbouring bands stay distinguishable for normal vision and for protan/deutan/tritan color vision deficiency
    (Machado et al. 2009 simulation, full severity), measured as CIEDE2000 between neighbours.

    python tools/check_ramps.py                 # the presets in configurator/src/lib.js
    python tools/check_ramps.py '#67000d,...'   # any ramp
"""
import json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_DE = 8.0          # smallest acceptable CIEDE2000 between neighbouring bands (about "clearly different" on a map)

MACHADO = {           # linear-RGB matrices, severity 1.0
    'protan': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    'deutan': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    'tritan': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def rgb(h): return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def lab(linrgb):
    r, g, b = [min(1, max(0, x)) for x in linrgb]
    X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    return 116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))


def de2000(a, b):
    L1, a1, b1 = a; L2, a2, b2 = b
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1 = math.degrees(math.atan2(b1, a1p)) % 360; h2 = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2 - h1 if abs(h2 - h1) <= 180 else h2 - h1 - 360 if h2 > h1 else h2 - h1 + 360)
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hb = h1 + h2 if C1p * C2p == 0 else ((h1 + h2) / 2 if abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2)
    T = 1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb)) + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63))
    SL = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2); SC = 1 + 0.045 * Cbp; SH = 1 + 0.015 * Cbp * T
    RT = -2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2)))
    return math.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))


def check(colors):
    lins = [[lin(c) for c in rgb(h)] for h in colors]
    views = {'normal': lins}
    for k, M in MACHADO.items():
        views[k] = [[sum(M[i][j] * v[j] for j in range(3)) for i in range(3)] for v in lins]
    L = [lab(v)[0] for v in lins]
    d = [L[i + 1] - L[i] for i in range(len(L) - 1)]
    monotonic = all(x > 0 for x in d) or all(x < 0 for x in d)
    mins = {k: min(de2000(lab(v[i]), lab(v[i + 1])) for i in range(len(v) - 1)) for k, v in views.items()}
    worst = min(mins, key=mins.get)
    return {'L': [round(x) for x in L], 'monotonic': monotonic, 'minDE': {k: round(v, 1) for k, v in mins.items()},
            'ok': monotonic and mins[worst] >= MIN_DE}


def presets():
    js = (ROOT / 'configurator' / 'src' / 'lib.js').read_text()
    m = re.search(r'/\*PRESETS\*/(.*?)/\*END PRESETS\*/', js, re.S)
    return json.loads(m.group(1))


if __name__ == '__main__':
    items = [{'name': 'given', 'colors': [c.strip() for c in sys.argv[1].split(',')]}] if len(sys.argv) > 1 else presets()
    bad = 0
    for p in items:
        r = check(p['colors'])
        bad += not r['ok'] and not p.get('legacy')
        print(f"{'OK  ' if r['ok'] else 'legacy' if p.get('legacy') else 'FAIL'} {p['name']:<28} L*={r['L']} monotonic={r['monotonic']} min dE: {r['minDE']}")
    sys.exit(1 if bad else 0)
