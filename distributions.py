"""Collect distribution records for a scientific name across ChecklistBank datasets.

Same logic as index.html, using only the Python standard library:
  python3 distributions.py "Pterois miles" [--griis] > distributions.json
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

API = "https://api.checklistbank.org"
GRIIS_PUBLISHER = "cdef28b1-db4e-4c58-aa71-3c5238c2d0b5"  # ISSG
ACCEPTED = {"accepted", "provisionally accepted"}


def get(path, **params):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def main(name, griis=False):
    # 1. every usage of the name in any dataset (cross dataset search)
    query = dict(q=name, content="SCIENTIFIC_NAME", type="EXACT", limit=1000)
    if griis:
        query["publisherKey"] = GRIIS_PUBLISHER
    usages, offset = [], 0
    while True:
        res = get("/nameusage/search", offset=offset, **query)
        page = [r["usage"] for r in res.get("result", [])]
        usages += page
        offset += len(page)
        if not page or offset >= res["total"]:
            break

    # 2. dataset filter: external datasets + newest release per project
    meta = {k: get(f"/dataset/{k}/simple") for k in {u["datasetKey"] for u in usages}}
    keep, releases = set(), defaultdict(list)
    for k, m in meta.items():
        if m["origin"] in ("release", "xrelease"):
            releases[m.get("sourceKey")].append(m)
        elif m["origin"] != "project" and not re.fullmatch(r"COL\d\d", m.get("alias") or ""):
            keep.add(k)  # external, minus the legacy COL Annual Checklists
    for rels in releases.values():
        xr = [m for m in rels if m["origin"] == "xrelease"] or rels
        keep.add(max(m["key"] for m in xr))

    # 3. distributions of the accepted taxon behind each usage
    records, seen = [], set()
    for u in usages:
        dk = u["datasetKey"]
        tid = u["id"] if u["status"] in ACCEPTED else (u.get("accepted") or {}).get("id")
        if dk not in keep or not tid or (dk, tid) in seen:
            continue
        seen.add((dk, tid))
        for d in get(f"/dataset/{dk}/taxon/{urllib.parse.quote(tid, safe='')}/distribution"):
            d.update(datasetKey=dk, datasetAlias=meta[dk].get("alias"), taxonId=tid)
            records.append(d)

    # keep datasets with at least one area that is not free text
    mapped_ds = {d["datasetKey"] for d in records if d["area"].get("gazetteer") not in (None, "text")}
    records = [d for d in records if d["datasetKey"] in mapped_ds or d["area"].get("gazetteer") == "text"]

    # 4. one GeoJSON shape per distinct area (404 = no shape for that area)
    areas = sorted({d["area"]["globalId"] for d in records if d["area"].get("gazetteer") not in (None, "text")})
    shapes = {}
    for gid in areas:
        try:
            shapes[gid] = get(f"/vocab/area/{urllib.parse.quote(gid, safe=':')}.geojson")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    print(f"{len(meta)} datasets, {len(keep)} kept, {len(mapped_ds)} with mapped areas, "
          f"{len(areas)} areas ({len(shapes)} with shapes), {len(records)} records", file=sys.stderr)
    features = [dict(s, properties={**s.get("properties", {}), "globalId": gid}) for gid, s in shapes.items()]
    return {"query": name, "records": records,
            "areas": {"type": "FeatureCollection", "features": features}}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    json.dump(main(args[0] if args else "Pterois miles", "--griis" in sys.argv), sys.stdout)
