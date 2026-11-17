"""Parse the newest raw/<date>/ folder, validate it and write the site's data files.

    python3 -I pipeline/build.py [raw_dir]

Writes site/static/data/{latest,history,rates,rules}.json and pipeline/state/sources.json.
Each source is parsed on its own. When a source fails to parse or fails validation, the
build keeps that source's last good values from pipeline/state/sources.json and marks it
stale, so one broken page never blanks the site.
"""
import csv
import datetime as dt
import html as htmllib
import io
import json
import re
import statistics
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from places import DELOITTE_CITIES, KRAJE, KRAJ_BY_NUTS, OKRES_TOWNS, RU_CAPITALS, slug  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site/static/data"
STATE = ROOT / "pipeline/state/sources.json"
MANUAL = ROOT / "pipeline/manual"
K = list(KRAJE)
BAND = 0.25  # validation band against the previous period
MONTHS_SK = {"január": 1, "február": 2, "marec": 3, "apríl": 4, "máj": 5, "jún": 6, "júl": 7, "august": 8,
             "september": 9, "október": 10, "november": 11, "december": 12}


class Invalid(Exception):
    pass


def check_band(name, series):
    """series: {key: (previous, latest)}; every key must move less than BAND."""
    for key, (prev, last) in series.items():
        if not prev or not last or abs(last / prev - 1) > BAND:
            raise Invalid(f"{name} {key}: {prev} -> {last} is outside ±{BAND:.0%}")


def check_kraje(name, d):
    missing = [k for k in K if k not in d]
    if missing:
        raise Invalid(f"{name}: missing kraje {missing}")


# ---------- one parser per source ----------

def p_nbs(raw):
    hits = [h["_source"] for h in json.load(open(raw / "nbs_region.json"))["hits"]["hits"]]
    q = sorted([h for h in hits if h["quarter"]], key=lambda r: (r["year"], r["quarter"]))
    yr = sorted([h for h in hits if not h["quarter"]], key=lambda r: r["year"])
    check_kraje("NBS", q[-1])
    check_band("NBS", {k: (q[-2][k], q[-1][k]) for k in K})
    first = yr[0]
    years = int(q[-1]["year"]) + int(q[-1]["quarter"][0]) / 4 - int(first["year"]) - 0.5
    return {
        "period": f'Q{q[-1]["quarter"][0]} {q[-1]["year"]}',
        "price": {k: round(q[-1][k], 1) for k in K},
        "yoy": {k: round(q[-1][k] / q[-5][k] - 1, 4) for k in K},
        "cagr": {k: round((q[-1][k] / first[k]) ** (1 / years) - 1, 4) for k in K},
        "cagr_from": first["year"],
        "annual": [[h["year"], *[round(h[k]) for k in K]] for h in yr],
        "quarterly": [[f'{h["year"]}Q{h["quarter"][0]}', *[round(h[k]) for k in K]] for h in q],
    }


def statdata_rows(raw, name):
    z = zipfile.ZipFile(raw / f"statdata_{name}.zip")
    csv_name = next(n for n in z.namelist() if n.endswith(f"{name}_CSV_SK.csv"))
    return list(csv.DictReader(io.TextIOWrapper(z.open(csv_name), encoding="utf-8")))


def p_wage(raw):
    rows = [r for r in statdata_rows(raw, "np3112qr") if r["e_unit_code"] == "UNIT_EUR" and r["hodnota"] != "."]
    rows = [r for r in rows if re.fullmatch(r"\d\. Q\.", r["e_quarter"]) and r["e_nuts13_code"] in KRAJ_BY_NUTS]
    periods = sorted({(r["e_year"], r["e_quarter"][0]) for r in rows})
    by = {(r["e_year"], r["e_quarter"][0], KRAJ_BY_NUTS[r["e_nuts13_code"]]): float(r["hodnota"]) for r in rows}
    last = periods[-1]
    value = {k: by[(*last, k)] for k in K if (*last, k) in by}
    check_kraje("ŠÚ SR mzdy", value)
    # wages are seasonal (Q4 bonuses), so compare with the same quarter a year earlier
    check_band("ŠÚ SR mzdy", {k: (by.get((str(int(last[0]) - 1), last[1], k)), value[k]) for k in K})
    return {"period": f"Q{last[1]} {last[0]}", "value": value,
            "quarterly": [[f"{y}Q{q}", *[by.get((y, q, k)) for k in K]] for y, q in periods]}


