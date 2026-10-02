from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "07_research_readiness_and_split.ipynb"

nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "Python (VAEP-Track)",
    "language": "python",
    "name": "vaep-track",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.13"}

nb["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Kesiapan penelitian dan pembagian data

Notebook ini merangkum bukti kelayakan IDSSE, mengunci pembagian
train/validation/test pada tingkat pertandingan, dan menjaga label
`is_gegenpressing` terpisah dari outcome `label_regain_5s`. Label `-1`
tetap disimpan sebagai kasus ragu dan tidak digunakan untuk training."""
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

from src.research_readiness import (
    DEFAULT_MATCH_SPLIT,
    build_match_split_manifest,
    build_model_manifest,
    validate_model_manifest,
)

PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
EPISODE_PATH = PROCESSED_DIR / 'episode_manifest.csv'
ANNOTATION_PATH = PROCESSED_DIR / 'gegenpressing_annotation_manifest.csv'
MODEL_MANIFEST_PATH = PROCESSED_DIR / 'model_episode_manifest.csv'
MATCH_SPLIT_PATH = PROCESSED_DIR / 'match_split_manifest.csv'"""
    ),
    nbf.v4.new_code_cell(
        """episodes = pd.read_csv(EPISODE_PATH)
annotations = pd.read_csv(ANNOTATION_PATH)

model_manifest = build_model_manifest(
    episodes,
    annotations,
    DEFAULT_MATCH_SPLIT,
)
match_split_manifest = build_match_split_manifest(model_manifest)

model_manifest.to_csv(MODEL_MANIFEST_PATH, index=False)
match_split_manifest.to_csv(MATCH_SPLIT_PATH, index=False)

print('Strict-valid model episodes:', len(model_manifest))
print('Model manifest:', MODEL_MANIFEST_PATH)
print('Match split manifest:', MATCH_SPLIT_PATH)"""
    ),
    nbf.v4.new_code_cell(
        """display(match_split_manifest)

split_summary = (
    model_manifest.groupby('split', observed=True)
    .agg(
        matches=('match_id', 'nunique'),
        strict_valid_episodes=('candidate_id', 'size'),
        quick_regain_positive=('label_regain_5s', 'sum'),
        annotated_usable=('eligible_for_detection_training', 'sum'),
    )
)
split_summary['quick_regain_negative'] = (
    split_summary['strict_valid_episodes']
    - split_summary['quick_regain_positive']
)
split_summary['episode_share_percent'] = (
    100 * split_summary['strict_valid_episodes']
    / split_summary['strict_valid_episodes'].sum()
).round(2)
display(split_summary)"""
    ),
    nbf.v4.new_code_cell(
        """pilot = annotations[
    annotations['pilot_selected'].astype(str).str.lower().eq('true')
    & annotations['is_gegenpressing'].notna()
].copy()
pilot['is_gegenpressing'] = pilot['is_gegenpressing'].astype(int)

print('Pilot annotations:', len(pilot))
display(
    pilot['is_gegenpressing']
    .value_counts()
    .sort_index()
    .rename('count')
    .to_frame()
)
print('Behavior label versus quick-regain outcome:')
display(pd.crosstab(
    pilot['is_gegenpressing'],
    pilot['quick_regain_success'],
    margins=True,
))
print('Usable manual labels by split:')
usable = model_manifest[model_manifest['eligible_for_detection_training']]
display(pd.crosstab(
    usable['split'],
    usable['gegenpressing_label'],
    margins=True,
))"""
    ),
    nbf.v4.new_code_cell(
        """checks = validate_model_manifest(model_manifest)
display(checks.to_frame())
assert checks.all(), 'Ada pemeriksaan manifest yang gagal.'

print('Kesimpulan kesiapan:')
print('- Pembagian pertandingan bebas kebocoran antarsplit.')
print('- Outcome quick regain dan label gegenpressing tetap terpisah.')
print('- Label ragu dikeluarkan dari training.')
print('- Pilot cukup untuk kalibrasi prosedur, belum cukup untuk training final.')"""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
