"""Decision analysis for India's National Action Plan for Prevention and Control of Snakebite Envenoming (NAPSE, 2024):
"halve snakebite deaths by 2030". NAPSE states no numeric baseline. Baseline year here: 2024.

1. Baseline and target under each candidate baseline (official counts vs reconciled estimates, scenarios S0/S3/S4).
2. Required pace: a 50% fall over 2024-2030 = -10.9% per year, against the posterior MDS trend.
3. Monitoring: can each recording system tell whether the target is met? For system k, the observed 2030/2024 ratio is
       R_k = (true ratio) x (completeness ratio) x (Poisson noise),
       log completeness ratio ~ N(6 * mu_k, 6 * sigma_k^2)       mu_k: drift in national completeness per year,
                                                                   sigma_k: year-to-year national volatility,
   both estimated from 2014-2024 under the primary scenario (S0); mu_k uncertainty from its regression SE.
   Two drift assumptions: drift continues at the 2014-24 pace, or drift stops (mu_k = 0, volatility only).
   True trajectories: target met (ratio 0.5); business as usual (MDS trend, posterior of B); no change (ratio 1).
   Reported: median observed change under each truth; P(declaring 'on track', an observed fall >= 40%) when the target is
   met and under business as usual; P(observed rise) when the target is met; AUC = P(observed ratio smaller when the
   target is met than under business as usual), i.e. the system's ability to tell the two apart (0.5 = none, 1 = perfect).
4. A verbal-autopsy alternative: SRS cause-of-death survey (8,839 sample units, more than 8.9 million people; ORGI,
   Causes of Death Statistics 2022-2024, s.1.3.1), which already assigns causes by verbal autopsy but does not tabulate
   snakebite (it falls within 'unintentional injuries: other than motor vehicle accidents'), with snakebite coded by
   verbal autopsy at stable misclassification: expected deaths per year = 8.9 M x rate / 1e5, counts over-dispersed
   with design effect 2 (variance = 2 x mean, for the cluster sample); 3-year pools 2022-24 vs
   2028-30, Poisson; same metrics.
Writes outputs/napse_baselines.csv, napse_monitoring.csv.
"""
import pathlib
import numpy as np, pandas as pd

P = pathlib.Path(__file__).resolve().parents[1]
O = P / "outputs"; rng = np.random.default_rng(20261110); N = 20000
units = pd.read_csv(P / "data/model/units.csv").set_index("unit"); pop = units[[f"pop_{y}" for y in range(2014, 2025)]].to_numpy(float)
q = lambda v: np.percentile(v, [50, 2.5, 97.5])

# ---- 1-2. baselines and pace ----
rows = [dict(baseline="IHIP surveillance, 2024 (recorded)", deaths_2024=370), dict(baseline="Health-facility reports (NHP), 2022 (recorded)", deaths_2024=525),
        dict(baseline="Medical certification (MCCD), 2024 (recorded)", deaths_2024=1393), dict(baseline="Police (NCRB), 2024 (recorded)", deaths_2024=9803)]
nat = {}
for S, lab in (("S0", "Reconciled, primary (MDS level, national trend)"), ("S3", "Reconciled, recent anchors (ICMR completeness unknown)"),
               ("S4", "Reconciled, ICMR task force ~90% complete")):
    z = np.load(O / f"draws_{S}.npz"); nat[S] = (z["lam_2014_2024"] * pop[None] / 1e5).sum(1)
    m, lo, hi = q(nat[S][:, -1]); rows.append(dict(baseline=lab, deaths_2024=m, lo=lo, hi=hi))
    if S == "S0": B = z["B"]
base = pd.DataFrame(rows); base["target_2030"] = base.deaths_2024 / 2
base["deaths_averted_needed_2030"] = base.deaths_2024 - base.target_2030
need = 100 * (0.5 ** (1 / 6) - 1)
pace = dict(required_pct_per_year=need, mds_trend=q(100 * np.expm1(B)).tolist(), p_bau_meets_target=float((np.expm1(B) <= 0.5 ** (1 / 6) - 1).mean()))
base.to_csv(O / "napse_baselines.csv", index=False)

