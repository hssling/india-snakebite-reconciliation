"""Build the state x year x source panel for the snakebite mortality reconciliation.

Outputs (all regenerated from local files; no network access):
  data/state_year_source_panel.csv   long panel (one row per state/geography x period x source x vintage)
  data/state_population.csv          Technical Group (2019) projected population, 1 July, 2011-2024
  data/completeness_anchors.csv      measured completeness values and place-of-death ceilings
  data/state_name_mapping.csv        every raw name seen -> canonical unit, per source
  data/panel_validation_log.txt      every row-sum / printed-total check and its result

Inputs:
  data/ncrb_adsi_snakebite_state_year.csv   (from src/extract_ncrb_adsi_snakebite.py; rerun that first if PDFs change)
  data_raw/snakebite/nhp/*.pdf              National Health Profile 2019, 2020, 2021, 2023
  MCCD annual reports 2016-2024 (paths in MCCD_PDFS)
  data_raw/snakebite/population/technical_group_population_projections_2011_2036_Nov2019.pdf
  data_raw/snakebite/literature/*.bioc.json PMC full texts (Suraweera 2020, Mohapatra 2011, Kadam 2025,
                                             Menon 2025, Dandona 2018, Kiran 2026)
Values that exist only in abstracts (TN IHIP, Karnataka HMIS, West Bengal surveys) and secondary-only
values (IHIP parliamentary figures, Kerala Forest Department) are entered literally below with their source.

Usage: python -I src/build_panel.py
"""
from __future__ import annotations

import csv
import os
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import fitz  # PyMuPDF

sys.stdout.reconfigure(encoding="utf-8")

PROJ = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("SNAKEBITE_RAW", PROJ / "data_raw"))   # see README: where to obtain each file
LIT = RAW / "literature"
OUT = PROJ / "data"
MCCD_DIR = RAW / "mccd"
MCCD_PDFS = {y: MCCD_DIR / f"Annual_Report_on_MCCD_{y}.pdf" for y in range(2016, 2024)}
MCCD_PDFS[2024] = MCCD_DIR / "Annual_Report_on_MCCD_2024.pdf"
POP_PDF = RAW / "population" / "technical_group_population_projections_2011_2036_Nov2019.pdf"

LOG: list[str] = []
MAPPING: dict[tuple, str] = {}


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg)


# --------------------------------------------------------------------------------------------
# Canonical state/UT units (36 current units) and explicit aggregate units
# --------------------------------------------------------------------------------------------
CANON = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman & Nicobar Islands", "Chandigarh",
    "Dadra & Nagar Haveli and Daman & Diu", "Delhi", "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]
AP_UNDIV = "Andhra Pradesh + Telangana (undivided AP)"
JK_UNDIV = "Jammu & Kashmir + Ladakh (former J&K state)"
NE7 = "NE-7 (Arunachal, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, Tripura)"
INDIA = "India"
DNH = "Dadra & Nagar Haveli (pre-2020 unit)"
DD = "Daman & Diu (pre-2020 unit)"
DNHDD = "Dadra & Nagar Haveli and Daman & Diu"


