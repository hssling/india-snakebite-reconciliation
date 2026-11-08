"""Bayesian reconciliation of snakebite deaths in India, 2014-2024: true-rate model anchored to the Million Death Study.

Stage 1 (this script) estimates the true snakebite death rate lambda_{u,t} per 100,000 for 20 units that tile India.
Government series are NOT allowed to inform lambda (their completeness changes over time; e.g. Bihar NCRB x7.5 in a
decade), so completeness is derived afterwards as recorded / expected deaths (completeness.py) - a "cut" design.

  log lambda_{u,t} = a_u + b_u * (min(t, 2014) - 2012) + g_u(t)                       t = 2001..2024
  a_u ~ N(A, s_a),  b_u ~ N(B, s_b)                                                    partial pooling over units
  MDS (Suraweera 2020, Table 3) period ASR, p in {2001-04, 2005-09, 2010-14}:
      log ASR_{u,p} ~ N(log mean_{t in p} lambda_{u,t},  sqrt(deff / n_{u,p} + s_x^2))
      n_{u,p} = study deaths 2001-14 allocated to periods by rate x years; deff = design effect; s_x = extra noise

Post-2014 trajectory g_u(t), t > 2014 (scenarios; MDS ends in 2014, so this is an assumption, not an estimate):
  S0 primary      : national MDS slope continues:              g = B * (t - 2014)
  S1 unit trends  : each unit's own 2001-14 slope continues:    g = b_u * (t - 2014)
  S2 flat         : rates stay at their 2014 level:             g = 0
  S3 anchors      : g = (B + D) * (t - 2014), D ~ N(0, 0.10) a post-2014 change in the national slope, informed by
                    the ICMR task-force districts (completeness c_icmr ~ Beta(1, 1), unknown) and Madhya Pradesh paid
                    compensation claims (a lower bound: claims ~ Poisson(c_comp * true deaths), c_comp ~ Beta(1, 1))
  S4 ICMR complete: as S3 but c_icmr ~ Beta(18, 2) (mean 0.9): the reading that the task-force counts are near-complete
  S5 deff = 1, S6 deff = 4 (primary deff = 2)
ICMR district relative risk vs its state: log RR_d ~ N(0, s_d), s_d ~ HalfNormal(0.5).
Outputs: outputs/draws_<scenario>.npz (lambda 2014-2024 by unit, hyper-parameters, anchor parameters), log.
"""
import os, sys, json, pathlib, time
os.environ["XLA_FLAGS"] = "--xla_force_host_platform_device_count=4"
import numpy as np, pandas as pd
import jax, jax.numpy as jnp
import numpyro, numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS
from numpyro.diagnostics import summary
numpyro.set_host_device_count(4)

P = pathlib.Path(__file__).resolve().parents[1]
D = P / "data/model"; O = P / "outputs"; O.mkdir(exist_ok=True)
units = pd.read_csv(D / "units.csv").set_index("unit")
mds = pd.read_csv(D / "mds_obs.csv"); icmr = pd.read_csv(D / "icmr_obs.csv"); comp = pd.read_csv(D / "anchors_obs.csv")
U = list(units.index); NU = len(U); uix = {u: i for i, u in enumerate(U)}
Y0, Y1 = 2001, 2024; YRS = np.arange(Y0, Y1 + 1); NT = len(YRS)
pop = units[[f"pop_{y}" for y in range(2014, 2025)]].to_numpy(float)          # NU x 11

# MDS design: period membership matrix (60 obs x NT)
mu_ix = jnp.array([uix[u] for u in mds.unit])
W = np.zeros((len(mds), NT))
for i, r in enumerate(mds.itertuples()):
    W[i, (YRS >= r.y0) & (YRS <= r.y1)] = 1.0 / (r.y1 - r.y0 + 1)
W = jnp.array(W); log_asr = jnp.array(np.log(mds.asr.values)); n_per = jnp.array(mds.n_period.values)
# ICMR: districts, 12 months centred on 2023.5 -> mean of 2023 and 2024 rates
ic_u = jnp.array([uix[u] for u in icmr.unit]); ic_pop = jnp.array(icmr.district_pop.values); ic_y = jnp.array(icmr.deaths.values)
# MP compensation, financial years: FY2020-21 = 0.75*2020 + 0.25*2021; FY2021-22 = 0.75*2021 + 0.25*2022
mp = uix["Madhya Pradesh"]
comp = comp.sort_values("year"); comp_y = jnp.array(comp.deaths.values.astype(float))
assert list(comp.year) == [2020, 2021]
t_c = jnp.array(YRS - 2012.0); t_pre = jnp.array(np.minimum(YRS, 2014) - 2012.0); t_post = jnp.array(np.maximum(YRS - 2014, 0.0))


