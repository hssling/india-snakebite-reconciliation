"""Model inputs for the snakebite reconciliation model: 20 analytic units that tile India.

The units are the ones for which the Million Death Study (MDS; Suraweera et al. 2020, Table 3) prints state rates:
18 named states (undivided Andhra Pradesh = AP + Telangana; former J&K state = J&K + Ladakh), the seven north-eastern
states other than Assam (NE-7, incl. Sikkim), and "all other states" (the remaining states and UTs). Government series
(NCRB, MCCD, NHP) printed for the 36 current units are summed to these 20 units.

Writes data/model/:
  units.csv            unit, members, population by year 2014-2024
  gov_obs.csv          source, unit, year, deaths (preferred vintage only; a unit-year is kept only if every member reported)
  mds_obs.csv          unit, period, years, ASR per 100k, study deaths 2001-14, approx study deaths in the period
  icmr_obs.csv         ICMR task-force districts: unit, district, deaths, district population (2024)
  anchors_obs.csv      Madhya Pradesh paid compensation (lower bound on true deaths)
Checks: unit populations sum to the sum of the 36 printed units; summed government deaths equal the printed
national totals wherever every unit reported.
"""
import pathlib, re
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
OUT = P / "data/model"; OUT.mkdir(exist_ok=True)
panel = pd.read_csv(P / "data/state_year_source_panel.csv")
pop = pd.read_csv(P / "data/state_population.csv")
YEARS = list(range(2014, 2025))

UAP, UJK = "Andhra Pradesh + Telangana (undivided AP)", "Jammu & Kashmir + Ladakh (former J&K state)"
NE7 = "NE-7 (Arunachal, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, Tripura)"
OTHER = "MDS residual group: all other states"
NAMED = ["Assam", "Bihar", "Chhattisgarh", "Gujarat", "Haryana", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
         "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Uttar Pradesh", "West Bengal"]
MEMBERS = {**{s: [s] for s in NAMED},
           UAP: ["Andhra Pradesh", "Telangana"],
           UJK: ["Jammu & Kashmir", "Ladakh"],
           NE7: ["Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Sikkim", "Tripura"],
           OTHER: ["Andaman & Nicobar Islands", "Chandigarh", "Dadra & Nagar Haveli and Daman & Diu", "Delhi", "Goa",
                   "Himachal Pradesh", "Lakshadweep", "Puducherry", "Uttarakhand"]}
UNITS = sorted(MEMBERS, key=lambda u: (u in (NE7, OTHER), u))
CURRENT = [m for u in UNITS for m in MEMBERS[u]]
assert len(CURRENT) == 36 == len(set(CURRENT))
TO_UNIT = {m: u for u, ms in MEMBERS.items() for m in ms}
TO_UNIT[UJK] = UJK                                                    # pre-2020 sources print the former state

# ---- population: sum of the 36 current units (no derived rows), every year ----
pp = pop[pop.state.isin(CURRENT) & pop.year.isin(YEARS)].pivot(index="state", columns="year", values="population")
assert pp.shape == (36, len(YEARS)) and not pp.isna().any().any(), pp.shape
upop = pd.DataFrame({u: pp.loc[MEMBERS[u]].sum() for u in UNITS}).T
assert np.allclose(upop.sum(), pp.sum())
units = upop.copy(); units.columns = [f"pop_{y}" for y in YEARS]
units.insert(0, "members", ["; ".join(MEMBERS[u]) for u in UNITS])
units.index.name = "unit"; units.to_csv(OUT / "units.csv")

# ---- government series ----
g = panel[panel.source.isin(["NCRB", "MCCD", "NHP"]) & (panel.preferred == 1) & panel.year.isin(YEARS)
          & panel.status.str.startswith(("primary", "derived"))].copy()
