# Snakebite mortality in India: verified source matrix

Built 2026-11-09 for the multi-source Bayesian reconciliation (source-specific bias terms, same design as the OMEGA suicide paper).
Machine-readable version: `docs/source_matrix.csv` (69 rows, one per source x reference period, 23 columns, including the exact quote and its page/table).
State-year police series: `data/ncrb_adsi_snakebite_state_year.csv` (NCRB, 9 years x 35-36 states/UTs, validated against the printed All-India totals).
Builders: `src/build_source_matrix_csv.py`, `src/extract_ncrb_adsi_snakebite.py`.

## Rules applied

1. **Citations.** Every DOI was resolved on Crossref and every PMID on PubMed E-utilities. Title, first author, year and journal were compared, and the PMID-to-DOI link was cross-checked for all 17 PubMed records. Discrepancies are flagged in the `citation_check` column. Citations that could not be verified are not in the matrix; they are listed in the UNVERIFIED section below.
2. **Numbers.** `number_status = primary` means the number was read in the primary document: the full text, a government PDF or the data file. Page and table are given in `location_in_source`. `secondary-only` names the secondary source. `derived` marks arithmetic of mine that the source does not state.
3. **Government reports** (NCRB, NHP, MCCD, SRS, NAPSE) were read from the PDFs themselves. NCRB, MCCD and SRS PDFs were already on disk. The NHP PDFs were downloaded from cbhidghs.mohfw.gov.in. NAPSE came from a Wayback copy, because the NCDC URL now returns 404.

---

## 1. National estimates, ranked (annual deaths, India)

| Annual deaths | Source (row id) | Type | Ref. year | Status |
|---:|---|---|---|---|
| 183 / 370-375 / 429-431 | IDSP-IHIP, Parliament replies (S18b) | notifiable surveillance | 2023 / 2024 / 2025 | secondary-only |
| 370 | IDSP-IHIP, NCDC authors (S18a) | notifiable surveillance | 2024 | primary |
| 525 - 1,700 (3,163 provisional 2019) | National Health Profile, T63.0 (S14) | public health facility | 2017-2022 | primary |
| ~1,069 (stated "about 2000") | NAPSE quoting CBHI (S24b) | policy | 2016-2020 | primary |
| 1,132 - 2,408 (snakes **plus** other venomous animals) | MCCD X20-X27 (S16) | medically certified | 2016-2024 | primary |
| 2,300 (2,000-2,650) | Ediriweera 2026, country-level data, uncorrected (S21a) | model | ~2025 | primary |
| ~4,700 (0.33/100k) | ICMR NTF community survey (S05a/b) | community surveillance (11 states) | 2022-25 | rate primary; national count **derived** |
| 7,846 - 10,382 | NCRB ADSI "Poisoning (Snake Bite)" (S13) | police | 2014-2024 | primary |
| ~11,000 | Kasturiratne 2008 conservative (S22) | literature model | ~2007 | primary |
| 37,600 (32,000-44,200) | Ediriweera 2026 LOW scenario (S21b) | model | ~2025 | primary |
| 45,900 (99% CI 40,900-50,900) | MDS 2001-03 deaths, 2005 totals (S01a) | verbal autopsy | 2005 | primary |
| 51,100 (95% UI 29,600-64,100) | GBD 2019 snakebite (S19) | model (MDS-type inputs) | 2019 | primary |
| 53,880 - 58,581 (venomous animal contact) | GBD 2023 Results tool (S20) | model | 2020-2023 | primary |
| 58,000 (average); 59,800 (2019 projection) | MDS 2001-14 (S02b, S02-2019) | verbal autopsy | 2000-2019 | primary |
| 70,100 (58,800-82,500) | Ediriweera 2026 HIGH scenario (S21c) | model | ~2025 | primary |

**Range: 370 (IHIP 2024) to about 70,100 (Ediriweera, high scenario), a spread of roughly 190-fold.** The "twelvefold" disagreement in the brief is the gap between the two community-based rate estimates: MDS at 4.0-4.8 per 100,000 (age-standardised) and the ICMR survey at 0.33 per 100,000 (crude). That ratio is 12-15x.

