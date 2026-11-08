# Snakebite deaths in India, 2014–2024: how much do routine systems record?

This repository holds the data and code for a Bayesian reconciliation of India's snakebite death figures. It combines state-level counts from:

- **Police:** National Crime Records Bureau, *Accidental Deaths & Suicides in India*.
- **Medical certification of cause of death:** Office of the Registrar General.
- **Public health facilities:** *National Health Profile*.
- **National disease surveillance:** Integrated Health Information Platform.

True death rates are anchored to the verbal-autopsy **Million Death Study** for 20 units that together cover India. The completeness of each recording system is then estimated by state and year. Finally, the repository tests whether any system could show if India's 2030 goal of **halving snakebite deaths** (NAPSE, 2024) is being met.

[![reproduce-and-verify](https://github.com/hssling/india-snakebite-reconciliation/actions/workflows/verify.yml/badge.svg)](https://github.com/hssling/india-snakebite-reconciliation/actions/workflows/verify.yml)

**Status.** The accompanying manuscript has been submitted for publication.

## Main findings

| | Snakebite deaths in 2024 (95% credible interval) |
|---|---|
| Reconciled estimate, primary model | **52 190** (38 740–68 810) |
| Recorded by police (NCRB) | 9803, i.e. **18.8%** (14.2–25.3%), up from 13.9% in 2014 |
| Recorded by medical certification (MCCD) | 1393, i.e. 2.7% |
| Recorded by public health facilities (NHP, 2022) | 525, i.e. 1.0% |
| Recorded by national surveillance (IHIP) | 370, i.e. **0.7%** |

- **Deaths concentrate where recording is weakest.** Uttar Pradesh and Bihar have 35% of deaths, but police record under 10% of them. In Bihar, police-recorded deaths rose from 45 to 478 over the decade, a change in recording rather than in mortality.
- **The recent task-force community surveillance (2022–25) recorded 11% of the deaths expected in its districts.**
  - Treating those counts as nearly complete would require a fall of about 11% a year since 2014 (19 470 deaths in 2024).
  - Madhya Pradesh compensation claims would then have to cover 95% of all snakebite deaths in the state.
- **No routine system can show whether deaths have halved by 2030:**
  - Police counts are biased by their rising completeness.
  - Surveillance counts rise as reporting expands.
  - Medical certification and facility counts are too noisy.
- **A verbal-autopsy measure could.** Tabulating snakebite in the Sample Registration System cause-of-death survey (8.9 million people) would separate success from business as usual almost perfectly.

## Reproduce

```bash
pip install -r requirements.txt
python verify.py          # recomputes 118 reported numbers from outputs/ and the posterior draws (seconds)
python run_pipeline.py    # rebuilds model inputs, completeness, the NAPSE analysis and figures from the draws, then verifies
```

Optional steps:

- **Refit the seven Bayesian models** (NumPyro, about 1–2 minutes): `pip install -r requirements-bayes.txt`, then `python run_pipeline.py --refit`.
- **Rebuild the panel from the source documents** (`pip install -r requirements-panel.txt`): put the files listed below under `data_raw/` (or point `SNAKEBITE_RAW` at them), then run `python run_pipeline.py --panel`.

GitHub Actions rebuilds the outputs and runs `verify.py` on every push.

## Contents

| Path | Contents |
|---|---|
| `data/state_year_source_panel.csv` | 1140 rows: snakebite deaths (and cases where printed) by state or district, year or period, and source. Values are transcribed from government reports and published studies, with page and table references. |
| `data/state_population.csv` | State populations 2011–2024 from the Technical Group on Population Projections, Table 11. |
| `data/completeness_anchors.csv` | Published measures of recording completeness and place-of-death ceilings. |
| `data/panel_validation_log.txt` | Every row-sum and printed-total check. |
| `data/model/` | Model inputs: 20 units, government counts, MDS period rates, task-force districts, Madhya Pradesh compensation. |
| `docs/` | Source matrix (every source, its definitions and verified citations) and the panel-build notes. |
| `src/model_inputs.py` | Builds the model inputs; government sums equal the printed national totals. |
| `src/reconcile_model.py` | Bayesian model of true rates anchored to the MDS (scenarios S0–S6). |
| `src/completeness.py` | Completeness of each system by unit and year; checks against the anchors. |
| `src/napse_decision.py` | 2030 target baselines and monitoring simulations. |
| `src/figures.py` | Figures 1–3. |
| `src/build_panel.py`, `src/extract_ncrb_adsi_snakebite.py` | Rebuild `data/` from the source documents. |
| `outputs/` | Posterior draws, completeness tables, anchor checks, monitoring results, diagnostics, figures. |
| `results/expected_key_results.json` | Values reported in the manuscript, checked by `verify.py`. |

## Source documents (not redistributed)

`data_raw/` should contain the following:

- `ncrb/ADSI_<year>.pdf`: NCRB *Accidental Deaths & Suicides in India*, 2014, 2015 and 2018–2024 (ncrb.gov.in).
- `mccd/Annual_Report_on_MCCD_<year>.pdf`: *Report on Medical Certification of Cause of Death*, 2016–2024 (censusindia.gov.in).
- `nhp/`: CBHI *National Health Profile*, 2019, 2020, 2021 and 2023 (cbhidghs.mohfw.gov.in).
- `population/`: the Technical Group population projections report, 2011–2036.
- `literature/`: PMC open-access full texts in BioC JSON for the MDS, task-force, compensation and district studies listed in `docs/source_matrix.md`.

## Licences

- **Code:** MIT.
- **Derived data:** CC BY 4.0.
- **Government reports and published papers:** cited and not redistributed.

## Author

Siddalingaiah H S, Department of Community Medicine, Shridevi Institute of Medical Sciences and Research Hospital, Tumakuru, Karnataka, India. ORCID [0000-0002-4771-8285](https://orcid.org/0000-0002-4771-8285).
