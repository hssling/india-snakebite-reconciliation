"""Completeness of each recording system = recorded deaths / true deaths, from the true-rate draws (cut design).

For every posterior draw of lambda (reconcile_model.py) and every source-unit-year, completeness
c = y* / (lambda * pop / 1e5), with y* ~ Gamma(y + 0.5, 1) to carry Poisson uncertainty in the recorded count.
Also:
  * national completeness by source and year (sum over units reporting in that year)
  * IHIP 2024 (370 deaths, national), ICMR task-force districts (195 deaths) and Madhya Pradesh paid compensation
    (FY2020-21 3,019; FY2021-22 2,760) set against expected deaths
  * completeness drift: per source, the trend (% per year) in national completeness (all years held) and the volatility
    of unit-level log completeness (SD of residuals from each unit's own linear trend, net of Poisson noise),
    used by the NAPSE monitoring analysis (napse_decision.py)
Writes outputs/completeness_unit_year_<S>.csv, completeness_national_<S>.csv, completeness_drift_<S>.csv,
anchors_check_<S>.csv.
"""
import sys, pathlib
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
D = P / "data/model"; O = P / "outputs"
units = pd.read_csv(D / "units.csv").set_index("unit"); U = list(units.index)
pop = units[[f"pop_{y}" for y in range(2014, 2025)]].to_numpy(float)
gov = pd.read_csv(D / "gov_obs.csv"); icmr = pd.read_csv(D / "icmr_obs.csv")
rng = np.random.default_rng(20261110)
q = lambda v, ax=0: np.percentile(v, [50, 2.5, 97.5], axis=ax)


def run(S):
    z = np.load(O / f"draws_{S}.npz"); assert list(z["units"]) == U
    lam = z["lam_2014_2024"]; ND = lam.shape[0]
    E = lam * pop[None] / 1e5                                                       # draws x NU x 11 expected true deaths
    rows = []
    for r in gov.itertuples():
        e = E[:, U.index(r.unit), r.year - 2014]; c = rng.gamma(r.deaths + 0.5, 1.0, ND) / e
        m, lo, hi = q(100 * c)
        rows.append(dict(source=r.source, unit=r.unit, year=r.year, recorded=r.deaths, expected=np.median(e), c_pct=m, lo=lo, hi=hi))
    uy = pd.DataFrame(rows); uy.to_csv(O / f"completeness_unit_year_{S}.csv", index=False)
    nat = []
    for (src, yr), d in gov.groupby(["source", "year"]):
        ix = [U.index(u) for u in d.unit]; e = E[:, ix, yr - 2014].sum(1)
        c = rng.gamma(d.deaths.sum() + 0.5, 1.0, ND) / e; m, lo, hi = q(100 * c)
        nat.append(dict(source=src, year=yr, units=len(d), recorded=int(d.deaths.sum()), expected=np.median(e),
                        expected_lo=np.percentile(e, 2.5), expected_hi=np.percentile(e, 97.5), c_pct=m, lo=lo, hi=hi))
    nat = pd.DataFrame(nat); nat.to_csv(O / f"completeness_national_{S}.csv", index=False)
    # drift: national completeness trend (log-linear over years with all 20 units) and unit-level volatility
    dr = []
    for src, d in uy.groupby("source"):
        n = nat[nat.source == src]                                                  # all years (expected deaths matched to the units reporting)
        slope = np.polyfit(n.year, np.log(n.c_pct), 1)[0]
        res = []
        for u, du in d.groupby("unit"):
            du = du[du.recorded >= 5]                                               # tiny counts are pure noise
            if len(du) < 4: continue
            lc = np.log(du.recorded / du.expected); fit = np.polyval(np.polyfit(du.year, lc, 1), du.year)
            v = np.var(lc - fit, ddof=2) - np.mean(1 / du.recorded)                # net of Poisson variance
            res.append(dict(unit=u, var=v, w=len(du) - 2))
        res = pd.DataFrame(res); vol = np.sqrt(max(np.average(res["var"], weights=res.w), 0))
        dr.append(dict(source=src, years=f"{int(n.year.min())}-{int(n.year.max())}", national_trend_pct_per_year=100 * np.expm1(slope),
                       unit_volatility_sd_log=vol, units_used=len(res)))
    pd.DataFrame(dr).to_csv(O / f"completeness_drift_{S}.csv", index=False)
    # anchors
    an = []
    e24 = E[:, :, -1].sum(1); c = rng.gamma(370.5, 1.0, ND) / e24; an.append(dict(anchor="IHIP national 2024 (370 deaths)", expected=np.median(e24),
                                                                                  lo_e=np.percentile(e24, 2.5), hi_e=np.percentile(e24, 97.5), **dict(zip(("c_pct", "lo", "hi"), q(100 * c)))))
    lam_ic = 0.5 * (lam[:, :, -2] + lam[:, :, -1])
    eic = sum(lam_ic[:, U.index(r.unit)] * r.district_pop / 1e5 for r in icmr.itertuples())
    c = rng.gamma(icmr.deaths.sum() + 0.5, 1.0, ND) / eic
    an.append(dict(anchor="ICMR task-force districts 2022-25 (195 deaths, 25 districts)", expected=np.median(eic),
                   lo_e=np.percentile(eic, 2.5), hi_e=np.percentile(eic, 97.5), **dict(zip(("c_pct", "lo", "hi"), q(100 * c)))))
    mp = U.index("Madhya Pradesh"); emp = E[:, mp]
    for lab, obs, fy in (("MP paid compensation FY2020-21 (3,019)", 3019, 0.75 * emp[:, 6] + 0.25 * emp[:, 7]),
                         ("MP paid compensation FY2021-22 (2,760)", 2760, 0.75 * emp[:, 7] + 0.25 * emp[:, 8])):
        an.append(dict(anchor=lab, expected=np.median(fy), lo_e=np.percentile(fy, 2.5), hi_e=np.percentile(fy, 97.5),
                       **dict(zip(("c_pct", "lo", "hi"), q(100 * obs / fy))), p_true_below_claims=float((fy < obs).mean())))
    an = pd.DataFrame(an); an.to_csv(O / f"anchors_check_{S}.csv", index=False)
    return uy, nat, pd.DataFrame(dr), an


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    for S in sys.argv[1:] or ["S0"]:
        uy, nat, dr, an = run(S)
        print(f"== {S} ==")
        print(nat.round(1).to_string(index=False)); print(dr.round(3).to_string(index=False)); print(an.round(2).to_string(index=False))