Independence: GBD (S19, S20) and the WHO fact sheet (S23) draw their Indian information from MDS-type verbal autopsy. They should not enter the fusion model as independent likelihood terms. Use them as a posterior-predictive check, or as one "MDS-family" block.

## 2. Source matrix (summary; full fields, including quotes, in the CSV)

| ID | Source | Type | Geography | Ref. period | Deaths (interval) | Rate /100k | Case definition | Key biases | Where in source |
|---|---|---|---|---|---|---|---|---|---|
| S01a | MDS, Mohapatra 2011 | verbal autopsy | India | 2005 | 45,900 (99% CI 40,900-50,900) | 4.1 (3.6-4.5) ASR | ICD-10 X20, dual physician VA coding | VA misclassification; UN-total scaling | Abstract; Methods |
| S01b | MDS, Mohapatra 2011 | verbal autopsy | UP / AP / Bihar | 2005 | 8,700 / 5,200 / 4,500 | AP 6.2 | as above | small state samples | Abstract; Table 2 |
| S02a | MDS, Suraweera 2020 | verbal autopsy | India | 2001-14 cumulative | 807,500 (738,200-833,400) | 4.8 (4.4-5.0) ASR | X20; 2,833 of 611,483 VA | range covers coding disagreement only | Table 1 |
| S02b / S02-yyyy | MDS, Suraweera 2020 | verbal autopsy | India | 2000-19; single years | 58,000/yr avg; 55,000 (2001) ... 61,200 (2014); 59,800 (2019 proj.) | 4.3-5.3 by year | as above | 2015-19 are projections | Abstract; Tables 1-2 |
| S02c | MDS, Suraweera 2020 | verbal autopsy | all large states | 2001-14 | e.g. high-burden 8: 557,400 | state ASR, 3 periods (e.g. MP 6.0, Kerala 0.5 in 2010-14) | as above | small n in some states | Table 3 |
| S02d | MDS vs MoHFW hospital reports | facility vs VA | India, by state | 2003-15 cumulative | 15,500 reported vs 154,200 MDS in-hospital (10%) | - | public-hospital reports | public facilities only | Table 4 |
| S03 | Bihar SmartVA, Dandona 2018 | verbal autopsy | Bihar | 2012-14 | - | 4.4 (4.3-4.6) adjusted | PHMRC VA + SmartVA | algorithmic VA | Abstract |
| S04 | TN IHIP + VA, Subhashini 2026 | notifiable surveillance | Tamil Nadu | Jan 2022-May 2025 | 100 | 0.14 ASMR | IHIP-reported deaths | facility-only | Abstract |
| S05a | ICMR NTF survey, Menon 2025 | community surveillance | 25 districts, 11 states (59.8 M) | 1 yr per site, 2022-25 | 195 | 0.33 crude | ASHA-tracked deaths | interim; UP/MP/Bihar excluded; COVID | Table 7; Abstract |
| S05b | derived from S05a | - | India | - | ~4,700 | 0.33 | - | **derived** | - |
| S05c | Menon 2025 statement | - | Kerala | 2024-25 | 31 | - | unnamed | source of 31 not stated | Discussion |
| S06 | Jagtial survey, Kiran 2026 | community survey (snowball) | Jagtial, Telangana | 2010-20 | - | 1.07/yr age-adj. (0.73-1.20); hospital 1.01 vs community 5.94 crude | recalled outcomes | snowball; 11.72 in abstract is cumulative | Results; Tables 2-3 |
| S07 | S-24 Parganas survey, Majumder/Sinha 2014 | community vs official | 8 blocks, WB (1.9 M) | ~2007-10 | - | - | door-to-door | 2-yr recall | Abstract ("Only 7.23% ... officially reported") |
| S08 | Burdwan survey, Hati 1992 | community survey | Burdwan, WB | 1980-89 | 31 in sample | 16.4 (5.28-31.75) | recall | old, small | Abstract |
| S09 | TN household survey, Vaiyapuri 2013 | household survey | rural TN | n/s | "0.45% of the population" | - | recall | metric unclear | Abstract |
| S10 | Loni autopsies, Farooqui 2016 | medico-legal autopsy | Loni, Maharashtra | 2004-14 | 54 | - | autopsied deaths | no denominator | Abstract |
| S11a/b | MP compensation, Kadam 2025 | compensation | Madhya Pradesh | FY2020-21; FY2021-22 | 3,019; 2,760 | 3.6; 3.3 (derived) | paid claims, postmortem required | lower bound; abstract 5,728 vs Table 1 5,779 | Results; Table 1 |
| S12 | Kerala Forest Dept compensation (via Menon 2026) | compensation | Kerala | 2018-19 ... 2025 | 123; 52; 65; 34 | - | paid claims | **secondary-only** | Introduction |
| S13-yyyy | NCRB ADSI | police | India + states | 2014, 2015, 2018-2024 | 7,846; 8,554; 8,962; 9,224; 9,822; 10,382; 10,096; 10,118; 9,803 | - | police inquest, "Poisoning (Snake Bite)" | police-recorded only; state practice varies | Table 1.9/1.10/1.11 (Contd.), pp.94-97 |
| S14-yyyy | National Health Profile | public facility | India + states | 2016-2022 | 1,068 (2016, **secondary**); 1,060; 887; 1,700 (prov. 3,163); 626 (prov.); 600; 525 (prov.) | - | ICD-10 T63.0 | public only; WB "NA"; revisions | NHP 2019 T3.2.9; NHP 2020 T3.2.9; NHP 2021 T3.2.9; NHP 2023 T3.2.3 |
| S15 | NHP analysis, Rubeshkumar 2021 | facility (secondary) | India | 2009-18 | - | CFR 5-13 per 1,000 | NHP | hospital-only | Abstract |
| S15b | Karnataka HMIS, Dodda Basava 2026 | facility (HMIS) | Karnataka | 2018-20 | not reported | incidence 24.57 / 24.49 | HMIS cases | incidence only | Abstract |
| S16-yyyy | MCCD | medically certified | India + states | 2016-2024 | 2,408; 1,577; 1,875; 1,692; 1,475; 1,132; 1,638; 1,639; 1,393 | - | ICD-10 X20-X27 (all venomous animals) | low, urban certification | Table 4 |
| S17 | SRS Cause of Death | routine VA | India | 2014-24 | not tabulated | - | lumped in "other unintentional injuries" | - | SRS COD 2021-23 p.16 |
| S18a | IHIP via NCDC (Shewale 2025) | notifiable surveillance | India | 2024 | 370 | - | IHIP S/P forms | facility-based | Introduction |
| S18b | IHIP via Parliament (news) | notifiable surveillance | India | 2023-25 | 183; 375/370; 429/431 | - | as above | **secondary-only** | - |
| S19 | GBD 2019 snakebite (Nat Commun 2022) | model | India | 2019 | 51,100 (29,600-64,100) | 4.0 (2.3-5.0) ASMR | snake share of venomous animal contact | MDS-dependent | Results; Suppl. Table 5 |
| S20-yyyy | GBD 2023 Results tool | model | India + 31 states | 2020-23 | 53,946; 58,581; 53,880; 54,464 | 3.77-4.13 crude | **venomous animal contact** (all species) | MDS-dependent; not snake-only | local IHME CSV |
| S21a/b/c | Ediriweera 2026 | geostatistical model | India | ~2025 | 2,300 / 37,600 / 70,100 | 0.2 / 2.7 / 5.0 | 3 data-source scenarios | scenario = under-reporting assumption | S4 Appendix Table B |
| S22 | Kasturiratne 2008 | literature model | India | ~2007 | ~11,000 | - | literature | pre-MDS | Results |
| S23 | WHO fact sheet (17 Sep 2026) | restates MDS | India | 2005; 2000-19 | 45,900; 58,000 | - | cites MDS | not independent | text |
| S24a/b/c | NAPSE (NCDC 2024) | policy | India | target 2030 | halve deaths, **no numeric baseline**; quotes ~2,000/yr, 5,343 (2016-20), 1,000-2,500, 50,000, 58,000 | - | - | internally inconsistent | PDF pp.1, 39, 43, 50, 85, 132, 135 |

