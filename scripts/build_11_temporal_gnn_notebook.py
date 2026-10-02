from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "11_temporal_gnn_training.ipynb"

nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "Python (VAEP-Track)",
    "language": "python",
    "name": "vaep-track",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.13"}

nb["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Temporal GNN training

Arsitektur mempertahankan graph pada seluruh 101 frame: dua GCN memproduksi
embedding setiap frame, mean pooling menggabungkan node valid, dan GRU memodelkan
urutan waktu sebelum klasifikasi biner. Split pertandingan sama dengan baseline.

Eksekusi saat ini adalah **smoke test**. Mode final ditolak otomatis sampai
seluruh anotasi dan minimum kelas per split memenuhi quality gate."""
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

from src.graph_cache import audit_graph_cache, build_graph_cache
from src.research_readiness import build_model_manifest
from src.temporal_gnn_training import prepare_gnn_dataset, train_temporal_gnn

DATA_DIR = PROJECT_ROOT / 'data' / 'sportec_idsse'
PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
GRAPH_CACHE_DIR = PROCESSED_DIR / 'graph_cache'
GRAPH_CACHE_MANIFEST_PATH = PROCESSED_DIR / 'graph_cache_manifest.csv'
ARTIFACT_DIR = PROJECT_ROOT / 'artifacts' / 'temporal_gnn_smoke'
FINAL_RUN = False"""
    ),
    nbf.v4.new_code_cell(
        """annotations = pd.read_csv(PROCESSED_DIR / 'gegenpressing_annotation_manifest.csv')
cache_manifest = build_graph_cache(
    annotations,
    DATA_DIR,
    GRAPH_CACHE_DIR,
    overwrite=False,
)
cache_manifest.to_csv(GRAPH_CACHE_MANIFEST_PATH, index=False)

cache_checks = audit_graph_cache(cache_manifest, annotations)
display(cache_checks.to_frame())
assert cache_checks.all(), 'Graph cache audit gagal.'
print('Cached graph sequences:', len(cache_manifest))"""
    ),
    nbf.v4.new_code_cell(
        """episodes = pd.read_csv(PROCESSED_DIR / 'episode_manifest.csv')
model_manifest = build_model_manifest(episodes, annotations)
dataset = prepare_gnn_dataset(model_manifest, cache_manifest)

metrics, predictions, history, readiness = train_temporal_gnn(
    dataset,
    annotations,
    GRAPH_CACHE_DIR,
    ARTIFACT_DIR,
    final_run=FINAL_RUN,
    random_state=42,
    batch_size=4,
    max_epochs=25 if not FINAL_RUN else 100,
    patience=6 if not FINAL_RUN else 15,
)

print('Final-training readiness:')
display(readiness.to_frame())
display(metrics[[
    'model', 'split', 'samples', 'positive_rate', 'threshold',
    'precision', 'recall', 'f1', 'roc_auc', 'pr_auc', 'loss',
]])
print('Best validation loss:', history['validation_loss'].min())
print('Artifacts:', ARTIFACT_DIR)
if not FINAL_RUN:
    print('PERINGATAN: metrik pilot tidak boleh dilaporkan sebagai hasil final.')"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
