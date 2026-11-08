# Panel build notes (state x year x source)

Built 2026-11-09. Regenerate everything with:

```
python -I src/extract_ncrb_adsi_snakebite.py   # NCRB state tables from the ADSI PDFs (about 3 min)
python -I src/build_panel.py                    # everything else, plus all checks
```

Both scripts read only local files under `injury_india_public_health/` (nothing in a scratchpad, no network).

| Output | Rows | Content |
|---|---:|---|
| `data/state_year_source_panel.csv` | 1,140 | long panel; columns listed in section 2 |
| `data/state_population.csv` | 588 | 42 units x 2011-2024 (38 printed units + India + 4 derived aggregates) |
| `data/completeness_anchors.csv` | 46 | measured completeness, derived bounds and place-of-death ceilings |
| `data/state_name_mapping.csv` | - | every printed name -> canonical unit, by source |
| `data/panel_validation_log.txt` | 116 lines | every row-sum and printed-total check, with its result |
| `data/ncrb_adsi_snakebite_state_year.csv` | 333 | NCRB raw extraction (input to the panel) |

## 1. Inputs and where they live

| Source | Local file(s) | Pages / tables used |
|---|---|---|
| NCRB ADSI 2014, 2015, 2018-2024 | `data_raw/ncrb/ADSI_<y>.pdf`; 2014-15 in `data_raw/downloads_2026_11/` | "Poisoning (Snake Bite)" block of Table 1.11 (2014-15), 1.9 (2018-19), 1.10 (2020-24) |
| National Health Profile 2019, 2020, 2021, 2023 | `data_raw/snakebite/nhp/` | NHP 2019 T3.2.9(A,B) pp.151-152; NHP 2020 T3.2.9(a,b) pp.218-219; NHP 2021 T3.2.9(A,B) pp.230-231; NHP 2023 T3.2.3(A,B) pp.153-154 |
| MCCD 2016-2024 | `meta_suicide_reconciliation_india/data/raw/SRS Cause of death/Annual_Report_on_MCCD_<y>.pdf`; 2024 in `data_raw/downloads_2026_11/mccd_2024.pdf` | Table 4 (deaths by sex in States/UTs, national list), row "Bites of snakes & other venomous animals (X20-X27)", two facing pages per year |
| MDS | `data_raw/snakebite/literature/PMC7340498.bioc.json` (Suraweera 2020), `PMC3075236.bioc.json` (Mohapatra 2011) | Suraweera Tables 3 and 4; Mohapatra Table 2 |
| Anchors | `data_raw/snakebite/literature/PMC11791426.bioc.json` (Kadam), `PMC12603170.bioc.json` (Menon/ICMR), `PMC5991745.bioc.json` (Dandona), `PMC13307855.bioc.json` (Kiran) | Kadam Table 1; Menon Table 7; Dandona Table 2/Abstract; Kiran Results 2.1, 2.4 |
| Population | `data_raw/snakebite/population/technical_group_population_projections_2011_2036_Nov2019.pdf` | Table 11 (projected total population by sex as on 1st July), printed pp.82-94 (PDF pp.86-98) |

The BioC JSON files are the PMC open-access full texts, saved from the NCBI BioC API on 2026-11-09. Tables are parsed from the XML embedded in them.

Values entered literally in `build_panel.py` (not parseable from a local full text): TN IHIP (Subhashini 2026 abstract), Karnataka HMIS (Dodda Basava 2026 abstract), South 24 Parganas (Majumder 2014 abstract), Burdwan (Hati 1992 abstract), IHIP national 2024 (Shewale 2025 text), and the secondary-only IHIP parliamentary figures and Kerala Forest Department figures.

## 2. Panel columns and conventions

`state, state_as_printed, geography_level, district, year, ref_start, ref_end, period_type, source, source_detail, vintage, preferred, deaths, cases, rate_per_100k, denominator_note, status, page_or_table, notes`

- **geography_level**: `national`, `state`, `state-group` (MDS groupings), `district`, or `multi-district` (ICMR pooled). District anchors keep the state in `state` and the district name in `district`.
- **year**: calendar year for annual rows. For financial-year rows (MP compensation, Karnataka HMIS, Kerala Forest Department) `year` holds the FY start year and `ref_start`/`ref_end` give 1 April to 31 March. For multi-year rows (MDS periods, TN IHIP 2022-25, surveys) `year` is blank and `ref_start`/`ref_end` carry the period. `period_type` says which case applies.
- **vintage / preferred**: NHP prints each year twice, first as provisional and a year later as final. Both are kept. `preferred = 1` marks the latest vintage: final for 2017-2019 and 2021; provisional only for 2020 and 2022, because NHP 2022 and NHP 2024 are not held. IHIP parliamentary rows are `preferred = 0`, since a primary figure (370) exists for 2024.
- **status**: `primary` (1,096 rows), `derived` (26: sums of printed sub-rows, e.g. DNH + DD, Jammu Div. + Kashmir Div.), `secondary-only` (18: IHIP parliamentary figures and Kerala Forest Department figures).
- **deaths** are persons. MDS figures printed in thousands are converted (e.g. 101.9 -> 101900), and both the status and the notes record "printed in thousands".