### Full citations of the verified sources

1. Mohapatra B, Warrell DA, Suraweera W, et al. Snakebite mortality in India: a nationally representative mortality survey. *PLoS Negl Trop Dis.* 2011;5(4):e1018. doi:10.1371/journal.pntd.0001018. PMID 21532748. https://pmc.ncbi.nlm.nih.gov/articles/PMC3075236/
2. Suraweera W, Warrell D, Whitaker R, et al. Trends in snakebite deaths in India from 2000 to 2019 in a nationally representative mortality study. *eLife.* 2020;9:e54076. doi:10.7554/eLife.54076. PMID 32633232. https://pmc.ncbi.nlm.nih.gov/articles/PMC7340498/
3. Dandona R, Kumar GA, Kharyal A, George S, Akbar M, Dandona L. Mortality due to snakebite and other venomous animals in the Indian state of Bihar: findings from a representative mortality study. *PLoS One.* 2018;13(6):e0198900. doi:10.1371/journal.pone.0198900. PMID 29879197.
4. Subhashini KJ, Kumar EV, Kumar MS, Devaparthasarathy TA, Selvavinayagam TS, Somasundaram A. Burden and determinants of snakebite mortality in Tamil Nadu, India: a surveillance and verbal autopsy study. *Trans R Soc Trop Med Hyg.* 2026 (online ahead of print):trag092. doi:10.1093/trstmh/trag092. PMID 42631407.
5. Menon JC, Bharti OK, M S A, et al. Cross-sectional survey of the incidence, mortality and socioeconomic burden of snakebite envenoming in India. *Nat Commun.* 2025;16(1):9871. doi:10.1038/s41467-025-64849-2. PMID 41213936. https://pmc.ncbi.nlm.nih.gov/articles/PMC12603170/
6. Kiran S, Srinivas S, Vasudevan K. Burden of mortality and morbidity caused by snakebites contributes to economic loss in a rural population in India. *Toxins (Basel).* 2026;18(6):250. doi:10.3390/toxins18060250. PMID 42347504.
7. Majumder D, Sinha A, Bhattacharya SK, Ram R, Dasgupta U, Ram A. Epidemiological profile of snake bite in South 24 Parganas district of West Bengal with focus on underreporting of snake bite deaths. *Indian J Public Health.* 2014;58(1):17-21. doi:10.4103/0019-557X.128158. PMID 24748352. *(PubMed lists Majumder first; Crossref lists Sinha as first author. Check the journal byline.)*
8. Hati AK, Mandal M, De MK, Mukherjee H, Hati RN. Epidemiology of snake bite in the district of Burdwan, West Bengal. *J Indian Med Assoc.* 1992;90(6):145-7. PMID 1522302 (no DOI).
9. Vaiyapuri S, Vaiyapuri R, Ashokan R, et al. Snakebite and its socio-economic impact on the rural population of Tamil Nadu, India. *PLoS One.* 2013;8(11):e80090. doi:10.1371/journal.pone.0080090. PMID 24278244.
10. Farooqui JM, Mukherjee BB, Manjhi SN, Farooqui AA, Datir S. Incidence of fatal snake bite in Loni, Maharashtra: an autopsy based retrospective study (2004-2014). *J Forensic Leg Med.* 2016;39:61-4. doi:10.1016/j.jflm.2016.01.013. PMID 26854851.
11. Kadam P, Patel B, Gopalakrishnan M, et al. Reported snakebite mortality and state compensation payments in Madhya Pradesh, India, from 2020 to 2022. *Trans R Soc Trop Med Hyg.* 2025;119(2):158-165. doi:10.1093/trstmh/trae045. PMID 39105603. Corrigendum (affiliation only): 2024;118(12):832, doi:10.1093/trstmh/trae099, PMID 39450558.
12. Menon JC, Jaya AM, Sivanandan H, et al. The final frontier: can Kerala lay out a roadmap to a 'zero snakebite deaths initiative' for India? *Trop Med Health.* 2026;54(1):112. doi:10.1186/s41182-026-00989-5. PMID 42260676.
13. Rubeshkumar P, Sakthivel M, Venkatasamy V, Ponnaiah M, Murhekar M. Secular trends of grossly underreported snakebite burden in India, 2009-2018: analysis of data from India's National Health Profile. *Trans R Soc Trop Med Hyg.* 2021;115(5):557-560. doi:10.1093/trstmh/trab050. PMID 33823554.
14. Dodda Basava J, Nagendraswamy C, Karun KM, Kothiwale VA, Vastrad P, Barvaliya MJ. Geospatial analysis of snakebite incidence rate in Karnataka. *Wilderness Environ Med.* 2026;37(3):341-349. doi:10.1177/10806032251413140. PMID 41575973.
15. Shewale AD, Mishra D, Tiwari S, Nale TN, Kuwatada J, Khandelwal N. Implementing interventions under "National Action Plan for Snakebite Envenoming (NAPSE) in India". *Trop Med Infect Dis.* 2025;10(5):132. doi:10.3390/tropicalmed10050132. PMID 40423362.
16. GBD 2019 Snakebite Envenomation Collaborators. Global mortality of snakebite envenoming between 1990 and 2019. *Nat Commun.* 2022;13(1):6160. doi:10.1038/s41467-022-33627-9. PMID 36284094.
17. Global Burden of Disease Collaborative Network. GBD 2023 Results. Seattle: IHME; 2024. https://vizhub.healthdata.org/gbd-results/ (local download `data_raw/gbd/IHME-GBD_2023_DATA-467618ec-1.csv`).
18. Ediriweera DS, Kasturiratne A, Pathmeswaran A, et al. Estimates of global burden of snakebite: a literature review and geostatistical modelling study. *PLoS Med.* 2026;23(8):e1005201. doi:10.1371/journal.pmed.1005201. PMID 42640884.
19. Kasturiratne A, Wickremasinghe AR, de Silva N, et al. The global burden of snakebite: a literature analysis and modelling based on regional estimates of envenoming and deaths. *PLoS Med.* 2008;5(11):e218. doi:10.1371/journal.pmed.0050218. PMID 18986210.
20. World Health Organization. Snakebite envenoming [fact sheet, 17 Sep 2026]. https://www.who.int/news-room/fact-sheets/detail/snakebite-envenoming
21. National Crime Records Bureau. *Accidental Deaths & Suicides in India* 2014, 2015, 2018-2024. New Delhi: MHA. https://ncrb.gov.in/accidental-deaths-suicides-india (local PDFs in `data_raw/ncrb/` and `data_raw/downloads_2026_11/`). ADSI 2016 and 2017 are not held locally.
22. Central Bureau of Health Intelligence. *National Health Profile* 2019, 2020, 2021, 2023. New Delhi: DGHS, MoHFW. https://cbhidghs.mohfw.gov.in/publications/national-health-profile
23. Office of the Registrar General, India. *Report on Medical Certification of Cause of Death* 2016-2024. https://censusindia.gov.in/census.website/data/mccdrep
24. Office of the Registrar General, India. *SRS Causes of Death Statistics* 2017-19, 2021-23, 2022-24. https://censusindia.gov.in/census.website/data/SRSCOD
25. Centre for One Health, NCDC. *National Action Plan for Prevention and Control of Snakebite Envenoming (NAPSE).* New Delhi: DGHS, MoHFW; 2024. Original URL now 404. Archived: http://web.archive.org/web/20250729154114/https://ncdc.mohfw.gov.in/wp-content/uploads/2024/07/NATIONAL-ACTION-PLAN-FOR-PREVENTION-AND-CONTROL-OF-SNAKEBITE-ENVENOMING-NAPSE.pdf

