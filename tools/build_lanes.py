#!/usr/bin/env python3
"""Turn an osmium GeoJSON-seq export into small per-area lane files for LaneTrack.

Usage: build_lanes.py lanes.geojsonseq out_dir

Writes out_dir/<la>_<lo>.json (one per 0.25 degree cell) and out_dir/index.json.
Each cell file is a JSON list of [osm_id, tags, [[lat, lon], ...]].
"""
import json, math, os, re, sys, time

CELL = 0.25
DES = re.compile(r'^(byway_open_to_all_traffic|restricted_byway|unclassified_county_road|'
                 r'unclassified_country_road|unclassified_highway|unclassified_road|byway|public_byway)$')
REF = re.compile(r'(^|[ ;])(BY|BOAT)[ .0-9]')
NAME = re.compile(r'\((BY|BOAT) ?[0-9]')
KEEP = ('name', 'prow_ref', 'ref', 'designation', 'highway', 'surface', 'tracktype', 'motor_vehicle',
        'vehicle', 'motorcycle', 'motor_vehicle:conditional', 'motorcycle:conditional',
        'vehicle:conditional', 'access', 'note')


def wanted(t):
    if not t.get('highway'):
        return False
    return bool(DES.match(t.get('designation', '')) or t.get('highway') == 'byway'
                or REF.search(t.get('prow_ref', '')) or REF.search(t.get('ref', ''))
                or NAME.search(t.get('name', '')))


def main(src, out):
    os.makedirs(out, exist_ok=True)
    cells = {}
    n = 0
    with open(src, encoding='utf-8') as f:
        for line in f:
            line = line.strip().lstrip('\x1e')
            if not line:
                continue
            feat = json.loads(line)
            g = feat.get('geometry') or {}
            if g.get('type') != 'LineString':
                continue
            props = feat.get('properties') or {}
            if not wanted(props):
                continue
            oid = props.get('@id')
            tags = {k: props[k] for k in KEEP if k in props}
            pts = [[round(c[1], 5), round(c[0], 5)] for c in g['coordinates']]
            lats = [p[0] for p in pts]
            lons = [p[1] for p in pts]
            rec = [oid, tags, pts]
            for la in range(math.floor(min(lats) / CELL), math.floor(max(lats) / CELL) + 1):
                for lo in range(math.floor(min(lons) / CELL), math.floor(max(lons) / CELL) + 1):
                    cells.setdefault(f'{la}_{lo}', []).append(rec)
            n += 1
    for name in os.listdir(out):
        if name.endswith('.json'):
            os.remove(os.path.join(out, name))
    for key, recs in cells.items():
        with open(os.path.join(out, key + '.json'), 'w', encoding='utf-8') as f:
            json.dump(recs, f, separators=(',', ':'), ensure_ascii=False)
    with open(os.path.join(out, 'index.json'), 'w') as f:
        json.dump({'cell': CELL, 'built': time.strftime('%Y-%m-%d'), 'ways': n, 'cells': sorted(cells)}, f)
    print(f'{n} lanes in {len(cells)} cells')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