def p_su_index(raw):
    rows = [r for r in statdata_rows(raw, "sp3801qr") if r["hodnota"] != "." and r["e_repurch"] == "Spolu"
            and r["e_unit_code"] == "UNIT_INX_Y_ROMR" and r["e_nuts13_code"] in KRAJ_BY_NUTS]
    periods = sorted({(r["e_year"], r["e_quarter"][0]) for r in rows})
    by = {(r["e_year"], r["e_quarter"][0], KRAJ_BY_NUTS[r["e_nuts13_code"]]): float(r["hodnota"]) for r in rows}
    last = periods[-1]
    yoy = {k: round(by[(*last, k)] / 100 - 1, 4) for k in K if (*last, k) in by}
    check_kraje("ŠÚ SR index", yoy)
    return {"period": f"Q{last[1]} {last[0]}", "yoy": yoy,
            "quarterly": [[f"{y}Q{q}", *[by.get((y, q, k)) for k in K]] for y, q in periods]}


ECB_FIX = {"A": "Spolu", "F": "Pohyblivá a fixácia do 1 roka", "I": "Fixácia nad 1 do 5 rokov",
           "O": "Fixácia nad 5 do 10 rokov", "P": "Fixácia nad 10 rokov"}


def p_ecb(raw):
    out = {}
    for code, label in ECB_FIX.items():
        f = raw / f"ecb_mir_{code}.csv"
        if not f.exists():
            continue
        rows = [r for r in csv.DictReader(open(f)) if r["OBS_VALUE"]]
        out[code] = {"label": label, "series": [[r["TIME_PERIOD"], float(r["OBS_VALUE"])] for r in rows]}
    if "A" not in out:
        raise Invalid("ECB: total rate missing")
    s = out["A"]["series"]
    check_band("ECB", {"A": (s[-2][1], s[-1][1])})
    return {"period": s[-1][0], "rate": s[-1][1], "by_fixation": out}


def p_cp041(raw):
    d = json.load(open(raw / "eurostat_cp041.json"))
    inv = {i: k for k, i in d["dimension"]["time"]["category"]["index"].items()}
    ser = sorted((inv[int(i)], v) for i, v in d["value"].items())
    by = dict(ser)
    last, v = ser[-1]
    y = int(last[:4])
    check_band("Eurostat CP041", {"SK": (ser[-2][1], v)})
    return {"period": last, "yoy": round(v / by[f"{y - 1}{last[4:]}"] - 1, 4),
            "avg10": round((v / by[f"{y - 10}{last[4:]}"]) ** 0.1 - 1, 4),
            "monthly": [[p, x] for p, x in ser if p >= "2002-01"]}


def realitymap_kraj(raw, deal):
    s = open(raw / f"realitymap_{deal}.html", encoding="utf-8").read()
    i = s.find('\\"krajSeries\\":[')
    if i < 0:
        raise Invalid(f"realitymap {deal}: krajSeries not found")
    ks = json.JSONDecoder().raw_decode(s[i + len('\\"krajSeries\\":'): i + 400000].replace('\\"', '"'))[0]
    d = {k["key"].upper(): k["points"] for k in ks}
    check_kraje(f"realitymap {deal}", d)
    check_band(f"realitymap {deal}", {k: (p[-2]["avgPricePerSqm"], p[-1]["avgPricePerSqm"]) for k, p in d.items()})
    return {"period": d["BA"][-1]["date"][:7],
            "m2": {k: round(statistics.mean(x["avgPricePerSqm"] for x in p[-3:]), 2) for k, p in d.items()},
            "n": {k: p[-1]["listingCount"] for k, p in d.items()},
            "monthly": [[pt["date"][:7], *[round(d[k][i]["avgPricePerSqm"], 2) for k in K]]
                        for i, pt in enumerate(d["BA"])]}