# ---- 3. drift of national completeness under S0 ----
cn = pd.read_csv(O / "completeness_national_S0.csv")
drift = {}
for src, d in cn.groupby("source"):
    x, y = d.year.to_numpy(float), np.log(d.c_pct.to_numpy())
    X = np.column_stack([np.ones_like(x), x - x.mean()]); beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta; s2 = e @ e / (len(y) - 2)
    yrs = np.diff(x); sig = np.sqrt(max(s2 - np.mean(1 / d.recorded), 1e-6))     # residual SD net of Poisson noise
    drift[src] = dict(mu=beta[1], mu_se=np.sqrt(s2 / ((x - x.mean()) ** 2).sum()), sigma=sig, y2024=d.recorded.iloc[-1], years=f"{int(x.min())}-{int(x.max())}")
# IHIP: only secondary (parliamentary) national counts 2023-25 (183, 375, 429); primary 2024 = 370
drift["IHIP (secondary-only 2023-25)"] = dict(mu=np.log(429 / 183) / 2, mu_se=0.15, sigma=drift["NHP"]["sigma"], y2024=370, years="2023-2025")

TRUTH = {"target met (true ratio 0.50)": lambda n: np.full(n, 0.5),
         "business as usual (MDS trend)": lambda n: np.exp(6 * rng.choice(B, n)),
         "no change (true ratio 1.00)": lambda n: np.ones(n)}
mon = []
DECL = 0.60                                                                   # "on track" if the system shows a fall of >= 40%


def summarise(system, dlab, sims, extra=None):
    Rt, Rb, R1 = sims["target met (true ratio 0.50)"], sims["business as usual (MDS trend)"], sims["no change (true ratio 1.00)"]
    auc = float((Rt[:, None] < Rb[None, :5000]).mean() + 0.5 * (Rt[:, None] == Rb[None, :5000]).mean())
    mon.append(dict(system=system, drift=dlab,
                    obs_change_if_target_met=float(100 * (np.median(Rt) - 1)), obs_change_if_bau=float(100 * (np.median(Rb) - 1)),
                    obs_change_if_no_change=float(100 * (np.median(R1) - 1)),
                    p_declare_on_track_if_target_met=float((Rt <= DECL).mean()), p_declare_on_track_if_bau=float((Rb <= DECL).mean()),
                    p_shows_rise_if_target_met=float((Rt > 1).mean()), auc_target_vs_bau=auc,
                    **{f"{k}_{qq}": float(100 * (np.percentile(R, pc) - 1)) for k, R in (("target", Rt), ("bau", Rb)) for qq, pc in (("lo", 2.5), ("hi", 97.5))},
                    **(extra or {})))


for src, dd in drift.items():
    for dlab, mu_on in (("drift continues", True), ("drift stops", False)):
        sims = {}
        for tlab, tf in TRUTH.items():
            tr = tf(N); mu = rng.normal(dd["mu"], dd["mu_se"], N) if mu_on else 0.0
            cr = np.exp(6 * mu + rng.normal(0, np.sqrt(6) * dd["sigma"], N))
            y24 = rng.poisson(dd["y2024"], N); y30 = rng.poisson(dd["y2024"] * tr * cr)
            sims[tlab] = (y30 + 0.5) / (y24 + 0.5)
        summarise(src, dlab, sims, dict(completeness_drift_pct_per_year=100 * np.expm1(dd["mu"]) if mu_on else 0.0, volatility_sd=dd["sigma"]))
# ---- 4. SRS verbal autopsy ----
srs_pop = 8.9e6; SRS_DEFF = 2.0                         # SRS COD 2022-24 report, s.1.3.1: 8,839 units, >8.9 M people
for S in ("S0", "S4"):
    rate24 = nat[S][:, -1] / pop[:, -1].sum() * 1e5
    sims = {}
    for tlab, tf in TRUTH.items():
        r = rng.choice(rate24, N); tr = tf(N)
        nb = lambda m: rng.poisson(rng.gamma(m / (SRS_DEFF - 1), SRS_DEFF - 1))     # variance = SRS_DEFF x mean (cluster sample)
        y_base = nb(3 * srs_pop * r / 1e5); y_end = nb(3 * srs_pop * r * tr / 1e5)
        sims[tlab] = (y_end + 0.5) / (y_base + 0.5)
    summarise(f"SRS verbal autopsy, 3-year pools ({S} rate)", "none (stable misclassification)", sims,
              dict(completeness_drift_pct_per_year=0.0, volatility_sd=0.0, expected_srs_deaths_per_year=float(np.median(srs_pop * rate24 / 1e5))))
mon = pd.DataFrame(mon); mon.to_csv(O / "napse_monitoring.csv", index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
print(base.round(0).to_string(index=False)); print(pace)
print({k: {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()} for k, v in drift.items()})
print(mon.round(3).to_string(index=False))
