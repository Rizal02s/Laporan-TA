from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "08_full_gegenpressing_annotation.ipynb"

nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {
    "display_name": "Python (VAEP-Track)",
    "language": "python",
    "name": "vaep-track",
}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.13"}

nb["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Anotasi penuh gegenpressing

Notebook ini melanjutkan pilot ke seluruh queue 264 transisi strict-valid.
Metodologi tidak berubah: keputusan perilaku hanya memakai window `T0` sampai
`T0+2s`, sedangkan quick regain lima detik tetap menjadi outcome terpisah dan
disembunyikan selama pengambilan keputusan.

Pekerjaan dibagi menjadi batch 25 sampel. Setiap klik label langsung menyimpan
CSV. Label `Ragu` memerlukan catatan dan tidak akan dipakai untuk training."""
    ),
    nbf.v4.new_markdown_cell(
        """## Pedoman keputusan

- **Gegenpressing (1):** sedikitnya satu pemain segera dan sengaja menutup
  pembawa bola, atau beberapa pemain menutup ruang serta opsi umpan di sekitar
  bola. Tekanan harus tampak berkelanjutan.
- **Bukan (0):** respons dominan adalah mundur atau reorganisasi, tidak ada
  tekanan segera, atau kedekatan terjadi karena bentuk pertahanan biasa.
- **Ragu (-1):** rebound, bola udara, duel tidak jelas, pembawa bola tidak dapat
  diidentifikasi, atau bukti visual tidak cukup.

Cue jarak, approach rate, jumlah presser, compactness, dan durasi hanya alat
bantu. Cue tidak boleh digunakan sebagai label otomatis."""
    ),
    nbf.v4.new_code_cell(
        """from functools import lru_cache
from pathlib import Path
import math
import sys

import ipywidgets as widgets
import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import clear_output, display

PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'src').exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.gegenpressing_annotation import (
    AnnotationConfig,
    annotation_progress,
    compute_annotation_context,
    initialize_annotation_manifest,
    plot_annotation_context,
    record_annotation,
)
from src.idsse_episode_dataset import load_match

DATA_DIR = PROJECT_ROOT / 'data' / 'sportec_idsse'
PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'
EPISODE_MANIFEST_PATH = PROCESSED_DIR / 'episode_manifest.csv'
ANNOTATION_PATH = PROCESSED_DIR / 'gegenpressing_annotation_manifest.csv'
CONFIG = AnnotationConfig()
ANNOTATOR = 'rizal'
BATCH_SIZE = 25"""
    ),
    nbf.v4.new_code_cell(
        """annotations = initialize_annotation_manifest(
    EPISODE_MANIFEST_PATH,
    ANNOTATION_PATH,
    samples_per_match=40,
    random_state=42,
    min_spacing_seconds=2.0,
)
full_queue = annotations.sort_values('annotation_order').copy()
total_batches = math.ceil(len(full_queue) / BATCH_SIZE)

print('Full queue distribution by match:')
display(full_queue.groupby('match_id').size().rename('count').to_frame())
print('Current progress:')
display(annotation_progress(annotations).to_frame('count'))
print('Batches:', total_batches, '| batch size:', BATCH_SIZE)
print('Annotation file:', ANNOTATION_PATH)"""
    ),
    nbf.v4.new_markdown_cell(
        """## Panel anotasi

Gunakan slider untuk meninjau ulang sampel tertentu. Tombol **Belum berikutnya**
melompat ke sampel belum berlabel. Confidence menunjukkan keyakinan pada
keputusan visual, bukan kekuatan cue."""
    ),
    nbf.v4.new_code_cell(
        """@lru_cache(maxsize=1)
def load_cached_match(match_id):
    return load_match(DATA_DIR, match_id)

def row_index_at(position):
    return int(full_queue.index[position - 1])

def first_unlabeled_position():
    for position, idx in enumerate(full_queue.index, start=1):
        if pd.isna(annotations.loc[idx, 'is_gegenpressing']):
            return position
    return 1

def next_unlabeled_position(current_position):
    positions = list(range(current_position + 1, len(full_queue) + 1))
    positions += list(range(1, current_position + 1))
    for position in positions:
        idx = row_index_at(position)
        if pd.isna(annotations.loc[idx, 'is_gegenpressing']):
            return position
    return current_position

candidate_selector = widgets.IntSlider(
    value=first_unlabeled_position(),
    min=1,
    max=len(full_queue),
    step=1,
    description='Sampel',
    continuous_update=False,
    layout=widgets.Layout(width='72%'),
)
confidence = widgets.ToggleButtons(
    options=[('Rendah', 1), ('Sedang', 2), ('Tinggi', 3)],
    value=2,
    description='Confidence',
)
notes = widgets.Textarea(
    description='Catatan',
    placeholder='Alasan keputusan atau penyebab ragu',
    layout=widgets.Layout(width='86%', height='70px'),
)
positive_button = widgets.Button(description='Gegenpressing', button_style='success')
negative_button = widgets.Button(description='Bukan', button_style='danger')
uncertain_button = widgets.Button(description='Ragu', button_style='warning')
previous_button = widgets.Button(description='Sebelumnya')
next_button = widgets.Button(description='Berikutnya')
next_unlabeled_button = widgets.Button(description='Belum berikutnya', button_style='info')
view_output = widgets.Output()
status_output = widgets.Output()

def current_batch_bounds():
    batch_number = (candidate_selector.value - 1) // BATCH_SIZE + 1
    start = (batch_number - 1) * BATCH_SIZE
    end = min(start + BATCH_SIZE, len(full_queue))
    return batch_number, start, end