## 3. National series side by side (deaths per year)

| Year | NCRB (police) | NHP (public facility, T63.0) | MCCD (X20-X27) | IHIP | MDS / model |
|---|---:|---:|---:|---:|---|
| 2014 | 7,846 | - | - | - | MDS 61,200 |
| 2015 | 8,554 | - | - | - | MDS proj. 62,300 |
| 2016 | n/a (not held) | 1,068 (secondary) | 2,408 | - | MDS proj. 62,000 |
| 2017 | n/a (not held) | 1,060 | 1,577 | - | MDS proj. 61,400 |
| 2018 | 8,962 | 887 (prov. 885) | 1,875 | - | MDS proj. 60,300 |
| 2019 | 9,224 | 1,700 (prov. 3,163) | 1,692 | - | MDS proj. 59,800; GBD 51,100 |
| 2020 | 9,822 | 626 (prov.) | 1,475 | - | GBD-VAC 53,946 |
| 2021 | 10,382 | 600 | 1,132 | - | GBD-VAC 58,581 |
| 2022 | 10,096 | 525 (prov.) | 1,638 | - | GBD-VAC 53,880 |
| 2023 | 10,118 | - | 1,639 | 183 (secondary) | GBD-VAC 54,464 |
| 2024 | 9,803 | - | 1,393 | 370 (primary) / 375 (secondary) | - |
| 2025 | - | - | - | 429-431 (secondary) | - |

