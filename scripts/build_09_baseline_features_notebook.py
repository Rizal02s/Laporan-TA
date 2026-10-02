from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "09_baseline_feature_extraction.ipynb"

nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "Python (VAEP-Track)",
    "language": "python",
    "name": "vaep-track",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.13"}

nb["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Baseline feature extraction

Notebook ini mengekstrak fitur operasional gegenpressing untuk seluruh queue
anotasi. Fitur hanya berasal dari tracking pada dua detik setelah loss. Outcome
quick regain dan label manual tidak digunakan selama ekstraksi, sehingga tidak
terjadi target leakage.

Metodologi tidak berubah: fitur mencakup jarak, approach rate, jumlah presser,
compactness, dan durasi tekanan. Tabel ini disiapkan untuk baseline setelah
anotasi penuh selesai."""
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

from src.gegenpressing_features import (
    BASELINE_FEATURE_COLUMNS,
    audit_baseline_feature_table,
    build_baseline_feature_table,
)

DATA_DIR = PROJECT_ROOT / 'data' / 'sportec_idsse'
PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
ANNOTATION_PATH = PROCESSED_DIR / 'gegenpressing_annotation_manifest.csv'
FEATURE_PATH = PROCESSED_DIR / 'gegenpressing_baseline_features.csv'"""
    ),
    nbf.v4.new_code_cell(
        """annotations = pd.read_csv(ANNOTATION_PATH)
features = build_baseline_feature_table(annotations, DATA_DIR)
features.to_csv(FEATURE_PATH, index=False)

print('Candidates:', len(annotations))
print('Feature rows:', len(features))
print('Feature columns:', len(BASELINE_FEATURE_COLUMNS))
print('Saved:', FEATURE_PATH)"""
    ),
    nbf.v4.new_code_cell(
        """checks = audit_baseline_feature_table(features, annotations)
display(checks.to_frame())
assert checks.all(), 'Audit baseline feature table gagal.'

missing = features[BASELINE_FEATURE_COLUMNS].isna().sum()
print('Missing values by feature:')
display(missing[missing.gt(0)].rename('missing').to_frame())
print('Feature summary:')
display(features[BASELINE_FEATURE_COLUMNS].describe().T)"""
    ),
    nbf.v4.new_code_cell(
        """labels = annotations[[
    'candidate_id',
    'is_gegenpressing',
    'annotation_confidence',
]].copy()
audit = features.merge(labels, on='candidate_id', how='left', validate='one_to_one')
completed = audit[audit['is_gegenpressing'].notna()].copy()
usable = completed[completed['is_gegenpressing'].isin([0, 1])].copy()

print('Completed annotations:', len(completed))
print('Usable binary labels:', len(usable))
print('Remaining annotations:', len(audit) - len(completed))
if len(usable):
    display(
        usable['is_gegenpressing']
        .astype(int)
        .value_counts()
        .sort_index()
        .rename('count')
        .to_frame()
    )
print('Status: features ready; final baseline waits for full annotation.')"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
