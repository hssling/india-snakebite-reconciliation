"""Recompute every number reported in the paper from outputs/ (and the posterior draws); exit 1 on any failure."""
import json, pathlib, sys
import numpy as np, pandas as pd
R = pathlib.Path(__file__).resolve().parent; O = R / "outputs"
E = json.loads((R / "results/expected_key_results.json").read_text())
fails, n = [], 0


def check(name, got, want, tol):
    global n; n += 1; ok = abs(got - want) <= tol
    print(f"{'PASS' if ok else 'FAIL'}  {name:72s} got {got:12.4f}  expected {want:12.4f}")
    if not ok: fails.append(name)


units = pd.read_csv(R / "data/model/units.csv").set_index("unit"); U = list(units.index)
pop = units[[f"pop_{y}" for y in range(2014, 2025)]].to_numpy(float)
check("population 2024 (millions), 20 units", pop[:, -1].sum() / 1e6, E["population_2024_millions"], 0.051)
draws = {S: np.load(O / f"draws_{S}.npz") for S in ("S0", "S1", "S2", "S3", "S4", "S5", "S6")}
nat = {S: (z["lam_2014_2024"] * pop[None] / 1e5).sum(1) for S, z in draws.items()}
for k, w in E["deaths"].items():
    S, y = k.split("|"); v = nat[S][:, int(y) - 2014]
    for lab, q, x in zip(("median", "lo", "hi"), (50, 2.5, 97.5), w): check(f"deaths {k} {lab} (from draws, nearest 10)", round(np.percentile(v, q), -1), x, 10)
for S, w in E["annual_change_after_2014_pct"].items():
    z = draws[S]; sl = z["B"] + (z["D"] if "D" in z else 0)
    for lab, q, x in zip(("median", "lo", "hi"), (50, 2.5, 97.5), w): check(f"annual change after 2014 {S} {lab}", np.percentile(100 * np.expm1(sl), q), x, 0.051)
for S, grp in (("S0", "completeness_national_S0"), ("S4", "completeness_national_S4")):
    cn = pd.read_csv(O / f"completeness_national_{S}.csv").set_index(["source", "year"])
    for k, w in E[grp].items():
        s, y = k.split("|"); r = cn.loc[(s, int(y))]; tol = 0.051 if isinstance(w[0], float) else 0.51
        for lab, col, x in zip(("median", "lo", "hi"), ("c_pct", "lo", "hi"), w): check(f"completeness {S} {k} {lab}", r[col], x, tol)
an = {S: pd.read_csv(O / f"anchors_check_{S}.csv") for S in ("S0", "S3", "S4")}
row = {"IHIP": 0, "ICMR": 1, "MP FY2020-21": 2, "MP FY2021-22": 3}
for k, w in E["anchors"].items():
    S, a = k.split("|"); r = an[S].iloc[row[a]]; tol = 0.0051 if a == "IHIP" else (0.051 if isinstance(w[0], float) else 0.51)
    for lab, col, x in zip(("median", "lo", "hi"), ("c_pct", "lo", "hi"), w): check(f"anchor {k} {lab}", r[col], x, tol)
for i, x in enumerate(E["p_true_below_claims_S0"]): check(f"P(true < claims) S0 FY{i}", an["S0"].iloc[2 + i].p_true_below_claims, x, 0.0051)
for k, w in E["anchor_parameters_S4"].items():
    for lab, q, x in zip(("median", "lo", "hi"), (50, 2.5, 97.5), w): check(f"S4 {k} {lab}", np.percentile(draws["S4"][k], q), x, 0.0051)
dr = pd.read_csv(O / "completeness_drift_S0.csv").set_index("source")
check("NCRB national completeness drift, % per year", dr.loc["NCRB", "national_trend_pct_per_year"], E["ncrb_drift_pct_per_year"], 0.051)
Ed = nat["S0"][:, -1]; Eu = draws["S0"]["lam_2014_2024"][:, :, -1] * pop[None, :, -1] / 1e5
for s, w in E["states_2024"].items():
    v = Eu[:, U.index(s)]
    for lab, q, x in zip(("median", "lo", "hi"), (50, 2.5, 97.5), w): check(f"deaths 2024 {s} {lab}", round(np.percentile(v, q), -1), x, 10)
