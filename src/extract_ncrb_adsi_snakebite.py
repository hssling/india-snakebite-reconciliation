"""Extract NCRB ADSI 'Poisoning (Snake Bite)' state-wise deaths from local ADSI PDFs.

Source table: ADSI 'Cause-wise Number of Cases, Persons Injured and Died due to Other Causes'
(Table 1.11 in 2014-15, 1.9 in 2018-19, 1.10 in 2020-24), sub-block 'Poisoning (Snake Bite)'.
Output: data/ncrb_adsi_snakebite_state_year.csv. State rows are validated against the
TOTAL (ALL INDIA) row; a residual row is written when a multi-line state name was not parsed.
Usage: python -I src/extract_ncrb_adsi_snakebite.py
"""
import csv, os, re, sys
from pathlib import Path
import fitz  # PyMuPDF

ROOT = Path(os.environ.get("SNAKEBITE_RAW", Path(__file__).resolve().parents[1] / "data_raw"))
PDFS = {2014: ROOT / "ncrb/ADSI_2014.pdf", 2015: ROOT / "ncrb/ADSI_2015.pdf"}
PDFS.update({y: ROOT / f"ncrb/ADSI_{y}.pdf" for y in range(2018, 2025)})
OUT = Path(__file__).resolve().parents[1] / "data" / "ncrb_adsi_snakebite_state_year.csv"


def lines_of(page):
    words = sorted(page.get_text("words"), key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines, cur, cy = [], [], None
    for w in words:
        c = (w[1] + w[3]) / 2
        if cy is None or abs(c - cy) <= 4:
            cur.append(w); cy = c if cy is None else cy
        else:
            lines.append(cur); cur, cy = [w], c
    lines.append(cur)
    return [" ".join(x[4] for x in sorted(l, key=lambda w: w[0])) for l in lines]


def main():
  rows = []
  for year, pdf in PDFS.items():
      doc = fitz.open(pdf)
      for i, page in enumerate(doc):
          text = page.get_text()
          if "Poisoning (Snake Bite)" not in text or not ("State/UT" in text or "STATES" in text):
              continue
          tab = re.search(r"Table\s+([\d\.]+)", text)
          states, total = [], None
          L = lines_of(page)
          for li, s in enumerate(L):
              nn = re.match(r"^(\d{1,2})\s+((?:\d+\s+){7,}\d+)$", s)
              if nn and any("HAVELI" in x for x in L[max(0, li - 2):li + 3]):
                  # name split over two text lines (DNH & DD from 2020): numbers sit on their own line
                  n = [int(x) for x in nn.group(2).split()]
                  states.append(("D & N HAVELI AND DAMAN & DIU", n[0], n[-1]))
                  continue
              m = re.match(r"^(\d{1,2})\s+([A-Z&\.\(\)\- ]+?)\s+((?:\d+\s+){3,}\d+)$", s)
              if m:
                  n = [int(x) for x in m.group(3).split()]
                  states.append((m.group(2).strip(), n[0], n[-1]))
              t = re.match(r"^TOTAL \(ALL INDIA\)\s+([\d ]+)$", s)
              if t:
                  n = [int(x) for x in t.group(1).split()]
                  total = (n[0], n[-1])
          for st, cases, died in states:
              rows.append(dict(year=year, state=st, cases=cases, persons_died=died,
                               adsi_table=f"Table {tab.group(1) if tab else '?'} (Contd.) Poisoning (Snake Bite)",
                               pdf_page=i + 1, note=""))
          resid = total[1] - sum(d for _, _, d in states)
          resid_cases = total[0] - sum(c for _, c, _ in states)
          if resid or resid_cases:
              rows.append(dict(year=year, state="UNPARSED_RESIDUAL (multi-line UT name, e.g. DNH & DD)",
                               cases=total[0] - sum(c for _, c, _ in states), persons_died=resid,
                               adsi_table="derived", pdf_page=i + 1, note="ALL INDIA total minus parsed rows"))
          rows.append(dict(year=year, state="TOTAL (ALL INDIA)", cases=total[0], persons_died=total[1],
                           adsi_table=f"Table {tab.group(1) if tab else '?'} (Contd.) Poisoning (Snake Bite)",
                           pdf_page=i + 1, note="as printed"))
          print(year, "states", len(states), "ALL INDIA died", total[1], "residual deaths", resid, "residual cases", resid_cases)
          break

  with open(OUT, "w", newline="", encoding="utf-8") as f:
      w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
      w.writeheader(); w.writerows(rows)
  print("wrote", OUT, len(rows))


if __name__ == "__main__":
    main()
