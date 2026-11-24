# Species Distributions

A single static page that collects distribution records for a scientific name across all
[ChecklistBank](https://www.checklistbank.org) datasets and shows them on one map.

Live: https://mdoering.github.io/clb-distributions/?q=Pterois%20miles

## What it does

1. Runs the cross-dataset name search (`/nameusage/search?q=…&type=EXACT&content=SCIENTIFIC_NAME`).
2. Looks up each dataset with `/dataset/{key}/simple` and keeps:
   - external datasets, except the legacy COL Annual Checklists 2000–2019 (alias `COLnn`);
   - for each project, the single newest release among the search hits (highest key), preferring XReleases. For COL this is the newest COL XRelease.

   Projects and the other releases are left out.
3. Fetches `/dataset/{key}/taxon/{id}/distribution` for each hit, using the accepted taxon for synonyms. It keeps the datasets that have at least one distribution with a gazetteer area, i.e. not plain text.
4. Draws every area on one MapLibre map, using the API's `/vocab/area/{gazetteer}:{id}.geojson` shapes, coloured by establishment means. Below the map:
   - a table of all areas;
   - a collapsible list of the text-only distributions;
   - the matching datasets with links to ChecklistBank.

**Download JSON** exports every aggregated distribution record, with dataset and usage details added.

A **GBIF occurrences** layer shows GBIF's hexagon density tiles on the same map, as on catalogueoflife.org. GBIF is queried through its Catalogue of Life checklist `7ddf754f-d193-4cc9-b351-99906754a03b`, using the COL taxon id from the newest COL XRelease (`/dataset/3LXR/nameusage/search`). The checkbox next to Download JSON switches it on and off.

The page has a collapsible section, **How to get the distribution data from the API yourself**, with a `curl` example for every call it makes.

## Python

`distributions.py` does the same with the Python standard library only. It prints a summary to stderr and writes the records plus a GeoJSON FeatureCollection of the areas:

```
python3 distributions.py "Pterois miles" [--griis] > distributions.json
```

## Parameters

- `q`: the scientific name.
- `griis=1`: limits the search to the GRIIS checklists, using `publisherKey=cdef28b1-db4e-4c58-aa71-3c5238c2d0b5` (ISSG). The page has a "GRIIS only" switch for this.
- `api`: the API base URL, default `https://api.checklistbank.org`. For example `?api=https://api.test.checklistbank.org`; links then point to the matching ChecklistBank UI.

## Run locally

```
python3 -m http.server 8765
open "http://localhost:8765/?q=Pterois%20miles"
```

There's no build step. The page works on any static host because the ChecklistBank API sends CORS headers.
