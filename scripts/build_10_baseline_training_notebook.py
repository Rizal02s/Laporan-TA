from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "10_baseline_training.ipynb"

nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "Python (VAEP-Track)",
    "language": "python",
    "name": "vaep-track",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.13"}

nb["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Baseline gegenpressing detection

Notebook ini membandingkan logistic regression dan XGBoost pada fitur
operasional. Split tetap berbasis pertandingan dari notebook 07. Threshold
dipilih hanya menggunakan validation; test tidak digunakan untuk tuning.

Eksekusi saat anotasi belum penuh adalah **smoke test**, bukan hasil penelitian
final. Ubah `FINAL_RUN = True` hanya setelah quality gate seluruh anotasi lulus."""
    ),
    nbf.v4.new_code_cell(
        """from pathlib import Path
import sys

import pandas as pd
from IPython.display import display

PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'src').exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.baseline_training import (
    baseline_readiness,
    prepare_baseline_dataset,
    run_baseline_training,
)
from src.research_readiness import build_model_manifest

PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
ARTIFACT_DIR = PROJECT_ROOT / 'artifacts' / 'baseline_smoke'
FINAL_RUN = False"""
    ),
    nbf.v4.new_code_cell(
        """episodes = pd.read_csv(PROCESSED_DIR / 'episode_manifest.csv')
annotations = pd.read_csv(PROCESSED_DIR / 'gegenpressing_annotation_manifest.csv')
features = pd.read_csv(PROCESSED_DIR / 'gegenpressing_baseline_features.csv')

model_manifest = build_model_manifest(episodes, annotations)
dataset = prepare_baseline_dataset(features, model_manifest)
readiness = baseline_readiness(annotations, dataset)

print('Final-training readiness:')
display(readiness.to_frame())
print('Usable labels:', int(dataset['eligible_for_detection_training'].sum()))
print('Mode:', 'FINAL' if FINAL_RUN else 'SMOKE TEST')"""
    ),
    nbf.v4.new_code_cell(
        """metrics, predictions, readiness = run_baseline_training(
    dataset,
    annotations,
    ARTIFACT_DIR,
    final_run=FINAL_RUN,
    random_state=42,
)

display(metrics[[
    'model', 'split', 'samples', 'positive_rate',
    'threshold', 'precision', 'recall', 'f1', 'roc_auc', 'pr_auc',
]])
print('Artifacts:', ARTIFACT_DIR)
if not FINAL_RUN:
    print('PERINGATAN: metrik pilot tidak boleh dilaporkan sebagai hasil final.')"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