def p_rm_sale(raw):
    return realitymap_kraj(raw, "predaj")


def p_rm_rent(raw):
    return realitymap_kraj(raw, "prenajom")


def quality(sale, rent):
    """standard: ≥ 50 sale and ≥ 30 rent listings in each of the last 3 months; indicative: ≥ 20 and ≥ 10."""
    if len(sale) < 3 or len(rent) < 3 or sale[-1]["date"] != rent[-1]["date"]:
        return None
    s, r = min(p["listingCount"] for p in sale[-3:]), min(p["listingCount"] for p in rent[-3:])
    if s >= 50 and r >= 30:
        return "standard"
    if s >= 20 and r >= 10:
        return "indicative"
    return None


def p_rm_towns(raw):
    towns = {}
    for line in open(raw / "realitymap_towns.jsonl"):
        x = json.loads(line)
        if x.get("series"):
            towns.setdefault(x["slug"], {})[x["deal"]] = x["series"]
    out = {}
    for s, t in towns.items():
        sale, rent = t.get("predaj", []), t.get("prenajom", [])
        q = quality(sale, rent)
        if not q:
            continue
        out[s] = {"quality": q, "period": sale[-1]["date"][:7],
                  "price": round(statistics.mean(p["avgPricePerSqm"] for p in sale[-3:])),
                  "rent": round(statistics.mean(p["avgPricePerSqm"] for p in rent[-3:]), 2),
                  "n_sale": sale[-1]["listingCount"], "n_rent": rent[-1]["listingCount"],
                  "rent_area": rent[-1]["medianArea"],
                  "start": sale[-36:][0]["date"][:7] if len(sale) >= 36 else sale[0]["date"][:7],
                  "sale_m2": [round(p["avgPricePerSqm"]) for p in sale[-36:]],
                  "rent_m2": [round(p["avgPricePerSqm"], 2) for p in rent[-len(sale[-36:]):]]}
    if not {"bratislava", "kosice", "zilina"} <= out.keys():
        raise Invalid(f"realitymap towns: only {len(out)} usable, big cities missing")
    return out