def key(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


RAWMAP = {  # normalised raw name -> canonical
    "andhrapradesh": "Andhra Pradesh", "arunachalpradesh": "Arunachal Pradesh", "assam": "Assam",
    "bihar": "Bihar", "chhattisgarh": "Chhattisgarh", "goa": "Goa", "gujarat": "Gujarat", "haryana": "Haryana",
    "himachalpradesh": "Himachal Pradesh", "jharkhand": "Jharkhand", "karnataka": "Karnataka", "kerala": "Kerala",
    "madhyapradesh": "Madhya Pradesh", "maharashtra": "Maharashtra", "manipur": "Manipur", "meghalaya": "Meghalaya",
    "mizoram": "Mizoram", "nagaland": "Nagaland", "odisha": "Odisha", "orissa": "Odisha", "punjab": "Punjab",
    "rajasthan": "Rajasthan", "sikkim": "Sikkim", "tamilnadu": "Tamil Nadu", "telangana": "Telangana",
    "tripura": "Tripura", "uttarpradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand", "westbengal": "West Bengal",
    "anislands": "Andaman & Nicobar Islands", "andamanandnicobarislands": "Andaman & Nicobar Islands",
    "andamannicobarislands": "Andaman & Nicobar Islands", "chandigarh": "Chandigarh", "delhi": "Delhi",
    "delhiut": "Delhi", "lakshadweep": "Lakshadweep", "puducherry": "Puducherry", "ladakh": "Ladakh",
    "dnhaveli": DNH, "dadraandnagarhaveli": DNH, "dadranagarhaveli": DNH, "damandiu": DD, "damananddiu": DD,
    "dnhavelianddamandiu": DNHDD, "dnhavelidamandiu": DNHDD,
}


def canon(raw: str, source: str, year=None) -> str:
    """Map a raw printed name to a canonical unit. J&K before 2020 -> former J&K state (incl. Ladakh)."""
    k = key(raw.replace("*", ""))
    if k in ("jammukashmir", "jammuandkashmir", "jammukashmirut"):
        out = JK_UNDIV if (year is not None and int(year) < 2020) else "Jammu & Kashmir"
    elif k in RAWMAP:
        out = RAWMAP[k]
    else:
        raise KeyError(f"unmapped name {raw!r} ({source} {year})")
    MAPPING[(source, raw, out)] = "pre-2020 J&K includes Ladakh" if out == JK_UNDIV else ""
    return out


PANEL_FIELDS = ["state", "state_as_printed", "geography_level", "district", "year", "ref_start", "ref_end",
                "period_type", "source", "source_detail", "vintage", "preferred", "deaths", "cases",
                "rate_per_100k", "denominator_note", "status", "page_or_table", "notes"]
PANEL: list[dict] = []


def row(**k):
    bad = set(k) - set(PANEL_FIELDS)
    assert not bad, bad
    r = {f: k.get(f, "") for f in PANEL_FIELDS}
    if r["year"] != "" and r["ref_start"] == "":
        r["ref_start"], r["ref_end"] = f"{r['year']}-01-01", f"{r['year']}-12-31"
    if r["preferred"] == "":
        r["preferred"] = 1
    PANEL.append(r)


def check(label: str, got, expected, tol=0) -> bool:
    ok = abs(got - expected) <= tol
    tag = "OK" if got == expected else ("OK-ROUNDING" if ok else "MISMATCH")
    log(f"[{tag}] {label}: computed {got} vs printed {expected}" + (f" (tolerance {tol:.2f})" if tol else ""))
    return ok


# --------------------------------------------------------------------------------------------
# 1. NCRB (police)
# --------------------------------------------------------------------------------------------
def build_ncrb():
    src = OUT / "ncrb_adsi_snakebite_state_year.csv"
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    by_year = defaultdict(list)
    for r in rows:
        by_year[int(r["year"])].append(r)
    for y, rs in sorted(by_year.items()):
        total = next(r for r in rs if r["state"] == "TOTAL (ALL INDIA)")
        states = [r for r in rs if r["state"] not in ("TOTAL (ALL INDIA)",) and not r["state"].startswith("UNPARSED")]
        assert not any(r["state"].startswith("UNPARSED") for r in rs), f"NCRB {y} has an unparsed residual"
        check(f"NCRB {y} sum of state deaths = TOTAL (ALL INDIA)", sum(int(r["persons_died"]) for r in states), int(total["persons_died"]))
        check(f"NCRB {y} sum of state cases = TOTAL (ALL INDIA)", sum(int(r["cases"]) for r in states), int(total["cases"]))
        merged = defaultdict(lambda: [0, 0, []])
        for r in states:
            c = canon(r["state"], "NCRB", y)
            if c in (DNH, DD):
                merged[DNHDD][0] += int(r["persons_died"]); merged[DNHDD][1] += int(r["cases"]); merged[DNHDD][2].append(r["state"])
                continue
            row(state=c, state_as_printed=r["state"], geography_level="state", year=y, period_type="calendar year",
                source="NCRB", source_detail="ADSI 'Poisoning (Snake Bite)' persons died", vintage="final",
                deaths=r["persons_died"], cases=r["cases"], denominator_note="state population (see state_population.csv)",
                status="primary", page_or_table=f"ADSI {y} {r['adsi_table']}, PDF p.{r['pdf_page']}",
                notes="police-recorded; 'cases' = number of cases (incidents) in the same table")
        for c, (d, cs, parts) in merged.items():
            row(state=c, state_as_printed=" + ".join(parts), geography_level="state", year=y, period_type="calendar year",
                source="NCRB", source_detail="ADSI 'Poisoning (Snake Bite)' persons died", vintage="final",
                deaths=d, cases=cs, status="derived (sum of the two pre-merger UT rows)",
                page_or_table=f"ADSI {y} {states[0]['adsi_table']}", notes="DNH and Daman & Diu printed separately before 2020")
        row(state=INDIA, state_as_printed="TOTAL (ALL INDIA)", geography_level="national", year=y, period_type="calendar year",
            source="NCRB", source_detail="ADSI 'Poisoning (Snake Bite)' persons died", vintage="final",
            deaths=total["persons_died"], cases=total["cases"], status="primary",
            page_or_table=f"ADSI {y} {total['adsi_table']}, PDF p.{total['pdf_page']}", notes="printed national total")


# --------------------------------------------------------------------------------------------
# 2. National Health Profile (public facilities, ICD-10 T63.0)
# --------------------------------------------------------------------------------------------
NHP_TABLES = [  # report, pdf, pdf page (1-based), data year, vintage, printed table id, printed page
    ("NHP 2019", "National-health-2019.pdf", 175, 2017, "final", "Table 3.2.9 (A)", 151),
    ("NHP 2019", "National-health-2019.pdf", 176, 2018, "provisional", "Table 3.2.9 (B)", 152),
    ("NHP 2020", "National-health-2020.pdf", 244, 2018, "final", "Table 3.2.9 (a)", 218),
    ("NHP 2020", "National-health-2020.pdf", 245, 2019, "provisional", "Table 3.2.9 (b)", 219),
    ("NHP 2021", "National-health-2021.pdf", 256, 2019, "final", "Table 3.2.9 (A)", 230),
    ("NHP 2021", "National-health-2021.pdf", 257, 2020, "provisional", "Table 3.2.9 (B)", 231),
    ("NHP 2023", "NHP-2023-Last-Final.pdf", 174, 2021, "final", "Table 3.2.3 (A)", 153),
    ("NHP 2023", "NHP-2023-Last-Final.pdf", 175, 2022, "provisional", "Table 3.2.3 (B)", 154),
]
# a year is 'preferred' only in its latest vintage: final where one exists in a later report
NHP_PREFERRED = {(2017, "NHP 2019"), (2018, "NHP 2020"), (2019, "NHP 2021"), (2020, "NHP 2021"), (2021, "NHP 2023"), (2022, "NHP 2023")}


def parse_nhp_table(text: str):
    body = text.split("Cases Deaths Cases Deaths Cases Deaths", 1)[1].split("Source:", 1)[0]
    toks = body.split()
    rows, name, nums = [], [], []
    for t in toks:
        if re.fullmatch(r"\d+|NA", t):
            nums.append(t)
            if len(nums) == 6 and name:
                rows.append((" ".join(name), nums))
                name, nums = [], []
        else:
            if t in ("a", "b"):
                continue
            if nums:  # a short numeric run before a name is the serial number
                nums = []
            name.append(t)
    return rows


def build_nhp():
    for rep, pdf, pg, yr, vint, tab, ppage in NHP_TABLES:
        doc = fitz.open(RAW / "nhp" / pdf)
        text = " ".join(doc[pg - 1].get_text().split())
        assert str(yr) in text[:400], (rep, pg, yr)
        rows = parse_nhp_table(text)
        tot = [r for r in rows if r[0] in ("India", "Total")]
        assert len(tot) == 1, (rep, yr, tot)
        tot = [int(x) for x in tot[0][1]]
        states = [r for r in rows if r[0] not in ("India", "Total")]
        label = f"{rep} {tab} (data year {yr}, {vint})"
        # row-level M+F=T checks and column sums
        colsum = [0] * 6
        for nm, v in states:
            if "NA" in v:
                continue
            v = [int(x) for x in v]
            for i in range(6):
                colsum[i] += v[i]
            if v[0] + v[2] != v[4] or v[1] + v[3] != v[5]:
                log(f"[MISMATCH] {label} row '{nm}': M+F cases {v[0]+v[2]} vs total {v[4]}; M+F deaths {v[1]+v[3]} vs total {v[5]}")
        for i, lab in enumerate(["male cases", "male deaths", "female cases", "female deaths", "total cases", "total deaths"]):
            check(f"{label} column sum of states, {lab}", colsum[i], tot[i])
        jk, dnhdd = defaultdict(lambda: [0, 0, []]), defaultdict(lambda: [0, 0, []])
        for nm, v in states:
            src_note = ""
            if nm.endswith("*"):
                src_note = "footnote '*': 'No reporting from the state in respect of the cases and death of snake bites' (printed 0)"
            k = key(nm)
            if k in ("jammudiv", "kashmirdiv", "jammu", "kashmir"):
                target = JK_UNDIV if yr < 2021 else "Jammu & Kashmir"
                MAPPING[("NHP", nm, target)] = "division rows summed" + ("; Ladakh not listed separately before 2021" if yr < 2021 else "")
                if "NA" not in v:
                    jk[target][0] += int(v[5]); jk[target][1] += int(v[4]); jk[target][2].append(f"{nm} {v[5]}")
                continue
            c = canon(nm, "NHP", yr)
            if c in (DNH, DD):
                dnhdd[DNHDD][0] += int(v[5]); dnhdd[DNHDD][1] += int(v[4]); dnhdd[DNHDD][2].append(f"{nm} {v[5]}")
                continue
            na = "NA" in v or src_note != ""
            row(state=c, state_as_printed=nm, geography_level="state", year=yr, period_type="calendar year",
                source="NHP", source_detail="ICD-10 T63.0 cases and deaths, State DHS reports", vintage=vint,
                preferred=1 if (yr, rep) in NHP_PREFERRED else 0,
                deaths="" if na else v[5], cases="" if na else v[4],
                status="primary", page_or_table=f"{rep}, {tab}, p.{ppage} (PDF p.{pg})",
                notes=("printed 'NA'" if "NA" in v else src_note) +
                      ("; probable column shift (deaths > 40% of cases, female cells 0)" if (rep == "NHP 2021" and yr == 2019 and c == "Assam") else ""))
        for grp in (jk, dnhdd):
            for c, (d, cs, parts) in grp.items():
                row(state=c, state_as_printed=" + ".join(parts), geography_level="state", year=yr, period_type="calendar year",
                    source="NHP", source_detail="ICD-10 T63.0 cases and deaths", vintage=vint,
                    preferred=1 if (yr, rep) in NHP_PREFERRED else 0, deaths=d, cases=cs,
                    status="derived (sum of printed sub-rows)", page_or_table=f"{rep}, {tab}, p.{ppage} (PDF p.{pg})",
                    notes="J&K printed as divisions" if c in (JK_UNDIV, "Jammu & Kashmir") else "DNH and Daman & Diu printed separately")
        # Ladakh is printed separately only in NHP 2023 and is handled by canon() above
        row(state=INDIA, state_as_printed="India" if rep == "NHP 2023" or rep == "NHP 2019" else "Total",
            geography_level="national", year=yr, period_type="calendar year", source="NHP",
            source_detail="ICD-10 T63.0", vintage=vint, preferred=1 if (yr, rep) in NHP_PREFERRED else 0,
            deaths=tot[5], cases=tot[4], status="primary", page_or_table=f"{rep}, {tab}, p.{ppage} (PDF p.{pg})",
            notes="West Bengal 'NA' (not in total)" if yr >= 2021 else "")


# --------------------------------------------------------------------------------------------
# 3. MCCD (medically certified deaths, X20-X27 snakes AND other venomous animals)
# --------------------------------------------------------------------------------------------
def mccd_colname(words: str) -> str | None:
    w = words.lower()
    if "States" in words:
        return INDIA
    rules = [ ("andhra", "Andhra Pradesh"), ("nicobar", "Andaman & Nicobar Islands"),
             ("arunachal", "Arunachal Pradesh"), ("assam", "Assam"), ("bihar", "Bihar"), ("chandigarh", "Chandigarh"),
             ("chhattisgarh", "Chhattisgarh"), ("delhi", "Delhi"), ("goa", "Goa"), ("gujarat", "Gujarat"),
             ("haryana", "Haryana"), ("himachal", "Himachal Pradesh"), ("kashmir", "J&K"), ("jharkhand", "Jharkhand"),
             ("karnataka", "Karnataka"), ("kerala", "Kerala"), ("ladakh", "Ladakh"), ("laksha", "Lakshadweep"),
             ("madhya", "Madhya Pradesh"), ("maharashtra", "Maharashtra"), ("manipur", "Manipur"),
             ("meghalaya", "Meghalaya"), ("mizoram", "Mizoram"), ("nagaland", "Nagaland"), ("odisha", "Odisha"),
             ("orissa", "Odisha"), ("puducherry", "Puducherry"), ("punjab", "Punjab"), ("rajasthan", "Rajasthan"),
             ("sikkim", "Sikkim"), ("tamil", "Tamil Nadu"), ("telangana", "Telangana"), ("tripura", "Tripura"),
             ("uttarakhand", "Uttarakhand"), ("uttar", "Uttar Pradesh"), ("bengal", "West Bengal")]
    if "haveli" in w and "daman" in w:
        return DNHDD
    if "haveli" in w:
        return DNH
    if "daman" in w:
        return DD
    if "group" in w or "major" in w:
        return None
    for k, v in rules:
        if k in w:
            return v
    if re.search(r"\bislands\b", w):
        return "Andaman & Nicobar Islands"
    return "?" + words


def mccd_page(page):
    W = page.get_text("words")
    lab = [w for w in W if w[4].startswith("snakes")]
    if not lab:
        return None
    lab = lab[0]
    ints = [w for w in W if re.fullmatch(r"\d{1,2}", w[4]) and w[1] < lab[1] - 5]
    byy = defaultdict(list)
    for w in ints:
        byy[round(w[1])].append(w)

    def run_len(ws):  # length of a run of consecutive column numbers (1,2,3,... or 19,20,...)
        v = [int(w[4]) for w in sorted(ws, key=lambda w: w[0])]
        return sum(1 for a, b in zip(v, v[1:]) if b == a + 1)

    cy = max(byy, key=lambda y: run_len(byy[y]))
    cols = sorted([w for w in ints if abs(round(w[1]) - cy) <= 1], key=lambda w: w[0])
    names = defaultdict(list)  # keyed by column INDEX (printed column numbers can repeat, e.g. '11' twice in 2021-22)
    for w in W:
        if re.fullmatch(r"[A-Z/\-\(\)]{2,}|\d+|-|/", w[4]):  # title words (all caps), digits
            continue
        if 40 < w[1] < cy - 2:
            xc = (w[0] + w[2]) / 2
            ci = min(range(len(cols)), key=lambda i: abs((cols[i][0] + cols[i][2]) / 2 - xc))
            if abs((cols[ci][0] + cols[ci][2]) / 2 - xc) < 12:
                names[ci].append(w[4])
    colmap = {i: ((c[0] + c[2]) / 2, mccd_colname(" ".join(names[i]))) for i, c in enumerate(cols)}
    dup = [nm for nm in set(v[1] for v in colmap.values()) if nm and sum(1 for v in colmap.values() if v[1] == nm) > 1]
    assert not dup, f"duplicate column names {dup}"
    near = [w for w in W if lab[1] - 3 < w[1] < lab[1] + 22 and re.fullmatch(r"\d+", w[4])]
    lines = defaultdict(list)
    for w in near:
        lines[round(w[1])].append(w)
    numeric = [sorted(v, key=lambda w: w[0]) for y, v in sorted(lines.items()) if len(v) >= max(3, len(cols) - 3)]
    assert len(numeric) >= 3, "could not find M/F/T lines"
    out = {}
    for sex, ln in zip("MFT", numeric[:3]):
        for w in ln:
            xc = (w[0] + w[2]) / 2
            cn, (cx, nm) = min(colmap.items(), key=lambda kv: abs(kv[1][0] - xc))
            if abs(cx - xc) < 10 and nm:
                out.setdefault(nm, {})[sex] = int(w[4])
    return out


def build_mccd():
    for y, pdf in sorted(MCCD_PDFS.items()):
        doc = fitz.open(pdf)
        data, pages = {}, []
        for i, p in enumerate(doc):
            t = p.get_text()
            if "TABLE 4" in t and "Bites of snakes" in t and "STATES" in t.upper():
                res = mccd_page(p)
                if res:
                    data.update(res); pages.append(i + 1)
            if len(pages) == 2:
                break
        bad = [k for k in data if k.startswith("?")]
        if bad:
            log(f"[MISMATCH] MCCD {y}: unrecognised column headers {bad}")
        total = data.pop(INDIA)
        for nm, v in data.items():
            if v.get("M", 0) + v.get("F", 0) != v.get("T"):
                log(f"[MISMATCH] MCCD {y} {nm}: M+F {v.get('M',0)+v.get('F',0)} vs T {v.get('T')}")
        check(f"MCCD {y} Table 4 sum of state T = All States (Total) T ({len(data)} columns, PDF pp.{pages})",
              sum(v["T"] for v in data.values()), total["T"])
        merged = defaultdict(lambda: [0, []])
        for nm, v in data.items():
            if nm == "J&K":
                c = JK_UNDIV if y < 2020 and "Ladakh" not in data else "Jammu & Kashmir"
                MAPPING[("MCCD", "Jammu & Kashmir", c)] = "Ladakh column absent" if c == JK_UNDIV else ""
            elif nm in (DNH, DD, DNHDD):
                merged[DNHDD][0] += v["T"]; merged[DNHDD][1].append(f"{nm} {v['T']}")
                MAPPING[("MCCD", nm, DNHDD)] = "summed with any other DNH/DD columns of the same year"
                continue
            else:
                c = nm
                MAPPING[("MCCD", nm, c)] = ""
            row(state=c, state_as_printed=nm, geography_level="state", year=y, period_type="calendar year",
                source="MCCD", source_detail="ICD-10 X20-X27 'Bites of snakes & other venomous animals' (NOT snake-only)",
                vintage="final", deaths=v["T"], status="primary", page_or_table=f"MCCD {y} Table 4, PDF pp.{pages}",
                notes=f"M {v.get('M')} F {v.get('F')}; category includes non-snake venomous animals")
        for c, (d, parts) in merged.items():
            row(state=c, state_as_printed=" + ".join(parts), geography_level="state", year=y, period_type="calendar year",
                source="MCCD", source_detail="ICD-10 X20-X27 (NOT snake-only)", vintage="final", deaths=d,
                status="derived (sum of DNH/DD columns)" if len(parts) > 1 else "primary", page_or_table=f"MCCD {y} Table 4, PDF pp.{pages}",
                notes="category includes non-snake venomous animals")
        row(state=INDIA, state_as_printed="All States (Total)", geography_level="national", year=y,
            period_type="calendar year", source="MCCD", source_detail="ICD-10 X20-X27 (NOT snake-only)", vintage="final",
            deaths=total["T"], status="primary", page_or_table=f"MCCD {y} Table 4, PDF p.{pages[0]}",
            notes=f"M {total.get('M')} F {total.get('F')}")


# --------------------------------------------------------------------------------------------
# 4. MDS (Suraweera 2020 Tables 3-4; Mohapatra 2011 Table 2)
# --------------------------------------------------------------------------------------------
def bioc_tables(fname):
    d = json.load(open(LIT / fname, encoding="utf-8"))
    d = d[0] if isinstance(d, list) else d
    out = {}
    for p in d["documents"][0]["passages"]:
        if p["infons"].get("type") == "table":
            rows = []
            for r in re.findall(r"<tr[^>]*>.*?</tr>", p["infons"]["xml"], re.S):
                rows.append([html.unescape(" ".join(re.sub(r"<[^>]+>", " ", c).split()))
                             for c in re.findall(r"<t[dh][^>]*>.*?</t[dh]>", r, re.S)])
            out[p["infons"].get("id")] = rows
    return out


MDS_NAME = {"Northeastern states": NE7, "All other states": "MDS residual group: all other states",
            "Andhra Pradesh": AP_UNDIV, "Jammu & Kashmir": JK_UNDIV}
SUR_CIT = "Suraweera W et al. eLife 2020;9:e54076 (doi:10.7554/eLife.54076)"


def build_mds():
    t = bioc_tables("PMC7340498.bioc.json")
    # ---- Table 3: state rates (3 periods) and deaths 2001-14 (thousands)
    t3 = [r for r in t["table3"] if len(r) >= 6 and re.fullmatch(r"\d+", r[1] or "")]
    groups = {"Higher burden states": [], "Lower burden states": []}
    cur = None
    for r in t3:
        nm = r[0]
        if nm in groups or nm == "All India":
            cur = nm if nm in groups else None
            continue
        if cur:
            groups[cur].append(r)
    for g, members in groups.items():
        printed = next(r for r in t3 if r[0] == g)
        check(f"MDS Suraweera T3 {g}: sum of member deaths 2001-14 (000)", round(sum(float(m[-1]) for m in members), 1), float(printed[-1]), tol=0.05 * len(members) + 1e-9)
        check(f"MDS Suraweera T3 {g}: sum of member study deaths", sum(int(m[1]) for m in members), int(printed[1]))
    allind = next(r for r in t3 if r[0] == "All India")
    check("MDS Suraweera T3 All India deaths (000) = higher + lower", round(sum(float(next(r for r in t3 if r[0] == g)[-1]) for g in groups), 1), float(allind[-1]), tol=0.25)
    for r in t3:
        nm = r[0]
        if nm in groups:
            continue
        st = INDIA if nm == "All India" else (MDS_NAME.get(nm) or canon(nm, "MDS", 2005))
        MAPPING[("MDS Suraweera T3", nm, st)] = "AP includes Telangana; J&K includes Ladakh" if st in (AP_UNDIV, JK_UNDIV) else ""
        lvl = "national" if st == INDIA else ("state-group" if st in (NE7,) or st.startswith("MDS residual") else "state")
        for (a, b), rate in zip([(2001, 2004), (2005, 2009), (2010, 2014)], r[2:5]):
            row(state=st, state_as_printed=nm, geography_level=lvl, ref_start=f"{a}-01-01", ref_end=f"{b}-12-31",
                period_type="annual average (rate only)", source="MDS", source_detail="verbal autopsy, ICD-10 X20; age-standardised rate",
                vintage="published", rate_per_100k=rate, denominator_note="rate standardised to Indian 2001 census population",
                status="primary", page_or_table="Suraweera 2020 Table 3", notes=f"{SUR_CIT}; study deaths 2001-14 = {r[1]}")
        row(state=st, state_as_printed=nm, geography_level=lvl, ref_start="2001-01-01", ref_end="2014-12-31",
            period_type="cumulative 14 years", source="MDS", source_detail="estimated deaths (MDS proportion x UN death totals)",
            vintage="published", deaths=int(round(float(r[-1]) * 1000)), status="primary (printed in thousands)",
            page_or_table="Suraweera 2020 Table 3", notes=f"printed {r[-1]} thousand; study deaths {r[1]}")
    # ---- Table 4: government hospital reports vs MDS, 2003-2015
    t4 = [r for r in t["table4"] if len(r) == 7 and re.fullmatch(r"[\d\.]+", r[1] or "")]
    gsum = {"Higher burden states†": [], "Lower burden states": []}
    cur = None
    for r in t4:
        nm = r[0].strip()
        if nm.startswith("Higher burden") or nm.startswith("Lower burden"):
            cur = nm
            gsum.setdefault(cur, [])
            continue
        if nm == "India":
            cur = None
            continue
        if cur:
            gsum[cur].append(r)
    for g, members in gsum.items():
        if not members:
            continue
        printed = next(r for r in t4 if r[0].strip() == g)
        for ci, lab in [(2, "government deaths (000)"), (4, "MDS total deaths (000)"), (5, "MDS in-hospital deaths (000)")]:
            check(f"MDS Suraweera T4 {g}: sum of member {lab}", round(sum(float(m[ci]) for m in members), 1), float(printed[ci]), tol=0.05 * len(members) + 1e-9)
    for r in t4:
        nm = r[0].strip()
        if nm.startswith("Higher burden") or nm.startswith("Lower burden"):
            continue
        st = INDIA if nm == "India" else (MDS_NAME.get(nm) or canon(nm, "MDS", 2005))
        MAPPING[("MDS Suraweera T4", nm, st)] = ""
        lvl = "national" if st == INDIA else ("state-group" if st in (NE7,) or st.startswith("MDS residual") else "state")
        common = dict(state=st, state_as_printed=nm, geography_level=lvl, ref_start="2003-01-01", ref_end="2015-12-31",
                      period_type="cumulative 13 years", vintage="published", page_or_table="Suraweera 2020 Table 4")
        row(**common, source="MDS", source_detail="estimated total snakebite deaths", deaths=int(round(float(r[4]) * 1000)),
            status="primary (printed in thousands)", notes=f"printed {r[4]} thousand; MDS in-hospital deaths {r[5]} thousand")
        row(**common, source="GovHospital-MoHFW", source_detail="deaths reported by government hospitals (MoHFW), as tabulated by Suraweera",
            deaths=int(round(float(r[2]) * 1000)), cases=int(round(float(r[1]) * 1000)),
            status="primary (printed in thousands; <100 printed as 0.0)",
            notes=f"printed deaths {r[2]} thousand, bites {r[1]} thousand; {r[3]} died in hospital; coverage vs MDS in-hospital deaths {r[6]}")
    # ---- Mohapatra 2011 Table 2 (2005 estimates, 13 high-prevalence states)
    t2 = bioc_tables("PMC3075236.bioc.json")
    tab = next(v for k, v in t2.items() if any(r and r[0] == "Sub total" for r in v))
    states = [r for r in tab if len(r) == 7 and re.fullmatch(r"[\d,]+/[\d,]+", r[1]) and r[0] not in ("Sub total", "Remaining states", "All India")]
    sub = next(r for r in tab if r[0] == "Sub total")
    allr = next(r for r in tab if r[0] == "All India")
    rem = next(r for r in tab if r[0] == "Remaining states")
    check("MDS Mohapatra T2: sum of 13 state deaths (000) = Sub total", round(sum(float(r[5]) for r in states), 1), float(sub[5]), tol=0.05 * 13)
    check("MDS Mohapatra T2: Sub total + Remaining = All India (000)", round(float(sub[5]) + float(rem[5]), 1), float(allr[5]), tol=0.1)
    check("MDS Mohapatra T2: sum of study deaths = Sub total", sum(int(r[1].split("/")[0].replace(",", "")) for r in states), int(sub[1].split("/")[0]))
    for r in states + [rem, allr]:
        nm = r[0]
        st = INDIA if nm == "All India" else ("Mohapatra residual group: remaining states" if nm == "Remaining states" else (MDS_NAME.get(nm) or canon(nm, "MDS", 2005)))
        MAPPING[("MDS Mohapatra T2", nm, st)] = "Orissa -> Odisha" if nm == "Orissa" else ""
        row(state=st, state_as_printed=nm, geography_level="national" if st == INDIA else ("state-group" if "residual" in st else "state"),
            year=2005, period_type="calendar year (2001-03 deaths applied to 2005 UN totals)", source="MDS",
            source_detail="verbal autopsy 2001-03; ICD-10 X20", vintage="published",
            deaths=int(round(float(r[5]) * 1000)), rate_per_100k=r[6], status="primary (printed in thousands)",
            page_or_table="Mohapatra 2011 Table 2",
            notes=f"study deaths/all deaths {r[1]}; died outside facility {r[3]}; rate standardised to 2005 UN estimates; Mohapatra B et al. PLoS NTD 2011;5:e1018")


# --------------------------------------------------------------------------------------------
# 5. State and district anchors
# --------------------------------------------------------------------------------------------
def build_anchors():
    # ---- Madhya Pradesh compensation (Kadam 2025, Table 1)
    t = bioc_tables("PMC11791426.bioc.json")
    tab = next(v for v in t.values() if any(r and r[0].startswith("Agar") for r in v))
    dist = [r for r in tab if len(r) == 8 and r[0] not in ("District", "Total", "") and re.fullmatch(r"\d+", r[2])]
    tot = next(r for r in tab if r and r[0] == "Total")
    check(f"MP compensation Table 1: sum of {len(dist)} district deaths FY2020-21 = Total", sum(int(r[2]) for r in dist), int(tot[2]))
    check(f"MP compensation Table 1: sum of district deaths FY2021-22 = Total", sum(int(r[5]) for r in dist), int(tot[5]))
    check("MP compensation Table 1: sum of district amounts FY2020-21 (lakh) = Total", sum(int(r[4].replace(" ", "")) for r in dist), int(tot[4].replace(" ", "")))
    log(f"[NOTE] MP compensation Table 1 'Total' rate columns print {tot[3]} and {tot[6]} (sums of district rates, not a state rate); abstract says 5728 families vs Table 1 {int(tot[2]) + int(tot[5])}")
    for fy, ci in [(2020, 2), (2021, 5)]:
        row(state="Madhya Pradesh", state_as_printed="Madhya Pradesh (Total)", geography_level="state",
            ref_start=f"{fy}-04-01", ref_end=f"{fy + 1}-03-31", period_type="financial year", year=fy,
            source="Compensation-MP", source_detail="paid snakebite-death compensation claims (postmortem required)",
            vintage="published", deaths=tot[ci], status="primary",
            denominator_note=f"Aadhaar-based population {tot[1]} (Oct 2023) used by source",
            page_or_table="Kadam 2025 Trans R Soc Trop Med Hyg 119:158 Table 1 (Total row)",
            notes=f"FY{fy}-{str(fy + 1)[2:]}; lower bound for true deaths; 'year' holds the FY start year")
    # ---- ICMR NTF community survey (Menon 2025, Table 7): district rows
    t = bioc_tables("PMC12603170.bioc.json")
    tab = next(v for v in t.values() if any(r and r[0] == "Jaisalmer" for r in v))
    dist = [r for r in tab if len(r) == 8 and r[0] not in ("District",)]
    tot = next(r for r in tab if r and r[0] == "Total")
    dsum = sum(int(r[3]) for r in dist if re.fullmatch(r"\d+", r[3]))
    check(f"ICMR NTF Table 7: sum of {len(dist)} district deaths = Total", dsum, int(tot[2]))
    check("ICMR NTF Table 7: sum of district incidents = Total", sum(int(r[2]) for r in dist), int(tot[1]))
    check("ICMR NTF Table 7: sum of district populations = Total", sum(int(r[4]) for r in dist), int(tot[3]))
    for r in dist:
        st = canon(r[1], "ICMR-NTF", 2024)
        row(state=st, state_as_printed=r[1], geography_level="district", district=r[0],
            ref_start="2022-01-01", ref_end="2025-12-31", period_type="12 months within 2022-25 (site-specific; Suppl. Table 1 not held)",
            source="ICMR-NTF", source_detail="prospective community surveillance by frontline workers",
            vintage="interim", deaths=r[3] if re.fullmatch(r"\d+", r[3]) else "", cases=r[2], rate_per_100k=r[6] if re.fullmatch(r"[\d\.]+", r[6]) else "",
            denominator_note=f"district population {r[4]} (2024 projection by source)", status="primary",
            page_or_table="Menon 2025 Nat Commun 16:9871 Table 7",
            notes="deaths printed '---'" if not re.fullmatch(r"\d+", r[3]) else "")
    row(state="25 districts in 11 states (pooled)", state_as_printed="Total", geography_level="multi-district",
        ref_start="2022-01-01", ref_end="2025-12-31", period_type="12 months per site", source="ICMR-NTF",
        source_detail="prospective community surveillance", vintage="interim", deaths=tot[2], cases=tot[1],
        rate_per_100k=tot[5], denominator_note=f"population {tot[3]}", status="primary",
        page_or_table="Menon 2025 Table 7 (Total row)", notes="UP, MP, Bihar not included")
    # ---- Bihar SmartVA (Dandona 2018)
    row(state="Bihar", state_as_printed="Bihar", geography_level="state", ref_start="2012-01-01", ref_end="2014-03-31",
        period_type="27 months (annualised rate)", source="SmartVA-Bihar", source_detail="representative household VA, SmartVA algorithm",
        vintage="published", deaths=47, rate_per_100k="4.4 (95% CI 4.3-4.6)",
        denominator_note="627,658 population in 1,017 clusters (sample)", status="primary",
        page_or_table="Dandona 2018 PLoS One 13:e0198900, Table 2 (Snakebite N = 47) and Abstract",
        notes="deaths = study deaths in the sample, not a state total; rate adjusted for age, sex and urban-rural distribution")
    # ---- Tamil Nadu IHIP study (Subhashini 2026; abstract only)
    row(state="Tamil Nadu", state_as_printed="Tamil Nadu", geography_level="state", ref_start="2022-01-01", ref_end="2025-05-31",
        period_type="41 months, cumulative", source="IHIP", source_detail="IDSP-IHIP reported snakebite deaths (state study, VA for 40)",
        vintage="published", deaths=100, cases=56664, rate_per_100k="0.14 (ASMR)", status="primary (abstract)",
        page_or_table="Subhashini 2026 Trans R Soc Trop Med Hyg trag092, Abstract", notes="CFR 0.18%; full text paywalled")
    # ---- Karnataka HMIS (Dodda Basava 2026; abstract only; incidence, no deaths)
    for fy, inc in [(2018, "24.57"), (2019, "24.49")]:
        row(state="Karnataka", state_as_printed="Karnataka", geography_level="state", year=fy,
            ref_start=f"{fy}-04-01", ref_end=f"{fy + 1}-03-31", period_type="financial year", source="HMIS-Karnataka",
            source_detail="HMIS reported snakebite cases (incidence only)", vintage="published",
            rate_per_100k=f"{inc} (INCIDENCE of reported bites, not mortality)", status="primary (abstract)",
            page_or_table="Dodda Basava 2026 Wilderness Environ Med 37:341, Abstract",
            notes="no deaths reported in abstract; full text paywalled")
    # ---- Telangana, Jagtial (Kiran 2026)
    row(state="Telangana", state_as_printed="Jagtial district", geography_level="district", district="Jagtial",
        ref_start="2010-01-01", ref_end="2020-12-31", period_type="11 years, cumulative recall", source="Survey-Jagtial",
        source_detail="community snowball survey of victims/kin", vintage="published", deaths=69,
        rate_per_100k="1.07 per year age-adjusted (95% CI 0.73-1.20)", denominator_note="district population 985,417 (Census 2011)",
        status="primary", page_or_table="Kiran 2026 Toxins 18:250, Results 2.4 and Tables 2-3",
        notes="69 deaths among 541 victims; snowball sample, so the count is a lower bound for the district")
    row(state="Telangana", state_as_printed="Jagtial district", geography_level="district", district="Jagtial",
        ref_start="2015-01-01", ref_end="2020-12-31", period_type="6 years", source="Survey-Jagtial",
        source_detail="community survey, crude mortality", vintage="published", rate_per_100k="5.94 (CI 4.20-8.15) crude, cumulative 2015-20",
        status="primary", page_or_table="Kiran 2026 Results 2.1", notes="paired with the district-hospital row below")
    row(state="Telangana", state_as_printed="Jagtial district", geography_level="district", district="Jagtial",
        ref_start="2015-01-01", ref_end="2020-12-31", period_type="6 years", source="Hospital-Jagtial",
        source_detail="district hospital registers", vintage="published", rate_per_100k="1.01 (CI 0.49-1.87) crude, cumulative 2015-20",
        status="primary", page_or_table="Kiran 2026 Results 2.1", notes="hospital catchment may include other districts (authors' caveat)")
    # ---- West Bengal surveys
    row(state="West Bengal", state_as_printed="South 24 Parganas (8 blocks)", geography_level="district", district="South 24 Parganas (8 blocks)",
        ref_start="2007-01-01", ref_end="2010-10-31", period_type="2-year recall before Jan 2009-Oct 2010 survey (approximate)",
        source="Survey-South24Parganas", source_detail="door-to-door community survey of 1.9 million", vintage="published",
        cases=4871, status="primary (abstract)", page_or_table="Majumder 2014 Indian J Public Health 58:17, Abstract",
        notes="deaths not given in abstract; only 7.23% of deaths officially reported (see completeness_anchors.csv)")
    row(state="West Bengal", state_as_printed="Burdwan district (26 villages)", geography_level="district", district="Burdwan (sample of 26 villages)",
        ref_start="1980-01-01", ref_end="1989-12-31", period_type="10 years", source="Survey-Burdwan",
        source_detail="village household survey, population 18,892", vintage="published", deaths=31, cases=307,
        rate_per_100k="16.4 average (range 5.28-31.75)", status="primary (abstract)",
        page_or_table="Hati 1992 J Indian Med Assoc 90:145, Abstract", notes="historical; sample counts")
    # ---- Kerala
    row(state="Kerala", state_as_printed="Kerala", geography_level="state", ref_start="2024-01-01", ref_end="2025-12-31",
        period_type="'2024-25' (exact months not stated)", source="ICMR-NTF", source_detail="statement in Discussion; underlying source not named",
        vintage="published", deaths=31, status="primary (statement)", page_or_table="Menon 2025 Nat Commun, Discussion",
        notes="the source compares this with an MDS-implied 2,100 using a national rate; MDS's own Kerala rate was 0.5/100k (2010-14)")
    for lab, fy, d in [("2018-19", 2018, 123), ("2020-21", 2020, 52), ("2021-22", 2021, 65)]:
        row(state="Kerala", state_as_printed="Kerala", geography_level="state", year=fy, ref_start=f"{fy}-04-01", ref_end=f"{fy + 1}-03-31",
            period_type="financial year (assumed from 'YYYY-YY' label)", source="Compensation-Kerala-Forest",
            source_detail="Kerala Forest Department compensated snakebite deaths", vintage="published", deaths=d,
            status="secondary-only (quoted in Menon 2026 Trop Med Health 54:112)", page_or_table="Menon 2026, Introduction",
            notes=f"printed '{lab}'; departmental data not seen")
    row(state="Kerala", state_as_printed="Kerala", geography_level="state", year=2025, period_type="calendar year (as printed '2025')",
        source="Compensation-Kerala-Forest", source_detail="Kerala Forest Department compensated snakebite deaths", vintage="published",
        deaths=34, status="secondary-only (quoted in Menon 2026)", page_or_table="Menon 2026, Introduction", notes="")
    # ---- IHIP national and state figures from Parliament (secondary only)
    for y, d, note in [(2023, 183, "86,294 cases"), (2024, 375, "120,982 cases (Rajya Sabha); Lok Sabha figure 370"),
                       (2025, 429, "140,302 cases (Rajya Sabha); Lok Sabha figure 431")]:
        row(state=INDIA, state_as_printed="India", geography_level="national", year=y, period_type="calendar year",
            source="IHIP", source_detail="IDSP-IHIP figures tabled in Parliament", vintage="parliament reply",
            preferred=0, deaths=d, status="secondary-only (South First / Kashmir Life / Newsmeter news reports)",
            page_or_table="Rajya Sabha / Lok Sabha unstarred replies (eparlib.sansad.in AU768, AU1060) - not reachable", notes=note)
    row(state=INDIA, state_as_printed="India", geography_level="national", year=2024, period_type="calendar year", source="IHIP",
        source_detail="IDSP-IHIP, reported by NCDC authors", vintage="published", deaths=370, cases="over 1.20 lakh (as printed)",
        status="primary", page_or_table="Shewale 2025 Trop Med Infect Dis 10:132, Introduction para 2",
        notes="'In 2024, over 1.20 Lakhs cases were reported, with 370 deaths.'")
    for st, y, d in [("Karnataka", 2025, 160), ("West Bengal", 2025, 65), ("Andhra Pradesh", 2025, 13),
                     ("Jammu & Kashmir", 2024, 18), ("Jammu & Kashmir", 2025, 8), ("Kerala", 2023, 0), ("Kerala", 2024, 1),
                     ("Kerala", 2025, 2), ("Telangana", 2023, 0), ("Telangana", 2024, 0), ("Telangana", 2025, 0)]:
        row(state=st, state_as_printed=st, geography_level="state", year=y, period_type="calendar year", source="IHIP",
            source_detail="IDSP-IHIP figures tabled in Parliament", vintage="parliament reply", deaths=d,
            status="secondary-only (news reports of parliamentary replies)", page_or_table="eparlib.sansad.in replies - not reachable",
            notes="verify against the primary reply before use")


# --------------------------------------------------------------------------------------------
# 6. Population (Technical Group 2019, Table 11, 1 July)
# --------------------------------------------------------------------------------------------
POP_PAGES = {  # PDF page (1-based): column units left to right, as printed
    86: ["INDIA", "JAMMU & KASHMIR (UT)", "HIMACHAL PRADESH"], 87: ["PUNJAB", "HARYANA", "NCT OF DELHI"],
    88: ["RAJASTHAN", "UTTAR PRADESH", "BIHAR"], 89: ["ASSAM", "WEST BENGAL", "JHARKHAND"],
    90: ["ODISHA", "CHHATTISGARH", "MADHYA PRADESH"], 91: ["GUJARAT", "MAHARASHTRA", "ANDHRA PRADESH"],
    92: ["KARNATAKA", "KERALA", "TAMIL NADU"], 93: ["CHANDIGARH", "UTTARAKHAND", "SIKKIM"],
    94: ["ARUNACHAL PRADESH", "NAGALAND", "MANIPUR"], 95: ["MIZORAM", "TRIPURA", "MEGHALAYA"],
    96: ["DAMAN & DIU", "DADRA & NAGAR HAVELI", "GOA"], 97: ["LAKSHADWEEP", "PUDUCHERRY", "ANDAMAN & NICOBAR ISLANDS"],
    98: ["TELANGANA", "LADAKH"],
}


def build_population():
    doc = fitz.open(POP_PDF)
    pop = {}
    for pg, units in POP_PAGES.items():
        text = doc[pg - 1].get_text()
        assert "TABLE" in text and "1st July" in text, pg
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        printed_page = lines[0]
        flat = " ".join(lines).upper().replace("ANDAMAN & NICOBAR ISLANDS", "ANDAMAN & NICOBAR ISLANDS")
        for u in units:
            assert u.split()[0] in flat, (pg, u)
        toks = lines
        i = next(j for j, t in enumerate(toks) if t == "2011")
        k = len(units)
        while i < len(toks) and re.fullmatch(r"20[1-3]\d", toks[i]):
            yr = int(toks[i])
            vals = [int(x.replace(",", "")) for x in toks[i + 1:i + 1 + 3 * k]]
            for j, u in enumerate(units):
                pop[(u, yr)] = (vals[3 * j], vals[3 * j + 1], vals[3 * j + 2], printed_page, pg)
            i += 1 + 3 * k
    units_all = [u for us in POP_PAGES.values() for u in us if u != "INDIA"]
    rows = []
    for yr in range(2011, 2025):
        india = pop[("INDIA", yr)][0]
        s = sum(pop[(u, yr)][0] for u in units_all)
        # The 38 units fall short of the printed India total by 24-38 thousand every year (<0.003%).
        # Rounding of 38 cells could explain at most +/-19; the report does not explain the gap.
        tag = "OK" if s == india else ("DIFF-SMALL" if abs(s - india) <= 40 else "MISMATCH")
        log(f"[{tag}] Population {yr}: sum of 38 units {s} vs printed India {india} ('000; diff {s - india})")
        for u in units_all:
            p, m, f = pop[(u, yr)][:3]
            if abs(m + f - p) > 1:
                log(f"[MISMATCH] Population {yr} {u}: M+F {m + f} vs persons {p}")
    pmap = {"JAMMU & KASHMIR (UT)": "Jammu & Kashmir", "NCT OF DELHI": "Delhi", "DAMAN & DIU": DD,
            "DADRA & NAGAR HAVELI": DNH, "ANDAMAN & NICOBAR ISLANDS": "Andaman & Nicobar Islands"}
    for (u, yr), (p, m, f, pp, pg) in sorted(pop.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if yr > 2024:
            continue
        st = INDIA if u == "INDIA" else pmap.get(u, u.title().replace(" And ", " and "))
        if st not in CANON + [INDIA, DD, DNH]:
            st = canon(u, "TechnicalGroup", 2024)
        MAPPING[("TechnicalGroup2019", u, st)] = ""
        rows.append(dict(state=st, year=yr, population=p * 1000, male=m * 1000, female=f * 1000, unit="persons (printed in '000)",
                         reference_date=f"{yr}-07-01", status="primary", source_table=f"Table 11, p.{pp} (PDF p.{pg})", notes=""))
    # derived aggregates
    def agg(name, parts, note):
        for yr in range(2011, 2025):
            vals = [next(r for r in rows if r["state"] == p and r["year"] == yr) for p in parts]
            rows.append(dict(state=name, year=yr, population=sum(v["population"] for v in vals),
                             male=sum(v["male"] for v in vals), female=sum(v["female"] for v in vals),
                             unit="persons", reference_date=f"{yr}-07-01", status="derived (sum)",
                             source_table="Table 11 (sum of units)", notes=note))
    agg(DNHDD, [DNH, DD], "merged UT (26 Jan 2020) = DNH + Daman & Diu")
    agg(JK_UNDIV, ["Jammu & Kashmir", "Ladakh"], "former J&K state = J&K (UT) + Ladakh, for sources before 2020")
    agg(AP_UNDIV, ["Andhra Pradesh", "Telangana"], "undivided AP, for MDS (2001-14) and earlier sources")
    agg(NE7, ["Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"], "MDS 'Northeastern states' group")
    fields = ["state", "year", "population", "male", "female", "unit", "reference_date", "status", "source_table", "notes"]
    with open(OUT / "state_population.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    log(f"wrote state_population.csv: {len(rows)} rows")


# --------------------------------------------------------------------------------------------
# 7. Completeness anchors
# --------------------------------------------------------------------------------------------
def build_completeness():
    A = []
    fields = ["anchor_id", "system_measured", "measured_against", "geography", "geography_level", "period",
              "numerator", "denominator", "completeness", "numerator_desc", "denominator_desc", "kind", "status",
              "page_or_table", "citation", "doi", "notes"]
    t = bioc_tables("PMC7340498.bioc.json")
    t4 = [r for r in t["table4"] if len(r) == 7 and re.fullmatch(r"[\d\.]+", r[1] or "")]
    for r in t4:
        nm = r[0].strip()
        st = nm if (nm.startswith("Higher") or nm.startswith("Lower") or nm == "India") else (MDS_NAME.get(nm) or canon(nm, "MDS", 2005))
        A.append(dict(anchor_id=f"SUR-T4-{key(nm)[:12]}", system_measured="hospital (government hospital reports to MoHFW)",
                      measured_against="MDS-estimated deaths that occurred in hospital (public + private)", geography=st,
                      geography_level="national" if nm == "India" else ("state-group" if nm.startswith(("Higher", "Lower")) or st in (NE7,) or "other" in nm.lower() else "state"),
                      period="2003-2015 cumulative", numerator=r[2], denominator=r[5], completeness=r[6],
                      numerator_desc="government-reported hospital deaths (thousands)", denominator_desc="MDS in-hospital deaths (thousands)",
                      kind="measured (as printed)", status="primary", page_or_table="Suraweera 2020 Table 4 col (7)",
                      citation=SUR_CIT, doi="10.7554/eLife.54076",
                      notes="denominator excludes out-of-hospital deaths, so completeness vs ALL deaths is lower (multiply by the in-hospital share)"))
    A.append(dict(anchor_id="MAJ-2014", system_measured="hospital/official reporting (health-facility based official data)",
                  measured_against="door-to-door community survey of the same area", geography="South 24 Parganas, West Bengal (8 blocks, 1.9 M)",
                  geography_level="district", period="2 years before Jan 2009-Oct 2010", numerator="", denominator="",
                  completeness="7.23%", numerator_desc="officially reported snakebite deaths", denominator_desc="snakebite deaths found by survey",
                  kind="measured", status="primary (abstract; counts not in abstract)",
                  page_or_table="Abstract: 'Only 7.23% snake bite deaths were officially reported.'",
                  citation="Majumder D, Sinha A, et al. Indian J Public Health 2014;58(1):17-21", doi="10.4103/0019-557X.128158",
                  notes="numerator and denominator need the full text"))
    A.append(dict(anchor_id="KIR-2026", system_measured="hospital (district hospital registers)", measured_against="community snowball survey",
                  geography="Jagtial district, Telangana", geography_level="district", period="2015-2020",
                  numerator="1.01", denominator="5.94", completeness="17% (derived: 1.01/5.94)",
                  numerator_desc="crude snakebite mortality per 100,000 in hospital data", denominator_desc="crude mortality per 100,000 in the community survey",
                  kind="derived ratio of two published rates", status="derived", page_or_table="Kiran 2026 Results 2.1",
                  citation="Kiran S, Srinivas S, Vasudevan K. Toxins 2026;18(6):250", doi="10.3390/toxins18060250",
                  notes="hospital catchment may differ from the survey area; survey is not a probability sample"))
    # MP: paid compensation is a lower bound for true deaths -> NHP/compensation and NCRB/compensation are UPPER bounds on completeness
    A.append(dict(anchor_id="MP-NHP-2021", system_measured="hospital (NHP, ICD-10 T63.0)", measured_against="paid compensation claims (lower bound of true deaths)",
                  geography="Madhya Pradesh", geography_level="state", period="NHP calendar 2021 vs compensation FY2021-22",
                  numerator="5", denominator="2760", completeness="0.18% (derived upper bound)",
                  numerator_desc="NHP 2023 Table 3.2.3(A) MP deaths 2021", denominator_desc="Kadam 2025 Table 1 compensated deaths FY2021-22",
                  kind="upper bound (derived; periods offset by 3 months)", status="derived",
                  page_or_table="NHP 2023 p.153; Kadam 2025 Table 1", citation="CBHI NHP 2023; Kadam P et al. Trans R Soc Trop Med Hyg 2025;119:158",
                  doi="10.1093/trstmh/trae045", notes=""))
    A.append(dict(anchor_id="MP-NCRB-2021", system_measured="police (NCRB ADSI)", measured_against="paid compensation claims (lower bound of true deaths)",
                  geography="Madhya Pradesh", geography_level="state", period="NCRB calendar 2021 vs compensation FY2021-22",
                  numerator="2732", denominator="2760", completeness="99% (derived upper bound)",
                  numerator_desc="NCRB ADSI 2021 MP snake-bite deaths", denominator_desc="Kadam 2025 Table 1 compensated deaths FY2021-22",
                  kind="upper bound (derived; periods offset by 3 months)", status="derived",
                  page_or_table="ADSI 2021 Table 1.10 p.96; Kadam 2025 Table 1", citation="NCRB ADSI 2021; Kadam 2025", doi="10.1093/trstmh/trae045",
                  notes="compensation requires a postmortem, so most compensated deaths should also pass through police inquest"))
    A.append(dict(anchor_id="MP-NCRB-2020", system_measured="police (NCRB ADSI)", measured_against="paid compensation claims (lower bound of true deaths)",
                  geography="Madhya Pradesh", geography_level="state", period="NCRB calendar 2020 vs compensation FY2020-21",
                  numerator="2512", denominator="3019", completeness="83% (derived upper bound)",
                  numerator_desc="NCRB ADSI 2020 MP snake-bite deaths", denominator_desc="Kadam 2025 Table 1 compensated deaths FY2020-21",
                  kind="upper bound (derived; periods offset by 3 months)", status="derived",
                  page_or_table="ADSI 2020 Table 1.10 p.96; Kadam 2025 Table 1", citation="NCRB ADSI 2020; Kadam 2025", doi="10.1093/trstmh/trae045", notes=""))
    # place-of-death ceilings for facility-based systems
    t2 = bioc_tables("PMC3075236.bioc.json")
    tab = next(v for v in t2.values() if any(r and r[0] == "Sub total" for r in v))
    for r in [x for x in tab if len(x) == 7 and re.fullmatch(r"[\d,]+/[\d,]+", x[1])]:
        n = int(r[1].split("/")[0].replace(",", "")); out = int(r[3])
        A.append(dict(anchor_id=f"MOH-T2-{key(r[0])[:12]}", system_measured="any facility-based system (hospital, MCCD, NHP, IHIP)",
                      measured_against="all VA snakebite deaths", geography=MDS_NAME.get(r[0], r[0] if r[0] in ("Sub total", "Remaining states", "All India") else canon(r[0], "MDS", 2005)),
                      geography_level="national" if r[0] == "All India" else ("state-group" if r[0] in ("Sub total", "Remaining states") else "state"),
                      period="2001-2003 study deaths", numerator=str(n - out), denominator=str(n),
                      completeness=f"{100 * (n - out) / n:.1f}% (derived ceiling)", numerator_desc="VA snakebite deaths that did NOT occur outside a health facility",
                      denominator_desc="VA snakebite deaths in sample", kind="ceiling (place-of-death share; small n)", status="derived",
                      page_or_table="Mohapatra 2011 Table 2 ('Died outside health facility')",
                      citation="Mohapatra B et al. PLoS Negl Trop Dis 2011;5(4):e1018", doi="10.1371/journal.pntd.0001018",
                      notes="a facility-based system cannot exceed this share unless it records deaths after discharge or brought dead"))
    A.append(dict(anchor_id="SUR-OOH", system_measured="any facility-based system", measured_against="all VA snakebite deaths", geography=INDIA,
                  geography_level="national", period="2001-2014", numerator="", denominator="", completeness="23% (derived from '77% occurred out of hospital')",
                  numerator_desc="", denominator_desc="", kind="ceiling (place-of-death share)", status="derived",
                  page_or_table="Suraweera 2020 Results: 'About 94% of snakebite deaths occurred in rural areas, and 77% occurred out of hospital'",
                  citation=SUR_CIT, doi="10.7554/eLife.54076", notes=""))
    A.append(dict(anchor_id="MEN-OOH", system_measured="any facility-based system", measured_against="deaths found by ICMR community surveillance",
                  geography="25 districts in 11 states", geography_level="multi-district", period="12 months per site, 2022-25",
                  numerator="", denominator="195", completeness="56.9% (as printed: deaths in hospital settings)",
                  numerator_desc="deaths in hospital settings", denominator_desc="all deaths recorded", kind="ceiling (place-of-death share)",
                  status="primary", page_or_table="Menon 2025 Results and Table 4 ('outside hospital (43.1%) and hospital settings (56.9%)')",
                  citation="Menon JC et al. Nat Commun 2025;16:9871", doi="10.1038/s41467-025-64849-2", notes=""))
    with open(OUT / "completeness_anchors.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(A)
    log(f"wrote completeness_anchors.csv: {len(A)} rows")


def main():
    build_ncrb()
    build_nhp()
    build_mccd()
    build_mds()
    build_anchors()
    for r in PANEL:
        if r["geography_level"] == "state" and r["state"] not in CANON + [AP_UNDIV, JK_UNDIV]:
            raise ValueError(f"non-canonical state in panel: {r['state']} ({r['source']})")
    with open(OUT / "state_year_source_panel.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=PANEL_FIELDS); w.writeheader(); w.writerows(PANEL)
    log(f"wrote state_year_source_panel.csv: {len(PANEL)} rows")
    build_population()
    build_completeness()
    with open(OUT / "state_name_mapping.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["source", "name_as_printed", "canonical_unit", "note"])
        for (s, raw, c), note in sorted(MAPPING.items()):
            w.writerow([s, raw, c, note])
    (OUT / "panel_validation_log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    nmis = sum(1 for l in LOG if l.startswith("[MISMATCH]"))
    print(f"validation: {sum(1 for l in LOG if l.startswith('[OK]'))} OK, {sum(1 for l in LOG if l.startswith('[OK-ROUNDING]'))} OK-ROUNDING, {sum(1 for l in LOG if l.startswith('[DIFF-SMALL]'))} DIFF-SMALL, {nmis} MISMATCH")


if __name__ == "__main__":
    main()
