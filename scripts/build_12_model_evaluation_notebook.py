from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "12_model_evaluation.ipynb"

nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "Python (VAEP-Track)",
    "language": "python",
    "name": "vaep-track",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.13"}

nb["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Match-level model evaluation

Notebook ini menggabungkan prediksi baseline dan temporal GNN. Threshold setiap
model berasal dari validation dan tidak diubah pada test. Kandidat yang dinilai
harus identik untuk seluruh model.

Output saat ini adalah smoke evaluation pada pilot, bukan hasil final."""
    ),
    nbf.v4.new_code_cell(
        """from pathlib import Path
import sys

from IPython.display import display

PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'src').exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.final_reporting import build_training_summary
from src.model_evaluation import save_evaluation_artifacts

BASELINE_PREDICTIONS = PROJECT_ROOT / 'artifacts' / 'baseline_smoke' / 'predictions.csv'
GNN_PREDICTIONS = PROJECT_ROOT / 'artifacts' / 'temporal_gnn_smoke' / 'predictions.csv'
OUTPUT_DIR = PROJECT_ROOT / 'artifacts' / 'evaluation_smoke'
FINAL_RUN = False"""
    ),
    nbf.v4.new_code_cell(
        """predictions, split_metrics, match_metrics, checks = save_evaluation_artifacts(
    [BASELINE_PREDICTIONS, GNN_PREDICTIONS],
    OUTPUT_DIR,
    final_run=FINAL_RUN,
)

display(checks.to_frame())
print('Split metrics:')
display(split_metrics[[
    'model', 'split', 'samples', 'positive_rate',
    'precision', 'recall', 'f1', 'roc_auc', 'pr_auc',
]])
print('Match-level test metrics:')
display(match_metrics[match_metrics['split'].eq('test')])
print('Artifacts:', OUTPUT_DIR)
summary_path = build_training_summary(
    PROJECT_ROOT / 'artifacts' / 'baseline_smoke',
    PROJECT_ROOT / 'artifacts' / 'temporal_gnn_smoke',
    OUTPUT_DIR,
    OUTPUT_DIR / 'training_summary.md',
    final_run=FINAL_RUN,
)
print('Summary:', summary_path)
print('PERINGATAN: evaluasi pilot tidak boleh dilaporkan sebagai hasil final.')"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