def p_ru(raw):
    s = open(raw / "realitnaunia_barometer.html", encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    toks = [x.strip() for x in htmllib.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n") if x.strip()]
    head = next(x for x in toks if x.startswith("Ceny bytov – "))
    month = head.removeprefix("Ceny bytov – ").split()
    period = f"{month[1]}-{MONTHS_SK[month[0].lower()]:02d}"
    start = toks.index(head)
    i = toks.index("Krajské mestá", toks.index("Krajské mestá", start) + 1)
    capitals = {}
    for c in RU_CAPITALS.values():
        i = toks.index(c, i)
        rows, j = {}, i + 1
        for _ in range(4):
            size, old, _, new, _ = toks[j:j + 5]
            rows[size] = {"older": float(old), "newer": float(new)}
            j += 5
        capitals[c] = rows
        i = j
    rank_head = next(x for x in toks[start:] if x.startswith("Rebríček 30 vybraných miest"))
    rank_date = re.search(r"k (\d+)\.(\d+)\.(\d{4})", rank_head)
    j = toks.index(rank_head) + 1
    while toks[j].rstrip(".") != "1":  # skip the header cells up to rank 1
        j += 1
    towns = {}
    while len(towns) < 30:
        _, name, price, chg = toks[j:j + 4]
        towns[slug(name)] = {"name": name, "m2": float(price), "yoy": float(chg) / 100}
        j += 4
    for c, rows in capitals.items():
        for size, v in rows.items():
            if not 800 < v["older"] < 15000:
                raise Invalid(f"RÚ {c} {size}: {v['older']} €/m² is implausible")
    return {"period": period, "capitals": capitals,
            "ranking": {"date": f"{rank_date[3]}-{int(rank_date[2]):02d}-{int(rank_date[1]):02d}", "towns": towns}}


def p_deloitte(raw):
    d = json.load(open(MANUAL / "deloitte.json"))
    p = d["periods"][0]
    newest_pdf = re.findall(r'Rent_Index_Q(\d)_(\d{4})_SK\.pdf', (raw / "deloitte_rent_index.html").read_text(errors="replace")) \
        if (raw / "deloitte_rent_index.html").exists() else []
    newest = max((f"Q{q} {y}" for q, y in newest_pdf), key=lambda s: (s[-4:], s[1]), default=p["period"])
    return {"period": p["period"], "rent": p["rent_per_flat"], "national": p["national"], "pdf": p["pdf"],
            "newer_available": newest if (newest[-4:], newest[1]) > (p["period"][-4:], p["period"][1]) else None}


PARSERS = {"nbs": p_nbs, "wage": p_wage, "su_index": p_su_index, "ecb": p_ecb, "cp041": p_cp041,
           "rm_sale": p_rm_sale, "rm_rent": p_rm_rent, "rm_towns": p_rm_towns, "ru": p_ru, "deloitte": p_deloitte}

SOURCES = {
    "nbs": ("NBS – ponukové ceny nehnuteľností podľa krajov", "https://nbs.sk/statisticke-udaje/vybrane-makroekonomicke-ukazovatele/ceny-nehnutelnosti-na-byvanie", "štvrťročne"),
    "wage": ("ŠÚ SR – priemerná mesačná mzda podľa krajov (np3112qr)", "https://statdata.statistics.sk/", "štvrťročne"),
    "su_index": ("ŠÚ SR – indexy realizačných cien nehnuteľností (sp3801qr)", "https://statdata.statistics.sk/", "štvrťročne"),
    "ecb": ("ECB MIR – úrokové sadzby nových úverov na bývanie, Slovensko", "https://data.ecb.europa.eu/data/datasets/MIR", "mesačne"),
    "cp041": ("Eurostat HICP CP041 – skutočne platené nájomné, Slovensko", "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table", "mesačne"),
    "rm_sale": ("realitymap.sk – ponukové ceny bytov na predaj", "https://realitymap.sk/ceny/predaj/byty", "mesačne"),
    "rm_rent": ("realitymap.sk – ponukové nájomné bytov", "https://realitymap.sk/ceny/prenajom/byty", "mesačne"),
    "rm_towns": ("realitymap.sk – mestá a mestské časti", "https://realitymap.sk/ceny/prenajom/byty", "mesačne"),
    "ru": ("Realitná únia SR – Realitný barometer", "https://www.realitnaunia.sk/realitny-barometer", "mesačne"),
    "deloitte": ("Deloitte Rent Index", "https://www.deloitte.com/cz-sk/sk/Industries/real-estate/collections/rent-index.html", "štvrťročne, ručne"),
}


def parse_all(raw):
    prev = json.load(open(STATE)) if STATE.exists() else {}
    fetched = json.load(open(raw / "fetch.json"))["fetched"] if (raw / "fetch.json").exists() else None
    state, status = {}, {}
    for key, fn in PARSERS.items():
        try:
            state[key] = fn(raw)
            status[key] = {"stale": False, "fetched": fetched}
        except Exception as e:  # keep last month's values, flag the source on the methodology page
            print(f"WARNING {key}: {e!r}", file=sys.stderr)
            if key not in prev:
                raise SystemExit(f"{key} failed and there is no previous good copy")
            state[key] = prev[key]
            status[key] = {"stale": True, "error": str(e)[:200], "fetched": prev.get("_status", {}).get(key, {}).get("fetched")}
        name, url, freq = SOURCES[key]
        status[key].update(name=name, url=url, frequency=freq, period=state[key].get("period"))
    state["_status"] = status
    return state


# ---------- derived files ----------

def build_places(S, rules):
    munis = json.load(open(ROOT / "pipeline/geo/municipalities.json"))
    cap = rules["sna_rent_cap"]
    coef, size = cap["flat_types"]["2"]
    places = []
    for k, (nuts, name) in KRAJE.items():
        wage = S["wage"]["value"][k]
        places.append({
            "id": k.lower(), "name": name, "level": "kraj", "kraj": k, "nuts": nuts,
            "price": {"value": S["nbs"]["price"][k], "source": "nbs", "period": S["nbs"]["period"],
                      "checks": [{"source": "rm_sale", "value": round(S["rm_sale"]["m2"][k]), "period": S["rm_sale"]["period"],
                                  "note": "priemer 3 mesiacov"}]},
            "rent": {"value": S["rm_rent"]["m2"][k], "source": "rm_rent", "period": S["rm_rent"]["period"],
                     "n": S["rm_rent"]["n"][k], "note": "priemer 3 mesiacov",
                     "checks": [{"source": "sna", "value": round(wage * cap["share_of_wage"] * coef / size, 2),
                                 "period": S["wage"]["period"], "note": "zákonný strop ŠNA pre 2-izbový byt, nie trhové nájomné"}]},
            "wage": {"value": wage, "source": "wage", "period": S["wage"]["period"]},
            "growth": {"nbs_cagr": S["nbs"]["cagr"][k], "from": S["nbs"]["cagr_from"], "nbs_yoy": S["nbs"]["yoy"][k],
                       "su_yoy": S["su_index"]["yoy"].get(k)},
            "quality": "standard",
        })
    ru, rank = S["ru"], S["ru"]["ranking"]
    listed = {slug(t) for t in OKRES_TOWNS}
    for s, t in S["rm_towns"].items():
        m = munis.get(s)
        if not m or not (s in listed or s.startswith(("bratislava-", "kosice-"))):
            continue
        kraj = m["kraj"]
        rm_check = {"source": "rm_sale", "value": t["price"], "period": t["period"], "note": "priemer 3 mesiacov, všetky byty"}
        if s in RU_CAPITALS:
            c = ru["capitals"][RU_CAPITALS[s]]
            price = {"value": round((c["2 izb."]["older"] + c["3 izb."]["older"]) / 2), "source": "ru", "period": ru["period"],
                     "note": "staršie 2- a 3-izbové byty", "checks": [rm_check]}
        elif s in rank["towns"]:
            price = {"value": rank["towns"][s]["m2"], "source": "ru", "period": rank["date"][:7],
                     "note": "staršie 3-izbové byty, štvrťročný rebríček", "checks": [rm_check]}
        else:
            price = {"value": t["price"], "source": "rm_sale", "period": t["period"], "note": "priemer 3 mesiacov", "checks": []}
        rent = {"value": t["rent"], "source": "rm_towns", "period": t["period"], "n": t["n_rent"],
                "note": "priemer 3 mesiacov", "checks": []}
        if s in DELOITTE_CITIES and s in S["deloitte"]["rent"]:
            rent["checks"].append({"source": "deloitte", "value": S["deloitte"]["rent"][s], "period": S["deloitte"]["period"],
                                   "per": "byt", "note": f"nájomné za byt; mediánový prenajímaný byt tu má {t['rent_area']:.0f} m²"})
        level = "mestska-cast" if s.startswith(("bratislava-", "kosice-")) else "mesto"
        name = m["name"].replace("-", " – ") if level == "mestska-cast" else m["name"]
        places.append({
            "id": s, "name": name, "level": level, "kraj": kraj, "okres": m["okres"], "price": price, "rent": rent,
            "wage": {"value": S["wage"]["value"][kraj], "source": "wage", "period": S["wage"]["period"],
                     "note": "mzda za celý kraj; ŠÚ SR nezverejňuje mzdy za mestá"},
            "growth": {"nbs_cagr": S["nbs"]["cagr"][kraj], "from": S["nbs"]["cagr_from"], "nbs_yoy": S["nbs"]["yoy"][kraj],
                       "su_yoy": S["su_index"]["yoy"].get(kraj), "ru_yoy": rank["towns"].get(s, {}).get("yoy")},
            "listings": {"sale": t["n_sale"], "rent": t["n_rent"]},
            "quality": t["quality"],
        })
    order = {"kraj": 0, "mesto": 1, "mestska-cast": 2}
    places.sort(key=lambda p: (order[p["level"]], p["name"]))
    return places


def main():
    raws = sorted(p for p in Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "raw").iterdir() if p.is_dir())
    raw = raws[-1]
    print("building from", raw)
    S = parse_all(raw)
    rules = json.load(open(MANUAL / "rules.json"))
    banks = json.load(open(MANUAL / "banks.json"))
    today = dt.date.today()
    warnings = []
    if rules["tax_year"] < today.year:
        warnings.append(f"rules.json is for tax year {rules['tax_year']}; review it for {today.year}")
    for o in banks["offers"]:
        o["stale"] = (today - dt.date.fromisoformat(o["checked"])).days > 45
    if any(o["stale"] for o in banks["offers"]):
        warnings.append("some bank offers are older than 45 days")
    if S["deloitte"].get("newer_available"):
        warnings.append(f"Deloitte {S['deloitte']['newer_available']} is out; add it to pipeline/manual/deloitte.json")
    for k, st in S["_status"].items():
        if st["stale"]:
            warnings.append(f"{k} is stale: {st['error']}")

    S["_status"]["sna"] = {"name": "Štátna nájomná agentúra – výpočet maximálneho nájomného", "url": rules["sna_rent_cap"]["url"],
                           "frequency": "ročne", "period": S["wage"]["period"], "stale": False}
    latest = {
        "generated": today.isoformat(),
        "sources": S["_status"],
        "defaults": {"rate": S["ecb"]["rate"], "rate_period": S["ecb"]["period"],
                     "rent_growth": S["cp041"]["avg10"], "rent_growth_period": S["cp041"]["period"],
                     "paid_rent_yoy": S["cp041"]["yoy"]},
        "places": build_places(S, rules),
        "warnings": warnings,
    }
    history = {
        "kraje": K,
        "nbs_annual": S["nbs"]["annual"], "nbs_quarterly": S["nbs"]["quarterly"],
        "wage_quarterly": S["wage"]["quarterly"], "su_index_quarterly": S["su_index"]["quarterly"],
        "rm_rent_monthly": S["rm_rent"]["monthly"], "rm_sale_monthly": S["rm_sale"]["monthly"],
        "cp041_monthly": S["cp041"]["monthly"],
        "towns": {s: {k: t[k] for k in ("start", "sale_m2", "rent_m2")} for s, t in S["rm_towns"].items()},
    }
    ecb = S["ecb"]["by_fixation"]
    rates = {"period": S["ecb"]["period"], "rate": S["ecb"]["rate"],
             "ecb": {c: {"label": v["label"], "series": v["series"][-60:]} for c, v in ecb.items()},
             "ecb_total_since_2008": ecb["A"]["series"], "banks": banks}
    DATA.mkdir(parents=True, exist_ok=True)
    for name, obj in {"latest": latest, "history": history, "rates": rates, "rules": rules}.items():
        json.dump(obj, open(DATA / f"{name}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    STATE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(S, open(STATE, "w"), ensure_ascii=False, indent=0)
    print(f"{len(latest['places'])} places;", "warnings:", warnings or "none")
    for f in sorted(DATA.iterdir()):
        print(f"  {f.name} {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