GBD-VAC = GBD 2023 venomous animal contact, all species.

## 4. State-level triangulation (where three or more systems overlap)

| State | NCRB police | NHP facility | Other | MDS rate (2010-14) |
|---|---|---|---|---|
| Madhya Pradesh | 2,512 (2020), 2,732 (2021), 2,487 (2022) | 5 (2021), 2 (2022) | Compensation 3,019 (FY20-21), 2,760 (FY21-22) | 6.0 /100k |
| Kerala | 34 (2020), 33 (2021), 22 (2022), 19 (2023), 51 (2024) | 0 (2021), 0 (2022) | Forest Dept compensation 52 (2020-21), 65 (2021-22), 34 (2025) [secondary]; ICMR "31" (2024-25); IHIP 2 (2025) [secondary] | 0.5 /100k |
| Tamil Nadu | 698 (2021), 698 (2022), 541 (2023), 449 (2024) | 160 (2021), 176 (2022) | IHIP study: 100 deaths over Jan 2022 - May 2025 (ASMR 0.14) | 3.0 /100k |
| Karnataka | 698 (2021), 688 (2022), 720 (2023), 497 (2024) | 36 (2021), 32 (2022) | IHIP 160 (2025) [secondary] | 2.9 /100k |
| Bihar | 216 (2021), 311 (2022), 365 (2023), 478 (2024) | 17 (2021), 0 (2022) | SmartVA 4.4 /100k (2012-14) | 8.9 /100k |
| West Bengal | 537 (2021), 478 (2022) | NA (2021, 2022) | Survey: only 7.23% of deaths officially reported | 2.9 /100k |

