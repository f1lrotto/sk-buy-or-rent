# Kúpiť či prenajať

Rent-or-buy and mortgage calculator for Slovak kraje, okres towns and Bratislava/Košice districts. Static SvelteKit site; all maths runs in the browser from JSON files refreshed monthly.

## Layout

- `pipeline/fetch.py` – downloads every automated source into `raw/<date>/` (standard library only).
- `pipeline/build.py` – parses and validates the newest raw folder, writes `site/static/data/*.json`. A source that fails keeps its last good values from `pipeline/state/sources.json` and is flagged as stale on the site.
- `pipeline/manual/` – hand-kept inputs: Deloitte Rent Index (quarterly, from the PDF), bank offers (monthly), legal rules (review every January).
- `pipeline/make_areas.py` – one-time map shapes from GKÚ boundaries (`uv run pipeline/make_areas.py USJ_hranice_3.gpkg`).
- `site/` – SvelteKit 3 app. `src/lib/calc.ts` holds the calculator, with tests in `calc.test.ts`.

## Run locally

```sh
python3 -I pipeline/fetch.py && python3 -I pipeline/build.py
cd site && pnpm install && pnpm test && pnpm build && pnpm preview
```

## Deploy (Cloudflare Workers)

`wrangler.jsonc` serves `site/build` as static assets from the `sk-buy-or-rent` worker. In the worker's Settings → Build, connect this GitHub repo with:

- Build command: `cd site && pnpm install && pnpm build`
- Deploy command: `npx wrangler deploy`
- Root directory: `/`

The `Monthly data refresh` workflow commits new data on the 15th, which triggers a deploy.

## Monthly manual steps

1. Bank offers: update `pipeline/manual/banks.json` (rows older than 45 days show greyed out).
2. Each quarter: add the new Deloitte period to `pipeline/manual/deloitte.json` (the build warns when a newer PDF is out).
