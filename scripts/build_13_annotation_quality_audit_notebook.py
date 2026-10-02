from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "13_annotation_quality_audit.ipynb"

nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "Python (VAEP-Track)",
    "language": "python",
    "name": "vaep-track",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.13"}

nb["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Audit kualitas anotasi gegenpressing

Notebook ini memeriksa integritas label dan membuat review queue untuk label
`Ragu` atau confidence rendah. Review queue sengaja tidak memuat outcome quick
regain agar peninjauan ulang tidak mengubah label perilaku berdasarkan hasil."""
    ),
    nbf.v4.new_code_cell(
        """from pathlib import Path
import json
import sys

import pandas as pd
from IPython.display import display

PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'src').exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.annotation_audit import build_annotation_audit
from src.research_readiness import build_model_manifest

PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'artifacts' / 'annotation_audit_current'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)"""
    ),
    nbf.v4.new_code_cell(
        """annotations = pd.read_csv(
    PROCESSED_DIR / 'gegenpressing_annotation_manifest.csv'
)
episodes = pd.read_csv(PROCESSED_DIR / 'episode_manifest.csv')
model_manifest = build_model_manifest(episodes, annotations)

summary, review_queue, checks = build_annotation_audit(
    annotations,
    model_manifest,
)
summary.to_csv(OUTPUT_DIR / 'annotation_audit_summary.csv', index=False)
review_queue.to_csv(OUTPUT_DIR / 'annotation_review_queue.csv', index=False)
(OUTPUT_DIR / 'annotation_audit_checks.json').write_text(
    json.dumps({key: bool(value) for key, value in checks.items()}, indent=2),
    encoding='utf-8',
)

print('Quality checks:')
display(checks.to_frame())
print('Summary by match and split:')
display(summary)
print('Blinded review queue:', len(review_queue))
display(review_queue)
print('Artifacts:', OUTPUT_DIR)
if checks['all_annotations_completed']:
    print('Semua sampel sudah dianotasi; tinjau review queue sebelum training final.')
else:
    print('Audit sementara. Kembali ke notebook 08 untuk menyelesaikan queue.')"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
