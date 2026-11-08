"""Re-run the analysis: python run_pipeline.py [--refit] [--panel]
  default : model inputs, completeness, NAPSE decision analysis and figures from the committed posterior draws, then verify.py
  --refit : refit all seven Bayesian models first (NumPyro, about 1-2 min; pip install -r requirements-bayes.txt)
  --panel : rebuild data/ from the source PDFs and PMC full texts in data_raw/ (see README; pip install pymupdf)"""
import pathlib, subprocess, sys
R = pathlib.Path(__file__).resolve().parent
run = lambda *a: subprocess.run([sys.executable, *map(str, a)], cwd=R, check=True)
if "--panel" in sys.argv: run("src/extract_ncrb_adsi_snakebite.py"); run("src/build_panel.py")
run("src/model_inputs.py")
if "--refit" in sys.argv: run("src/reconcile_model.py")
run("src/completeness.py", "S0", "S3", "S4"); run("src/napse_decision.py"); run("src/figures.py"); run("verify.py")