### Canonical state names (full list in `state_name_mapping.csv`)

The 36 current units use names like "Odisha", "Delhi", "Andaman & Nicobar Islands", "Dadra & Nagar Haveli and Daman & Diu", "Jammu & Kashmir" and "Ladakh". Explicit rules:

| Case | Rule |
|---|---|
| Telangana / Andhra Pradesh | NCRB, NHP and MCCD print Telangana separately in every year held (2014+), so they map 1:1. MDS (Suraweera Tables 3-4, Mohapatra Table 2) "Andhra Pradesh" includes Telangana and maps to `Andhra Pradesh + Telangana (undivided AP)`. Population for that unit = AP + Telangana (derived). |
| J&K / Ladakh | Before 2020 every source prints one J&K (state incl. Ladakh) -> `Jammu & Kashmir + Ladakh (former J&K state)`: NCRB 2014-2019, MCCD 2016-2019, MDS. NHP 2017-2020 prints "Jammu Div." and "Kashmir Div."; their sum maps to the same former-state unit, because Ladakh is not listed separately. From 2020 NCRB prints J&K and Ladakh separately. NHP 2023 prints Jammu, Kashmir and Ladakh: J&K = Jammu + Kashmir (derived), Ladakh 1:1. **MCCD 2020 has no J&K or Ladakh column at all** (gap). |
| DNH / Daman & Diu | Any source printing them separately (NCRB 2014-19, NHP all years, MCCD 2016-19) is summed into `Dadra & Nagar Haveli and Daman & Diu` (status derived). MCCD 2021 and 2022 print BOTH a merged "D & N Haveli & Daman & Diu" column and a separate "Daman & Diu" column; the two are summed into one row. |
| Orissa | -> Odisha (NHP 2019, Mohapatra). |
| Groups | MDS "Northeastern states" -> `NE-7 (...)` (population derived as the sum of the 7 states). MDS "All other states" and Mohapatra "Remaining states" are kept as residual groups without a population (membership not fully specified in the sources). |

## 3. Source-specific extraction decisions

- **NCRB.** `persons_died` is the last column (Total died) of the snake-bite block. In ADSI 2015 the table also reprints the 2014 deaths; the 2015 value is the last column. The DNH & DD row in 2020-2024 has its name split over two text lines. The extractor now catches it, so all nine years reconcile exactly with no residual row; earlier versions left 1 death (2020) and 2 deaths (2022) unassigned.
- **NHP.** Deaths and cases are the "Total" columns. Lakshadweep in NHP 2019 (data years 2017 and 2018) carries the footnote "* No reporting from the state in respect of the cases and death of snake bites". Its printed zeros are entered as missing. West Bengal is printed "NA" in 2021 and 2022 and is entered as missing. The NHP 2021 Assam 2019 row (758 cases, 359 deaths, female cells 0) is kept as printed and flagged as a probable column shift. NHP 2020's provisional 2019 table has Odisha at 1,872 deaths; the final figure is 117 (NHP 2021). Both are kept and only the final is preferred.
- **MCCD.** Columns are located by word coordinates on each of the two facing pages, because the second page is mirrored in the PDF text layer. Columns are keyed by position, since printed column numbers repeat ("11" twice in 2021-22). Title words in capitals are excluded from header matching, and "Lakshawdeep" (sic, 2016-18) is recognised. Every row is flagged "includes non-snake venomous animals". M and F counts are kept in `notes`.
- **MDS.**
  - Suraweera Table 3 contributes three period rates per state (2001-04, 2005-09, 2010-14; deaths blank) and one cumulative 2001-14 death count per state.
  - Table 4 contributes, per state, MDS total deaths 2003-15, plus a separate source `GovHospital-MoHFW` for government-hospital-reported deaths and bites over the same period. Coverage and in-hospital deaths are in `notes` and in the completeness file.
  - Mohapatra Table 2 contributes 2005 deaths and rates for 13 high-prevalence states, the residual group and All India.
  - No state-by-single-year MDS series exists in the published papers.
