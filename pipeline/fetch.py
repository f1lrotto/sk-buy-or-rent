"""Fetch every automated source into raw/<YYYY-MM-DD>/. Standard library only.

    python3 -I pipeline/fetch.py [raw_dir]

Raw copies are kept so a broken parser can be fixed and build.py re-run without
fetching again. Realitymap town pages are ~300 KB each, so only their embedded monthly
series is stored (raw/<date>/realitymap_towns.jsonl); the two kraj pages are kept whole.
Deloitte Rent Index and bank rates are entered by hand in pipeline/manual/.
"""
import datetime as dt
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from places import OKRES_TOWNS, slug  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UA = "kupit-ci-prenajat data bot (+https://github.com/f1lrotto/sk-buy-or-rent)"
STATDATA = "https://statdata.statistics.sk/public/api/dc/opendata/cube/dataset/{}/download?lang=SK&type=CSV"
ECB = "https://data-api.ecb.europa.eu/service/data/MIR/M.SK.B.A2C.{}.R.A.2250.EUR.N?format=csvdata"
SIMPLE = {
    "statdata_np3112qr.zip": STATDATA.format("np3112qr"),  # average wage by kraj, quarterly
    "statdata_sp3801qr.zip": STATDATA.format("sp3801qr"),  # transaction price index by kraj
    "eurostat_cp041.json": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr"
                           "?geo=SK&coicop18=CP041&unit=I25&format=JSON",
    "realitymap_predaj.html": "https://realitymap.sk/ceny/predaj/byty",
    "realitymap_prenajom.html": "https://realitymap.sk/ceny/prenajom/byty",
    "realitnaunia_barometer.html": "https://www.realitnaunia.sk/realitny-barometer",
    "deloitte_rent_index.html": "https://www.deloitte.com/cz-sk/sk/Industries/real-estate/collections/rent-index.html",
    # ECB MIR housing loan rates for Slovakia, new business: total and by initial rate fixation
    **{f"ecb_mir_{f}.csv": ECB.format(f) for f in ("A", "F", "I", "O", "P")},
}


def get(url, data=None, headers=None, tries=3, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:  # ECB sometimes hangs for 30 s; retry with backoff
            if i == tries - 1:
                raise
            print(f"  retry {url}: {e!r}", file=sys.stderr)
            time.sleep(5 * (i + 1))


def realitymap_series(html):
    """The monthly series that realitymap embeds in its Next.js payload."""
    i = html.find('\\"series\\":[')
    if i < 0:
        return None
    chunk = html[i + len('\\"series\\":'): i + 200000].replace('\\"', '"')
    return json.JSONDecoder().raw_decode(chunk)[0]


def town_slugs():
    """Okres towns plus the Bratislava and Košice districts realitymap has rent and sale pages for."""
    xml = get("https://realitymap.sk/sitemap/0.xml").decode()
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    have = {deal: {u.rsplit("/", 1)[1] for u in urls if f"/ceny/{deal}/byty/" in u} for deal in ("predaj", "prenajom")}
    both = have["predaj"] & have["prenajom"]
    wanted = [slug(t) for t in OKRES_TOWNS] + sorted(s for s in both if s.startswith(("bratislava-", "kosice-")))
    return [s for s in dict.fromkeys(wanted) if s in both]


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "raw") / dt.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for name, url in SIMPLE.items():
        try:
            (out / name).write_bytes(get(url))
            print("ok", name)
        except Exception as e:
            failed.append(name)
            print("FAILED", name, repr(e), file=sys.stderr)
    try:
        body = get("https://nbs.sk/elastic/real_estate_price_by_region/_search", data=b'{"size":200}',
                   headers={"Content-Type": "application/json"})
        (out / "nbs_region.json").write_bytes(body)
        print("ok nbs_region.json")
    except Exception as e:
        failed.append("nbs_region.json")
        print("FAILED nbs", repr(e), file=sys.stderr)

    with open(out / "realitymap_towns.jsonl", "w") as f:
        for s in town_slugs():
            for deal in ("predaj", "prenajom"):
                url = f"https://realitymap.sk/ceny/{deal}/byty/{s}"
                rec = {"slug": s, "deal": deal, "url": url}
                try:
                    rec["series"] = realitymap_series(get(url).decode("utf-8", "replace"))
                except Exception as e:
                    rec["error"] = repr(e)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                time.sleep(1.2)  # be polite: one request at a time
    print("ok realitymap_towns.jsonl")
    json.dump({"fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "failed": failed},
              open(out / "fetch.json", "w"))
    print("failed:", failed or "none")


if __name__ == "__main__":
    main()