## 5. The most important discrepancies

1. **MDS/GBD (about 4-5 per 100,000; 50,000-60,000 deaths) versus the ICMR community survey (0.33 per 100,000; about 4,700 deaths if extrapolated).** This is the twelvefold conflict. Both claim to be community-based. The ICMR authors call the MDS "grossly overestimated". Their survey is interim, purposively sampled and excludes UP, MP and Bihar, and the authors themselves list ASHA under-ascertainment and COVID as reasons for low counts. Two checks weaken the ICMR side:
   - Their Kerala comparison ("2,100 MDS-implied deaths vs 31") applies a national rate to the state. MDS's own Kerala rate was 0.5 per 100,000 (Suraweera Table 3), about 175 deaths.
   - In Madhya Pradesh, postmortem-verified *paid compensation claims alone* give about 3.3-3.6 per 100,000. That is 10-11 times the ICMR pooled rate, and 55-60% of MDS's MP rate (6.0).

   A reconciliation model that uses compensation as a lower bound can arbitrate between the two.
2. **Government systems disagree with each other by 20-30x, and the gap is driven by states.** NCRB police counts run at about 10,000 per year. NHP records about 500-1,700, MCCD 1,100-2,400 (all venomous animals) and IHIP about 370-430. MP shows the gap most clearly: police record about 2,500 deaths and compensation pays about 2,800-3,000, against 2-5 in NHP. Tamil Nadu runs the other way: police record 450-700 per year, against about 29 per year in the state's own IHIP-based paper. Completeness differs by system *and* by state, so the model needs source x state bias terms, not one national under-reporting factor. Empirical anchors for those terms already exist: government hospital reports captured 10% of MDS in-hospital deaths (Suraweera Table 4), official reports captured 7.23% of surveyed deaths in South 24 Parganas, and district hospital records captured about 17% in Jagtial.
3. **NAPSE has no numeric baseline for its 2030 "halve the deaths" target, and its own figures conflict.** It cites "about 2000 deaths" per year (CBHI 2016-20), then 5,343 deaths over 2016-20 (about 1,069 per year). The 5,343 total matches the NHP year totals. It also quotes 1,000-2,500, about 50,000 and about 58,000 elsewhere. States are told to "estimate burden ... for baseline assessment". Depending on which number serves as the baseline, the 2030 ceiling falls anywhere from about 185 deaths a year (half of IHIP's 370 for 2024) to 29,000 (half of the MDS's 58,000). That makes the reconciliation directly policy-relevant (NAPSE decision analysis).
4. Smaller points to handle in the data pipeline:
   - Media and some papers quote NCRB *cases* as deaths (10,085 for 2022; 10,144 for 2023). The death totals are 10,096 and 10,118.
   - NHP provisional and final totals differ by up to 1.9x (2019: 3,163 provisional, 1,700 final).
   - The Kadam abstract (5,728) disagrees with its own Table 1 (5,779).
   - The MCCD category includes non-snake venomous animals.
   - GBD 2023 public results are for venomous animal contact, not snakebite.