- **MP compensation.** One state row per financial year from the Table 1 total row (3,019; 2,760). Districts are not entered as panel rows; they are used only for the row-sum check.
- **ICMR NTF.** All 25 district rows from Table 7 plus the pooled total. Three districts print "---" for deaths (Aizawl, Champhai, Pakke Kessang); their deaths are left blank. The exact 12-month window per district is in Supplementary Table 1, which is not held, so `ref_start`/`ref_end` are set to 2022-2025.
- **Bihar SmartVA.** `deaths = 47` is the number of study deaths in the sample (Table 2 "Snakebite N = 47"), not a state total. Use the 4.4 per 100,000 rate.
- **Jagtial.** Three rows: 69 deaths among 541 victims over 2010-20 (snowball sample, so a lower bound for the district), and the paired community and district-hospital crude rates for 2015-20.

## 4. Population (`state_population.csv`)

- Source: *Report of the Technical Group on Population Projections, 2011-2036*, National Commission on Population, MoHFW. Table 11 ("Projected Total Population by Sex as on 1st July"), in thousands, converted to persons. Every year 2011-2024 is printed, so **no interpolation was needed**.
- The 2011 value is the 1 July 2011 projection from the Census 2011 base, not the Census enumeration of 1 March 2011 (that is Table 8 of the same report, not extracted).
- **Version caveat.** The local PDF's cover is dated "November, 2019". It was downloaded from a GiveWell mirror because the NCP and MoHFW URLs did not respond. The report was publicly released in July 2020. Before publication, check that the figures match the official NCP copy.
- J&K (UT) and Ladakh are printed separately, as are Daman & Diu and DNH. The derived rows are the merged DNH & DD, the former J&K state, undivided AP and NE-7 (status `derived (sum)`).
- The NE-7 state figures are the report's own pro-rata split of a combined NE projection (report p.21). Treat them as less informative.

## 5. Validation checks (full list in `data/panel_validation_log.txt`)

Result: 81 OK, 7 OK-ROUNDING, 14 DIFF-SMALL, 10 MISMATCH. None of the mismatches is an extraction error; each is a printed inconsistency in the source.

| Check | Result |
|---|---|
| NCRB, 9 years: state deaths and cases sum to printed TOTAL (ALL INDIA) | 18/18 exact |
| NHP, 8 tables x 6 columns (M/F/T cases and deaths): state rows sum to the printed India/Total row | 7 tables exact. **NHP 2020 Table 3.2.9(a) (data year 2018, final): all 37 rows parsed, but they sum to 885 deaths / 161,203 cases, against a printed total of 887 / 165,948.** The printed total is inconsistent with its own rows. |
| NHP row-level M + F = Total | 3 printed inconsistencies, all in NHP 2019 Table 3.2.9(B) (2018 provisional) and in cases only: Meghalaya 325 vs 327, Mizoram 321 vs 368, Nagaland 251 vs 245 |
| MCCD, 9 years: state T sums to All States (Total) T; per-state M + F = T | 9/9 exact; no M+F mismatches |
| Suraweera Table 3 / Table 4 group subtotals and All India (thousands) | equal within rounding of 0.1-thousand cells (7 OK-ROUNDING, largest gap 0.2 thousand) |
| Mohapatra Table 2: 13 states sum to Sub total; Sub total + Remaining = All India; study deaths | exact |
| Kadam Table 1: 51 district deaths sum to the totals (3,019; 2,760) and amounts to 12,076 lakh | exact. The printed "Total" in the two rate columns (195, 177) is a sum of district rates, not a state rate. The abstract's 5,728 families disagrees with Table 1's 3,019 + 2,760 = 5,779. |
| ICMR Table 7: district deaths (195) and incidents (7,094) sum to the total | exact. District populations sum to 59,781,582 against a printed 59,781,583 (1 person). |
| Population: 38 printed units sum to printed India, every year | **systematic shortfall of 24-38 thousand per year** (<0.003%). Rounding 38 cells explains at most ~19 thousand. The report gives no explanation. Logged as DIFF-SMALL. Use unit-level values; do not rescale to India. |

## 6. Coverage summary