def show_current(*_):
    idx = row_index_at(candidate_selector.value)
    row = annotations.loc[idx]
    tracking, events = load_cached_match(row['match_id'])
    context = compute_annotation_context(row, tracking, events, CONFIG)
    with view_output:
        clear_output(wait=True)
        fig = plot_annotation_context(context)
        display(fig)
        plt.close(fig)
        display(context['summary'].to_frame('value'))
        existing = row['is_gegenpressing']
        print(f"Tersimpan: {existing if pd.notna(existing) else 'belum'}")
    notes.value = '' if pd.isna(row['annotation_notes']) else str(row['annotation_notes'])
    if pd.notna(row['annotation_confidence']):
        confidence.value = int(row['annotation_confidence'])

    batch_number, start, end = current_batch_bounds()
    batch_indices = full_queue.iloc[start:end].index
    with status_output:
        clear_output(wait=True)
        print(
            f'Batch {batch_number}/{total_batches} | '
            f'sampel {candidate_selector.value}/{len(full_queue)}'
        )
        display(annotation_progress(annotations.loc[batch_indices]).to_frame('batch'))
        print('Full queue:')
        display(annotation_progress(annotations).to_frame('count'))
        print('Label ragu wajib disertai catatan singkat.')

def save_label(label):
    if label == -1 and not notes.value.strip():
        with status_output:
            clear_output(wait=True)
            print('Tambahkan alasan singkat sebelum menyimpan label Ragu.')
        return
    idx = row_index_at(candidate_selector.value)
    record_annotation(
        annotations,
        idx,
        label,
        confidence.value,
        notes.value,
        ANNOTATOR,
        ANNOTATION_PATH,
    )
    target = next_unlabeled_position(candidate_selector.value)
    if target == candidate_selector.value:
        show_current()
    else:
        candidate_selector.value = target

positive_button.on_click(lambda _: save_label(1))
negative_button.on_click(lambda _: save_label(0))
uncertain_button.on_click(lambda _: save_label(-1))
previous_button.on_click(lambda _: setattr(
    candidate_selector,
    'value',
    max(candidate_selector.min, candidate_selector.value - 1),
))
next_button.on_click(lambda _: setattr(
    candidate_selector,
    'value',
    min(candidate_selector.max, candidate_selector.value + 1),
))
next_unlabeled_button.on_click(lambda _: setattr(
    candidate_selector,
    'value',
    next_unlabeled_position(candidate_selector.value),
))
candidate_selector.observe(show_current, names='value')

display(candidate_selector)
display(confidence, notes)
display(widgets.HBox([
    previous_button,
    negative_button,
    uncertain_button,
    positive_button,
    next_button,
    next_unlabeled_button,
]))
display(status_output, view_output)
show_current()"""
    ),
    nbf.v4.new_markdown_cell(
        """## Audit progres dan quality gate

Jalankan cell berikut setiap selesai satu batch. Outcome quick regain baru
ditampilkan pada tahap audit. Jangan mengubah label perilaku agar sesuai dengan
outcome."""
    ),
    nbf.v4.new_code_cell(
        """saved = pd.read_csv(ANNOTATION_PATH)
print('Full queue progress:')
display(annotation_progress(saved).to_frame('count'))

completed = saved[saved['is_gegenpressing'].notna()].copy()
completed['is_gegenpressing'] = completed['is_gegenpressing'].astype(int)
if len(completed):
    print('Label by match:')
    display(pd.crosstab(
        completed['match_id'],
        completed['is_gegenpressing'],
        margins=True,
    ))
    print('Behavior label versus quick-regain outcome:')
    display(pd.crosstab(
        completed['is_gegenpressing'],
        completed['quick_regain_success'],
        margins=True,
    ))

uncertain_without_notes = completed[
    completed['is_gegenpressing'].eq(-1)
    & completed['annotation_notes'].fillna('').str.strip().eq('')
]
missing_confidence = completed[completed['annotation_confidence'].isna()]
invalid_labels = completed[~completed['is_gegenpressing'].isin([-1, 0, 1])]
duplicate_candidates = int(saved['candidate_id'].duplicated().sum())

quality_gate = pd.Series({
    'all_264_completed': len(completed) == len(saved),
    'both_binary_classes_present': {0, 1}.issubset(set(completed['is_gegenpressing'])),
    'uncertain_have_notes': len(uncertain_without_notes) == 0,
    'confidence_complete': len(missing_confidence) == 0,
    'labels_valid': len(invalid_labels) == 0,
    'candidate_id_unique': duplicate_candidates == 0,
}, name='passed')
print('Quality gate:')
display(quality_gate.to_frame())

usable = completed[completed['is_gegenpressing'].isin([0, 1])]
print('Usable binary labels:', len(usable))
if quality_gate['all_264_completed']:
    print('Queue selesai. Bekukan manifest sebelum training baseline.')
else:
    print('Belum siap training final. Selesaikan anotasi yang tersisa.')"""
    ),
    nbf.v4.new_markdown_cell(
        """## Syarat menuju training

Setelah semua 264 sampel selesai:

1. Tinjau ulang semua label ragu dan confidence rendah.
2. Bekukan salinan manifest beserta tanggal dan checksum.
3. Gunakan hanya label `0/1`; jangan mengubah `-1` menjadi negatif.
4. Pertahankan split pertandingan dari notebook 07.
5. Jalankan baseline feature-based sebelum temporal GNN."""
    ),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUTPUT)
print(OUTPUT)