## 6. Existing work that could pre-empt a reconciliation paper

Searched PubMed (several Boolean queries, ~400 records screened by title), the web (standard and extended search) and Crossref. **No published formal reconciliation or Bayesian multi-source fusion of Indian snakebite mortality was found.** The closest items:

- **Ediriweera et al. 2026, PLoS Med** (doi:10.1371/journal.pmed.1005201). A global geostatistical model whose S4 Appendix Table B already reports India under three data-source scenarios (2,300 / 37,600 / 70,100). It shows the spread but does not reconcile Indian sources or estimate source-specific bias. This is the most serious overlap. A reconciliation paper must cite it and position against it: India-specific, multiple government systems, state level, explicit bias terms.
- **Suraweera et al. 2020, eLife.** Table 4 is a state-by-state completeness comparison of government hospital reports against MDS (10% national). This is a one-source-pair precursor.
- **Menon et al. 2025, Nat Commun** (ICMR NTF). Openly disputes the MDS. The authors say the final report will give state-specific estimates and include West Bengal and Meghalaya. That final report, or an ICMR rebuttal and commentary exchange with the MDS group, is the most likely near-term pre-emption risk.
- **Kiran et al. 2026, Toxins.** Discusses MDS "overestimate" against the ICMR figure, and compares hospital with community data in one district.
- **Rubeshkumar et al. 2021** analyses NHP trends only.
- **Bhaumik, Norton, Jagnoor 2020, F1000Research** (doi:10.12688/f1000research.21924.2, PMID 32399199). A *protocol* for a systematic review of snakebite burden in India, with a planned state-level meta-analysis of community mortality. No results paper was found on PubMed or the web. It could still appear, possibly as part of a thesis (not verified).
- **Jaybhaye et al. 2025, Indian J Forensic Med Pathol** 19(1):85-99 (doi:10.21088/ijfmp.0974.3383.19126.11; Crossref-verified; PROSPERO CRD420251168454 as stated on the journal page). A systematic review dominated by hospital series and treatment outcomes. It does not pool or reconcile national estimates.
- **Afroz et al. 2024, PLoS NTD** (doi:10.1371/journal.pntd.0012080). A global meta-analysis: pooled mortality 0.33 per 100,000 globally and 0.96 for Asia. Not India-specific.
- **Huang, Brown, Blangiardo 2025, Spat Spatiotemporal Epidemiol** (doi:10.1016/j.sste.2025.100738). A spatial case-crossover analysis of MDS snakebite deaths. This is a methods precedent from the MDS group, not a reconciliation.
- **GBD 2019 Snakebite Collaborators 2022.** Single-model estimate.

