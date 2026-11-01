#!/usr/bin/env python3
"""One-off: build markets.json (draft boxes) from the TEGNA market list + Nielsen DMA outlines.

Usage: python3 reference/make_markets.py > markets.json     (prints a size report to stderr)
Boxes are DRAFTS for the contact-sheet review (work order step 4). Once Justin signs off, markets.json is
hand-edited and this script is not run again.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import dmabox

# (id, display name, [TV call signs], Nielsen DMA name in the dataset | (lat, lon) for a hand-sized box)
M = [
 ('huntsville-al', 'Huntsville, AL', ['WZDX'], 'Huntsville-Decatur (Florence), AL'),
 ('flagstaff-az', 'Flagstaff, AZ', ['KNAZ-TV'], (35.2, -111.65)),
 ('phoenix-az', 'Phoenix, AZ', ['KPNX'], 'Phoenix, AZ'),
 ('tucson-az', 'Tucson, AZ', ['KMSB', 'KTTU'], 'Tucson (Sierra Vista), AZ'),
 ('fort-smith-fayetteville-ar', 'Fort Smith–Fayetteville, AR', ['KFSM-TV'], 'Ft. Smith-Fayetteville-Springdale-Rogers, AR'),
 ('little-rock-ar', 'Little Rock, AR', ['KTHV'], 'Little Rock-Pine Bluff, AR'),
 ('sacramento-ca', 'Sacramento, CA', ['KXTV'], 'Sacramento-Stockton-Modesto, CA'),
 ('san-diego-ca', 'San Diego, CA', ['KFMB-TV'], 'San Diego, CA'),
 ('denver-co', 'Denver, CO', ['KUSA', 'KTVD'], 'Denver, CO'),
 ('hartford-new-haven-ct', 'Hartford–New Haven, CT', ['WTIC-TV', 'WCCT-TV'], 'Hartford & New Haven, CT'),
 ('washington-dc', 'Washington, DC', ['WUSA'], 'Washington, DC (Hagerstown, MD)'),
 ('jacksonville-fl', 'Jacksonville, FL', ['WJXX', 'WTLV'], 'Jacksonville, FL'),
 ('tampa-fl', 'Tampa–St. Petersburg, FL', ['WTSP'], 'Tampa-St. Petersburg (Sarasota), FL'),
 ('atlanta-ga', 'Atlanta, GA', ['WXIA-TV', 'WATL'], 'Atlanta, GA'),
 ('macon-ga', 'Macon, GA', ['WMAZ-TV'], 'Macon, GA'),
 ('boise-id', 'Boise, ID', ['KTVB'], 'Boise, ID'),
 ('twin-falls-id', 'Twin Falls, ID', ['KTFT-LD'], 'Twin Falls, ID'),
 ('indianapolis-in', 'Indianapolis, IN', ['WTHR', 'WALV-CD'], 'Indianapolis, IN'),
 ('davenport-ia', 'Davenport (Quad Cities), IA', ['WQAD-TV'], 'Davenport, IA-Rock Island-Moline, IL'),
 ('des-moines-ia', 'Des Moines, IA', ['WOI-DT', 'KCWI-TV'], 'Des Moines-Ames, IA'),
 ('louisville-ky', 'Louisville, KY', ['WHAS-TV'], 'Louisville, KY'),
 ('new-orleans-la', 'New Orleans, LA', ['WWL-TV', 'WUPL'], 'New Orleans, LA'),
 ('portland-me', 'Portland, ME', ['WCSH'], 'Portland-Auburn, ME'),
 ('bangor-me', 'Bangor, ME', ['WLBZ'], 'Bangor, ME'),
 ('grand-rapids-mi', 'Grand Rapids, MI', ['WZZM'], 'Grand Rapids-Kalamazoo-Battle Creek, MI'),
 ('minneapolis-mn', 'Minneapolis–Saint Paul, MN', ['KARE'], 'Minneapolis-St. Paul, MN'),
 ('st-louis-mo', 'St. Louis, MO', ['KSDK'], 'St. Louis, MO'),
 ('buffalo-ny', 'Buffalo, NY', ['WGRZ'], 'Buffalo, NY'),
 ('charlotte-nc', 'Charlotte, NC', ['WCNC-TV'], 'Charlotte, NC'),
 ('greensboro-nc', 'Greensboro, NC', ['WFMY-TV'], 'Greensboro-High Point-Winston Salem, NC'),
 ('cleveland-oh', 'Cleveland, OH', ['WKYC'], 'Cleveland-Akron (Canton), OH'),
 ('columbus-oh', 'Columbus, OH', ['WBNS-TV'], 'Columbus, OH'),
 ('toledo-oh', 'Toledo, OH', ['WTOL', 'WUPW'], 'Toledo, OH'),
 ('portland-or', 'Portland, OR', ['KGW'], 'Portland, OR'),
 ('scranton-wilkes-barre-pa', 'Scranton–Wilkes-Barre, PA', ['WNEP-TV'], 'Wilkes Barre-Scranton, PA'),
 ('harrisburg-pa', 'Harrisburg, PA', ['WPMT'], 'Harrisburg-Lancaster-Lebanon-York, PA'),
 ('columbia-sc', 'Columbia, SC', ['WLTX'], 'Columbia, SC'),
 ('knoxville-tn', 'Knoxville, TN', ['WBIR-TV'], 'Knoxville, TN'),
 ('memphis-tn', 'Memphis, TN', ['WATN-TV', 'WLMT'], 'Memphis, TN'),
 ('abilene-tx', 'Abilene, TX', ['KXVA'], 'Abilene-Sweetwater, TX'),
 ('austin-tx', 'Austin, TX', ['KVUE'], 'Austin, TX'),
 ('beaumont-tx', 'Beaumont, TX', ['KBMT'], 'Beaumont-Port Arthur, TX'),
 ('bryan-college-station-tx', 'Bryan–College Station, TX', ['KAGS-LD'], (30.65, -96.35)),
 ('corpus-christi-tx', 'Corpus Christi, TX', ['KIII'], 'Corpus Christi, TX'),
 ('dallas-fort-worth-tx', 'Dallas–Fort Worth, TX', ['WFAA', 'KFAA-TV'], 'Dallas-Ft. Worth, TX'),
 ('houston-tx', 'Houston, TX', ['KHOU', 'KTBU'], 'Houston, TX'),
 ('odessa-midland-tx', 'Odessa–Midland, TX', ['KWES-TV'], 'Odessa-Midland, TX'),
 ('san-angelo-tx', 'San Angelo, TX', ['KIDY'], 'San Angelo, TX'),
 ('san-antonio-tx', 'San Antonio, TX', ['KENS'], 'San Antonio, TX'),
 ('tyler-tx', 'Tyler, TX', ['KYTX'], 'Tyler-Longview(Lufkin & Nacogdoches), TX'),
 ('waco-tx', 'Waco, TX', ['KCEN-TV'], 'Waco-Temple-Bryan, TX'),
 ('norfolk-va', 'Norfolk, VA', ['WVEC'], 'Norfolk-Portsmouth-Newport News, VA'),
 ('seattle-wa', 'Seattle–Tacoma, WA', ['KING-TV', 'KONG'], 'Seattle-Tacoma, WA'),
 ('spokane-wa', 'Spokane, WA', ['KREM', 'KSKN'], 'Spokane, WA'),
]

dmas = dmabox.load()
out, big = [], []
for mid, name, calls, src in M:
    if isinstance(src, tuple):
        lat, lon = src
        ext, note = (lon - 0.9, lat - 0.75, lon + 0.9, lat + 0.75), 'hand-sized (no DMA outline)'
    else:
        ext, dropped = dmabox.main_extent(dmas[src]); note = f'{len(dropped)} stray piece(s) dropped'
    b = dmabox.box169(ext)
    out.append({'id': mid, 'name': name, 'stations': calls, 'bounds': list(b)})
    w, h = b[2] - b[0], b[3] - b[1]
    print(f'{mid:30s} {w:5.1f} x {h:4.1f} deg  {note}', file=sys.stderr)
json.dump({'schemaVersion': 1, 'markets': out}, sys.stdout, indent=1, ensure_ascii=False)
print()