| Source | Rows | Years / period | Geography |
|---|---:|---|---|
| NCRB | 329 | 2014, 2015, 2018-2024 | 36 units + India |
| MCCD | 323 | 2016-2024 | 33-36 units + India (no J&K/Ladakh in 2020) |
| NHP | 290 | 2017-2022 (2018-2020 and 2022 provisional; 2018-2019 also final) | 35-37 units + India; WB missing 2021-22 |
| MDS | 120 | 2001-04, 2005-09, 2010-14 rates; 2001-14 and 2003-15 cumulative deaths; 2005 (13 states) | states, groups, India |
| GovHospital-MoHFW (via Suraweera T4) | 21 | 2003-2015 cumulative | states, groups, India |
| ICMR-NTF | 27 | 12 months within 2022-25; Kerala "2024-25" | 25 districts, pooled, Kerala |
| IHIP | 16 | TN 2022-25 (primary); India 2024 (primary); India 2023-25 and 6 states 2023-25 (secondary-only) | TN, India, states |
| Compensation-MP | 2 | FY2020-21, FY2021-22 | Madhya Pradesh |
| Compensation-Kerala-Forest | 4 | 2018-19, 2020-21, 2021-22, 2025 | Kerala (secondary-only) |
| SmartVA-Bihar | 1 | Jan 2012 - Mar 2014 | Bihar |
| HMIS-Karnataka | 2 | FY2018-19, FY2019-20 (incidence only) | Karnataka |
| Survey-Jagtial / Hospital-Jagtial | 2 / 1 | 2010-20; 2015-20 | Jagtial district |
| Survey-South24Parganas | 1 | ~2007-10 (cases only) | district |
| Survey-Burdwan | 1 | 1980-89 | district sample |

- Counting only primary or derived rows with a death count, **37 units have at least three sources**. That is 36 canonical units plus the former-J&K unit; undivided AP has two.
- **36 units have three systems (NCRB, NHP, MCCD) in the same calendar year**, for every year 2018-2022.
- Counting primary sources only, 9 states have 6 (government series plus MDS, MoHFW hospital reports or an anchor): Bihar, Kerala, Madhya Pradesh, Maharashtra, Odisha, Punjab, Rajasthan, Tamil Nadu and West Bengal. Kerala reaches 8 if the secondary-only IHIP and Forest Department rows are counted.

## 7. Completeness anchors (`completeness_anchors.csv`, 46 rows)

| kind | n | What |
|---|---:|---|
| measured (as printed) | 23 | Suraweera Table 4 col (7): government hospital reports / MDS in-hospital deaths, 2003-15, for India (10%), 18 states and 4 groups (2 burden groups, NE-7, all other states). The denominator is in-hospital deaths only, so completeness against all deaths is lower. |
| measured | 1 | South 24 Parganas: 7.23% of deaths officially reported (abstract; counts not available) |
| derived ratio | 1 | Jagtial: district hospital vs community crude mortality, 1.01 / 5.94 = 17% |
| upper bound (derived) | 3 | MP: NHP 2021 / compensation FY21-22 = 5 / 2,760 (0.18%); NCRB 2021 / compensation = 2,732 / 2,760 (99%); NCRB 2020 / compensation FY20-21 = 2,512 / 3,019 (83%). Compensation is a lower bound on true deaths, so these ratios are upper bounds. |
| ceiling (place of death) | 18 | Mohapatra Table 2 for 13 states, the sub-total, remaining states and All India (16 rows): share of VA snakebite deaths NOT outside a facility (All India 127/562 = 22.6%); Suraweera "77% out of hospital" (23%); ICMR 56.9% in hospital. A facility-based system cannot exceed these shares. |

## 8. Could not extract (gaps)

1. NCRB ADSI 2016 and 2017: PDFs not held.
2. NHP 2018 (data 2016), NHP 2022 (final 2020, provisional 2021) and NHP 2024+ (2022 final, 2023+): not on the CBHI publication page; the old e-book URL returns 404. So 2020 and 2022 exist only as provisional figures.
3. MCCD 2020: no J&K or Ladakh column in Table 4.
4. MDS: no annual state series. Only three period rates, cumulative deaths, and the 2005 state estimates for 13 states. The Suraweera Appendix tables give age and sex detail, not state-year.
5. IHIP: no primary state-year data. Only the TN study and the national 2024 figure are primary. The parliamentary replies on eparlib.sansad.in refused connections, so the 2023-25 national and state figures are secondary-only.
6. ICMR NTF: Supplementary Table 1 (exact 12-month window per site) not held; the West Bengal and Meghalaya sites are not yet reported.
7. Karnataka HMIS: deaths not in the abstract (full text paywalled). South 24 Parganas: death counts not in the abstract (full text not accessed).
8. Kerala Forest Department compensation and Odisha "800-900/yr": quoted in Menon 2026 only; departmental data not seen.
9. GBD state estimates are deliberately not in the panel. They are not independent of MDS. GBD 2023 venomous-animal-contact state results exist in `data_raw/gbd/IHME-GBD_2023_DATA-467618ec-1.csv` if needed for validation; GBD 2019 Supplementary Table 5 (snake-specific states) is not held.
10. Population: the Census 2011 enumeration (1 March, Table 8) was not extracted. The official NCP copy of the projection report could not be downloaded for comparison.