**PROSPERO:** the new PROSPERO site is a JavaScript application. The direct record URLs (`/PROSPERO/view/CRD420251168454`) return only a 1.3 kB shell to curl, so no PROSPERO search could be run. **A manual search in a browser is needed** for terms such as snakebite / snake bite / envenom* AND India AND mortality. Also confirm what CRD420251168454 covers.

## 7. UNVERIFIED — needs manual check

| Item | Claimed value | Why unverified | Secondary source |
|---|---|---|---|
| IHIP national 2023 / 2024 / 2025 (Parliament replies) | 183 deaths; 375 (RS) or 370 (LS); 429 (RS) or 431 (LS); cases 86,294 / 120,982 / 140,302 | eparlib.sansad.in refused connections (AU768, AU1060 PDFs) | South First; Kashmir Life; Newsmeter |
| IHIP state 2025 | Karnataka 160, West Bengal 65, AP 13, J&K 8, Kerala 2, Telangana 0 | same | same |
| NHP 2016 | 178,433 cases; 1,068 deaths | CBHI NHP 2018 e-book page now 404; NHP 2018 PDF not on the CBHI listing | web-search index of the CBHI page; consistent with NAPSE's 5,343 for 2016-20 |
| Kerala Forest Department compensation deaths | 123 (2018-19), 52 (2020-21), 65 (2021-22), 34 (2025) | departmental data not seen | Menon et al. 2026, Trop Med Health |
| Odisha "800-900 deaths per annum" | - | no source given | Menon et al. 2026 |
| Maharashtra notification: "1.29 lakh cases, 656 deaths in 3 years" | - | news only | Free Press Journal |
| Karnataka 2023 / 2024 state health department | 19 / 100 deaths | news only | Deccan Herald; South First |
| GBD snake-specific (not venomous-animal) results after GBD 2019 | - | not in the local GBD 2023 download; needs an IHME request or the GBD 2019 paper's Supplementary Table 5 | - |
| WHO India-specific estimate | none independent | the fact sheet only restates MDS | - |
| Roshnath et al., Kannur (Kerala) compensation study | cited in Menon 2025 | not found on PubMed | - |
| PROSPERO record CRD420251168454 and any other India snakebite registrations | - | site needs a browser | journal web page (rfppl.co.in) |
| ICMR survey site-level study years | "one year per site" | Supplementary Table 1 not downloaded | - |
| Vaiyapuri 2013 "deaths ... 0.45% of the population" | - | metric unclear in abstract | - |
| Majumder vs Sinha first authorship (S07) | - | PubMed and Crossref disagree | - |

## 8. Notes for the model specification (from the matrix)

- **Independent likelihood blocks:** (a) MDS verbal autopsy (S01/S02; age-sex-state-year), (b) NCRB police (S13, state-year), (c) NHP facility (S14, state-year), (d) MCCD (S16, state-year; needs a snake share), (e) IHIP (S18 and S04, 2022+), (f) community surveys (S05, S03, S06-S08), (g) compensation (S11, S12) as **lower bounds** (censored likelihood).
- **Not independent:** GBD (S19, S20), WHO (S23) and NAPSE (S24) restate or derive from (a) or (c). Use them for validation, not as data.
- **Bias-term priors with empirical anchors:** facility completeness of 10% (S02d), 7.23% (S07) and ~17% (S06). The state x source pattern in section 4 argues for hierarchical source-by-state completeness rather than one national factor.
- **Gaps to fill before modelling:** NCRB ADSI 2016 and 2017 PDFs; NHP 2018 (2016 data) and NHP 2022 or later (2019-20 finals and 2023+ data); state rows of the MCCD Table 4 (same PDFs); GBD 2019 Supplementary Table 5 (state snakebite estimates); ICMR Supplementary Table 1.