top5 = np.argsort(-np.median(Eu, 0))[:5]                                       # shares computed within each draw
for lab, sh, w in (("Uttar Pradesh + Bihar", (Eu[:, U.index("Uttar Pradesh")] + Eu[:, U.index("Bihar")]) / Eu.sum(1), E["share_up_bihar_pct"]),
                   ("five largest units", Eu[:, top5].sum(1) / Eu.sum(1), E["share_top5_pct"])):
    for ql, q, x in zip(("median", "lo", "hi"), (50, 2.5, 97.5), w): check(f"share of deaths 2024, {lab} {ql} (%)", np.percentile(100 * sh, q), x, 0.51)
cu = pd.read_csv(O / "completeness_unit_year_S0.csv").set_index(["source", "unit", "year"])
for k, x in E["ncrb_state_completeness"].items():
    s, y = k.split("|"); check(f"NCRB completeness {k}", cu.loc[("NCRB", s, int(y)), "c_pct"], x, 0.051)
N = E["napse"]; base = pd.read_csv(O / "napse_baselines.csv").set_index("baseline")
check("required annual change for halving by 2030 (%)", 100 * (0.5 ** (1 / 6) - 1), N["required_pct_per_year"], 0.051)
check("2030 target, IHIP baseline", base.target_2030.iloc[0], N["targets_2030"]["IHIP"], 0.51)
check("2030 target, NCRB baseline (nearest 100)", round(base.target_2030.iloc[3], -2), N["targets_2030"]["NCRB"], 0.5)
check("2030 target, reconciled S0 (nearest 100)", round(base.target_2030.iloc[4], -2), N["targets_2030"]["S0"], 0.5)
m = pd.read_csv(O / "napse_monitoring.csv")
pick = lambda sys_, d: m[(m.system.str.startswith(sys_)) & (m.drift == d)].iloc[0]
r = pick("NCRB", "drift continues")
for lab, col, x in zip(("median", "lo", "hi"), ("obs_change_if_target_met", "target_lo", "target_hi"), N["NCRB continues|target"]): check(f"NCRB drift continues, target met, {lab}", r[col], x, 0.51)
check("NCRB drift continues, business as usual", r.obs_change_if_bau, N["NCRB continues|bau"], 0.51)
check("NCRB drift continues, P(on track | target met)", r.p_declare_on_track_if_target_met, N["NCRB continues|on_track_if_met"], 0.0051)
check("NCRB drift stops, AUC", pick("NCRB", "drift stops").auc_target_vs_bau, N["NCRB stops|auc"], 0.0051)
check("MCCD AUC", pick("MCCD", "drift continues").auc_target_vs_bau, N["MCCD continues|auc"], 0.0051)
check("MCCD P(on track | BAU)", pick("MCCD", "drift continues").p_declare_on_track_if_bau, N["MCCD continues|on_track_if_bau"], 0.0051)
check("NHP AUC", pick("NHP", "drift continues").auc_target_vs_bau, N["NHP continues|auc"], 0.0051)
check("NHP P(on track | BAU)", pick("NHP", "drift continues").p_declare_on_track_if_bau, N["NHP continues|on_track_if_bau"], 0.0051)
check("IHIP P(rise | target met)", pick("IHIP", "drift continues").p_shows_rise_if_target_met, N["IHIP continues|rise_if_met"], 0.0051)
for S, key in (("S0", "SRS S0"), ("S4", "SRS S4")):
    r = m[m.system.str.contains(f"SRS.*{S}")].iloc[0]
    check(f"SRS deaths per year ({S}, nearest 10)", round(r.expected_srs_deaths_per_year, -1), N[f"{key}|deaths_per_year"], 0.5)
    check(f"SRS P(on track | target met) {S}", r.p_declare_on_track_if_target_met, N[f"{key}|on_track_if_met"], 0.0051)
    check(f"SRS P(on track | BAU) {S} below 1%", min(r.p_declare_on_track_if_bau, N["SRS|on_track_if_bau_max"]), r.p_declare_on_track_if_bau, 0)
dg = json.loads((O / "model_diagnostics.json").read_text())
for S, d in dg.items():
    check(f"{S} max R-hat <= 1.01", min(d["max_rhat"], E["mcmc"]["max_rhat"]), d["max_rhat"], 0)
    check(f"{S} divergences", d["divergences"], E["mcmc"]["divergences"], 0)
print(f"\n{n - len(fails)}/{n} checks passed"); sys.exit(1 if fails else 0)