nat = g[g.geography_level == "national"].set_index(["source", "year"]).deaths
g = g[g.geography_level == "state"].copy()
g["unit"] = g.state.map(TO_UNIT)
assert g.unit.notna().all(), g[g.unit.isna()].state.unique()
dup = g.groupby(["source", "year", "state"]).size()
assert (dup == 1).all(), dup[dup > 1]
rows, log = [], []
for (src, yr), d in g.groupby(["source", "year"]):
    have = set(d.state)
    if UJK in have: have |= {"Jammu & Kashmir", "Ladakh"}
    for u in UNITS:
        dd = d[d.unit == u]
        complete = set(MEMBERS[u]) <= have and dd.deaths.notna().all()
        if complete:
            rows.append(dict(source=src, unit=u, year=int(yr), deaths=int(dd.deaths.sum())))
    tot = d.deaths.sum(); full = all(set(MEMBERS[u]) <= have for u in UNITS) and d.deaths.notna().all()
    log.append(f"{src} {int(yr)}: units {sum(1 for r in rows if r['source'] == src and r['year'] == yr)}/20; "
               f"sum {tot:,.0f} vs printed national {nat.get((src, yr), np.nan):,.0f}" + ("" if full else " (incomplete year)"))
    if full and src != "NHP":                                         # NHP 2018 final prints an inconsistent total
        assert tot == nat[(src, yr)], (src, yr, tot, nat[(src, yr)])
gov = pd.DataFrame(rows); gov.to_csv(OUT / "gov_obs.csv", index=False)

# ---- MDS period ASRs (Suraweera Table 3) ----
m = panel[(panel.source == "MDS") & panel.rate_per_100k.notna() & panel.ref_start.isin(["2001-01-01", "2005-01-01", "2010-01-01"])
          & panel.ref_end.isin(["2004-12-31", "2009-12-31", "2014-12-31"])].copy()
m = m[m.state.isin(UNITS)]
m["period"] = m.ref_start.str[:4] + "-" + m.ref_end.str[:4]
m["y0"] = m.ref_start.str[:4].astype(int); m["y1"] = m.ref_end.str[:4].astype(int)
m["asr"] = m.rate_per_100k.astype(float)
m["n_total"] = m.notes.str.extract(r"study deaths 2001-14 = (\d+)")[0].astype(float)
assert set(m.state) == set(UNITS) and len(m) == 60, (len(m), set(UNITS) - set(m.state))
w = m.asr * (m.y1 - m.y0 + 1)                                        # allocate study deaths to periods by rate x years
m["n_period"] = m.n_total * w / w.groupby(m.state).transform("sum")
mds = m.rename(columns={"state": "unit"})[["unit", "period", "y0", "y1", "asr", "n_total", "n_period"]].sort_values(["unit", "y0"])
mds.to_csv(OUT / "mds_obs.csv", index=False)

# ---- ICMR task-force districts (12 months within 2022-25) ----
ic = panel[(panel.source == "ICMR-NTF") & (panel.geography_level == "district")].copy()
ic["district_pop"] = ic.denominator_note.str.extract(r"district population (\d+)")[0].astype(float)
ic["unit"] = ic.state.map(TO_UNIT)
ic = ic[ic.deaths.notna()][["unit", "state", "district", "deaths", "district_pop"]]
pooled = panel[(panel.source == "ICMR-NTF") & (panel.geography_level == "multi-district")].deaths.iloc[0]
assert ic.deaths.sum() == pooled == 195, (ic.deaths.sum(), pooled)
ic.to_csv(OUT / "icmr_obs.csv", index=False)

# ---- Madhya Pradesh compensation (paid claims; a lower bound on true deaths), financial years -> calendar ----
mp = panel[panel.source == "Compensation-MP"][["state", "year", "ref_start", "ref_end", "deaths"]].copy()
assert sorted(mp.deaths) == [2760, 3019]
mp.to_csv(OUT / "anchors_obs.csv", index=False)

print("\n".join(log))
print(f"units {len(UNITS)} | gov obs {len(gov)} ({gov.groupby('source').size().to_dict()}) | MDS {len(mds)} | ICMR districts {len(ic)} "
      f"({int(ic.deaths.sum())} deaths, {ic.district_pop.sum() / 1e6:.1f} M) | population 2024 {upop[2024].sum() / 1e6:,.1f} M")