def model(scn):
    A = numpyro.sample("A", dist.Normal(jnp.log(4.0), 1.0))
    s_a = numpyro.sample("s_a", dist.HalfNormal(1.0))
    B = numpyro.sample("B", dist.Normal(0.0, 0.05))
    s_b = numpyro.sample("s_b", dist.HalfNormal(0.03))
    a = numpyro.deterministic("a", A + s_a * numpyro.sample("za", dist.Normal(0, 1).expand([NU])))
    b = numpyro.deterministic("b", B + s_b * numpyro.sample("zb", dist.Normal(0, 1).expand([NU])))
    s_x = numpyro.sample("s_x", dist.HalfNormal(0.15))
    if scn["post"] == "national": g = B * t_post[None, :]
    elif scn["post"] == "unit": g = b[:, None] * t_post[None, :]
    elif scn["post"] == "flat": g = jnp.zeros((1, NT))
    else:
        Dch = numpyro.sample("D", dist.Normal(0.0, 0.10))
        g = (B + Dch) * t_post[None, :]
    loglam = a[:, None] + b[:, None] * t_pre[None, :] + g                       # NU x NT
    lam = jnp.exp(loglam)
    numpyro.deterministic("lam_2014_2024", lam[:, -11:])
    pm = (lam[mu_ix] * W).sum(1)
    numpyro.sample("mds", dist.Normal(jnp.log(pm), jnp.sqrt(scn["deff"] / n_per + s_x ** 2)), obs=log_asr)
    if scn.get("anchors"):
        lam_ic = 0.5 * (lam[:, -2] + lam[:, -1])                                # 2023, 2024
        s_d = numpyro.sample("s_d", dist.HalfNormal(0.5))
        rr = jnp.exp(s_d * numpyro.sample("zd", dist.Normal(0, 1).expand([len(icmr)])))
        c_ic = numpyro.sample("c_icmr", dist.Beta(*scn["c_icmr"]))
        numpyro.sample("icmr", dist.Poisson(c_ic * lam_ic[ic_u] * rr * ic_pop / 1e5), obs=ic_y)
        dmp = lam[mp, -11:] * pop[mp] / 1e5                                       # 2014..2024
        fy = jnp.stack([0.75 * dmp[6] + 0.25 * dmp[7], 0.75 * dmp[7] + 0.25 * dmp[8]])
        c_comp = numpyro.sample("c_comp", dist.Beta(1.0, 1.0))
        numpyro.sample("comp", dist.Poisson(c_comp * fy), obs=comp_y)


SCN = {"S0": dict(post="national", deff=2.0), "S1": dict(post="unit", deff=2.0), "S2": dict(post="flat", deff=2.0),
       "S3": dict(post="change", deff=2.0, anchors=True, c_icmr=(1.0, 1.0)),
       "S4": dict(post="change", deff=2.0, anchors=True, c_icmr=(18.0, 2.0)),
       "S5": dict(post="national", deff=1.0), "S6": dict(post="national", deff=4.0)}
LABEL = {"S0": "primary: unit level to 2014, national MDS slope after", "S1": "unit-specific 2001-14 slopes continue",
         "S2": "flat after 2014", "S3": "anchor-informed post-2014 change (ICMR completeness unknown)",
         "S4": "anchor-informed post-2014 change, ICMR assumed ~90% complete", "S5": "MDS design effect 1", "S6": "MDS design effect 4"}

if __name__ == "__main__":
    todo = sys.argv[1:] or list(SCN)
    diag = {}
    for k in todo:
        t0 = time.time()
        mcmc = MCMC(NUTS(model, target_accept_prob=0.95), num_warmup=1000, num_samples=1000, num_chains=4, progress_bar=False)
        mcmc.run(jax.random.PRNGKey(20261110), SCN[k], extra_fields=("diverging",))
        g = mcmc.get_samples(group_by_chain=True)
        keys = [v for v in ("A", "s_a", "B", "s_b", "s_x", "D", "c_icmr", "c_comp", "s_d", "a", "b") if v in g]
        sm = summary({v: g[v] for v in keys}, prob=0.95)
        rhat = max(float(np.max(v["r_hat"])) for v in sm.values()); neff = min(float(np.min(v["n_eff"])) for v in sm.values())
        ndiv = int(mcmc.get_extra_fields()["diverging"].sum())
        s = {v: np.asarray(x) for v, x in mcmc.get_samples().items() if v in keys + ["lam_2014_2024"]}
        np.savez_compressed(O / f"draws_{k}.npz", units=np.array(U), **s)
        nat = (s["lam_2014_2024"] * pop[None] / 1e5).sum(1)                   # draws x 11
        q = lambda v: np.percentile(v, [50, 2.5, 97.5])
        diag[k] = dict(label=LABEL[k], seconds=round(time.time() - t0), max_rhat=round(rhat, 4), min_neff=round(neff), divergences=ndiv,
                       deaths_2014=q(nat[:, 0]).round(-1).tolist(), deaths_2024=q(nat[:, -1]).round(-1).tolist(),
                       B_pct_per_year=q(100 * np.expm1(s["B"])).round(2).tolist(),
                       **({"D_pct_per_year": q(100 * np.expm1(s["D"])).round(2).tolist()} if "D" in s else {}),
                       **({v: q(s[v]).round(3).tolist() for v in ("c_icmr", "c_comp") if v in s}))
        print(k, json.dumps(diag[k]), flush=True)
    old = json.loads((O / "model_diagnostics.json").read_text()) if (O / "model_diagnostics.json").exists() else {}
    old.update(diag); (O / "model_diagnostics.json").write_text(json.dumps(old, indent=1))
