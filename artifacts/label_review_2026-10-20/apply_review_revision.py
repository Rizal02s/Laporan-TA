"""Apply explicitly reviewed decisions with immutable backups and provenance."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
from src.annotation_audit import build_annotation_audit
from src.research_readiness import (
    build_model_manifest, build_match_split_manifest, validate_model_manifest,
)

REVIEW = Path(__file__).resolve().parent
PROCESSED = ROOT / "data/processed"
SOURCE = PROCESSED / "gegenpressing_annotation_manifest.csv"

# Decisions from visual review, not a function of model predictions or regain.
# Fields: candidate_id, original label, revised label, confidence, reasoning.
DECISIONS = {
    16: ("J03WMX_P1_F11238", 1, 0, 2,
         "Dalam 0-2 s, pemain biru dekat bola tetap memiliki ruang; pemain merah terdekat minimal 14,76 m. Panel lima waktu tidak menunjukkan respons tekanan segera terhadap pemain dekat bola atau penutupan opsi operan lokal yang jelas. Keputusan negatif berdasarkan interpretasi tracking, perlu konfirmasi manusia."),
    109: ("J03WOY_P1_F48730", 1, 0, 2,
          "Bola bergerak menjauh dari kelompok merah; jarak terdekat meningkat 16,33 menjadi 29,36 m. Panel lima waktu memperlihatkan pemisahan dari area bola tanpa respons tekanan segera yang jelas. Keputusan negatif berdasarkan tracking, perlu konfirmasi manusia."),
    259: ("J03WR9_P1_F16153", 1, 0, 2,
          "Pemain merah tetap jauh dari bola (minimum 18,05 m) dan lintasan umumnya menjauh dari sisi bola. Tidak tampak tekanan segera terhadap pemain dekat bola atau opsi operan lokal. Keputusan negatif berdasarkan tracking, perlu konfirmasi manusia."),
    31: ("J03WMX_P2_F104384", 1, -1, 1,
         "Tekanan langsung terhadap bola tidak terlihat, tetapi terdapat penjagaan lawan di area lain. Belum dapat membedakan tekanan terhadap opsi operan dari penjagaan biasa; jangan memutuskan negatif hanya karena cue bola nol."),
    85: ("J03WOH_P1_F50920", 1, -1, 1,
         "Bola berpindah di antara pemain biru tanpa cue dekat bola. Beberapa pemain merah tetap dekat lawan lain; kemungkinan tekanan terhadap penerima operan belum dapat dipastikan dari panel."),
    188: ("J03WQQ_P1_F71233", 1, -1, 1,
          "Jarak terhadap bola meningkat 11,61 menjadi 19,53 m tanpa pengejaran langsung yang jelas, tetapi terdapat penjagaan lawan/opsi operan. Bukti belum cukup untuk menetapkan 0 atau 1."),
    51: ("J03WN1_P1_F12950", 1, -1, 1,
         "Tidak terlihat tekanan dekat bola dan tracking berubah menjadi dead pada +0,72 s. Perlu memastikan konteks permainan, kesesuaian event, dan kelayakan kandidat; bukan otomatis negatif."),
    228: ("J03WR9_P2_F153808", 1, -1, 1,
          "Tidak terlihat tekanan dekat bola; jarak minimum 22,52 m dan event GENERIC:FairPlay pada +0,308 s. Makna kejadian dan kelayakan kandidat sebagai transisi perlu diverifikasi."),
    251: ("J03WR9_P2_F111335", 1, -1, 1,
          "Bola bergerak cepat menjauh dari pemain merah sehingga cue jarak nol. Belum jelas apakah terdapat upaya tekanan singkat di lokasi awal sebelum operan; perlu tinjauan urutan lebih rinci."),
    1: ("J03WMX_P2_F112306", 0, -1, 1,
        "Alasan garis pertahanan terlalu belakang tidak cukup untuk menolak gegenpressing. Lintasan menunjukkan satu pemain merah mengikuti area bola; perlu menilai tekanan individual, bukan posisi bek saja."),
    72: ("J03WOH_P2_F102262", 0, -1, 1,
         "Catatan awal menyebut throw-in; event BALL_OUT tercatat -1,535 s, tetapi tracking sebelum loss tetap alive. Perlu memeriksa jenis kejadian dan keselarasan waktu sebelum menentukan label perilaku."),
    193: ("J03WQQ_P1_F57778", 0, -1, 1,
          "Frame tepat sebelum loss berstatus dead dan frame loss alive. Kandidat mungkin merepresentasikan restart, bukan kehilangan penguasaan dalam permainan terbuka; kelayakan kandidat belum dipastikan."),
    219: ("J03WQQ_P1_F69088", 0, -1, 1,
          "Bola kemudian mati; event BALL_OUT pada +0,606 s berbeda dari tracking pertama dead pada +1,64 s. Perlu memastikan interval permainan aktif dan konteks transisi sebelum label definitif."),
}

source_bytes = SOURCE.read_bytes()
before_hash = hashlib.sha256(source_bytes).hexdigest()
expected_hash = json.loads((REVIEW / "provenance.json").read_text())["sha256"]
if before_hash != expected_hash:
    raise RuntimeError("Source annotations changed since reviewed snapshot; abort.")
reader = csv.DictReader(io.StringIO(source_bytes.decode("utf-8-sig")))
columns = reader.fieldnames
original = list(reader)
revised = [dict(row) for row in original]
now = datetime.now(timezone.utc)
timestamp = now.isoformat()
revision = REVIEW / ("revision_" + now.strftime("%Y%m%dT%H%M%SZ"))
revision.mkdir(exist_ok=False)
(revision / "backups").mkdir()
(revision / "staged").mkdir()
changes = []
allowed_columns = {
    "is_gegenpressing", "annotation_confidence", "annotation_notes",
    "annotated_at_utc", "annotator",
}
for row in revised:
    order = int(row["annotation_order"])
    if order not in DECISIONS:
        continue
    candidate, old_label, new_label, confidence, reason = DECISIONS[order]
    assert row["candidate_id"] == candidate
    assert int(row["is_gegenpressing"]) == old_label
    before = dict(row)
    addition = f"[Review AI {timestamp}; codex_ai_review] {reason}"
    row["is_gegenpressing"] = str(new_label)
    row["annotation_confidence"] = str(confidence)
    row["annotation_notes"] = (row["annotation_notes"].strip() + "\n" + addition).strip()
    row["annotated_at_utc"] = timestamp
    row["annotator"] = "codex_ai_review"
    changes.append({
        "annotation_order": order, "candidate_id": candidate,
        **{f"old_{k}": before[k] for k in sorted(allowed_columns)},
        **{f"new_{k}": row[k] for k in sorted(allowed_columns)},
        "review_reason": reason,
        "reviewer_type": "AI_assisted_review_not_independent_expert",
        "evidence_directory": str(REVIEW / "panels"),
    })
assert len(changes) == len(DECISIONS) == 13
for before, after in zip(original, revised):
    changed = {key for key in columns if before[key] != after[key]}
    assert changed <= allowed_columns
    if int(before["annotation_order"]) not in DECISIONS:
        assert before == after
buffer = io.StringIO(newline="")
writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
writer.writeheader()
writer.writerows(revised)
new_bytes = buffer.getvalue().encode("utf-8")
annotations = pd.read_csv(io.BytesIO(new_bytes))
episodes = pd.read_csv(PROCESSED / "episode_manifest.csv")
manifest = build_model_manifest(episodes, annotations)
match_manifest = build_match_split_manifest(manifest)
summary, queue, checks = build_annotation_audit(annotations, manifest)
assert checks.all() and validate_model_manifest(manifest).all()
assert annotations.is_gegenpressing.value_counts().to_dict() == {1: 208, -1: 28, 0: 28}
assert len(annotations) == 264 and len(queue) == 28
old_splits = pd.read_csv(PROCESSED / "model_episode_manifest.csv")[["candidate_id", "split"]]
split_check = old_splits.merge(manifest[["candidate_id", "split"]], on="candidate_id", validate="one_to_one")
assert len(split_check) == len(old_splits) == len(manifest)
assert split_check.split_x.eq(split_check.split_y).all()

audit_dir = ROOT / "artifacts/annotation_audit_current"
def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8")

outputs = {
    SOURCE: new_bytes,
    PROCESSED / "model_episode_manifest.csv": csv_bytes(manifest),
    PROCESSED / "match_split_manifest.csv": csv_bytes(match_manifest),
    audit_dir / "annotation_audit_summary.csv": csv_bytes(summary),
    audit_dir / "annotation_review_queue.csv": csv_bytes(queue),
    audit_dir / "annotation_audit_checks.json": json.dumps(
        {k: bool(v) for k, v in checks.items()}, indent=2).encode(),
}
backup_map = {}
for index, (target, content) in enumerate(outputs.items()):
    backup = revision / "backups" / f"{index:02d}_{target.name}"
    shutil.copy2(target, backup)
    backup_map[str(target)] = str(backup)
    (revision / "staged" / f"{index:02d}_{target.name}").write_bytes(content)

pd.DataFrame(changes).to_csv(revision / "perubahan_anotasi.csv", index=False, encoding="utf-8-sig")
summary.to_csv(revision / "ringkasan_setelah_revisi.csv", index=False, encoding="utf-8-sig")
provenance = {
    "revision_time_utc": timestamp,
    "source_sha256_before": before_hash,
    "source_sha256_after": hashlib.sha256(new_bytes).hexdigest(),
    "rows_changed": len(changes),
    "reviewer": "codex_ai_review",
    "training_run": False,
    "backup_map": backup_map,
    "evidence_scope": "Prior audit + visual interpretation; not verified video ground truth.",
    "application_status": "prepared",
}
(revision / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != before_hash:
    raise RuntimeError("Source changed during preparation; abort before applying.")
written = []
try:
    for index, target in enumerate(outputs):
        staged = revision / "staged" / f"{index:02d}_{target.name}"
        os.replace(staged, target)
        written.append(target)
    assert SOURCE.read_bytes() == new_bytes
    saved = pd.read_csv(SOURCE)
    assert len(saved) == 264 and saved.candidate_id.is_unique
except Exception:
    for target in written:
        shutil.copy2(backup_map[str(target)], target)
    raise
provenance["application_status"] = "applied_and_verified"
(revision / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

report = """# Revisi anotasi berdasarkan review AI

Perubahan telah diterapkan pada file anotasi aktif atas permintaan pengguna.
Ini merupakan revisi kerja berdasarkan interpretasi tracking, bukan sertifikasi kebenaran seluruh label oleh ahli sepak bola. Anotasi lain belum dinyatakan valid hanya karena tidak diubah.

Tiga sampel diubah dari 1 menjadi 0: **#16, #109, #259**. Keyakinan diset sedang (2), karena tidak menggunakan video.

Sepuluh sampel diubah menjadi ragu (-1), dengan keyakinan rendah (1): **#1, #31, #51, #72, #85, #188, #193, #219, #228, #251**. Alasannya meliputi tekanan terhadap opsi operan yang belum jelas, konteks bola mati/restart/FairPlay, dan ketidaksesuaian waktu event dengan tracking.

Audit awal menyebut enam kemungkinan negatif. Pada penerapan, #31, #85, dan #188 dipertahankan sebagai ragu karena belum cukup bukti untuk menolak tekanan terhadap opsi operan. Sampel #154 tetap negatif. Delapan belas label ragu awal tetap ragu.

| Label | Sebelum | Sesudah |
| --- | ---: | ---: |
| Gegenpressing (1) | 217 | 208 |
| Bukan gegenpressing (0) | 29 | 28 |
| Ragu (-1) | 18 | 28 |
| Total | 264 | 264 |

Sampel yang dapat digunakan untuk klasifikasi biner berjumlah **236**, sedangkan 28 ragu dikecualikan. Jumlah negatif turun meskipun ada tiga negatif baru, karena empat negatif lama dipindahkan ke ragu.

Identitas reviewer pada 13 baris yang diubah adalah `codex_ai_review`; nama anotator asli, waktu, label, confidence, dan catatan lama tersimpan dalam log dan cadangan. Catatan lama juga dipertahankan di dalam catatan aktif. Tidak ada perubahan kandidat, fitur, data graph, outcome, ataupun pembagian pertandingan.

File manifest model, ringkasan pembagian pertandingan, dan laporan audit aktif telah diperbarui agar menggunakan label revisi. Artefak model smoke dan artikel sebelumnya tetap merupakan hasil historis, bukan hasil dengan label revisi ini. Tidak ada pelatihan model yang dijalankan.

Jika notebook anotasi sedang terbuka, muat ulang data anotasinya sebelum menyimpan label berikutnya, karena notebook menyimpan salinan tabel dalam memori.

## Berkas

- [Log setiap perubahan](perubahan_anotasi.csv).
- [Ringkasan per pertandingan](ringkasan_setelah_revisi.csv).
- [Metadata revisi dan lokasi cadangan](provenance.json).
- [Cadangan lengkap anotasi asli](backups/00_gegenpressing_annotation_manifest.csv).

Keputusan yang masih ragu perlu ditinjau manusia menggunakan rubrik yang sama di seluruh pembagian data. Review ini bukan anotator manusia kedua dan tidak dapat dipakai sebagai bukti inter-rater reliability.
"""
(revision / "Ringkasan_Revisi.md").write_text(report, encoding="utf-8")
print("REVISION_DIR", revision)
print("CHECKS", checks.to_dict())
print("BY_SPLIT\n", summary.groupby("split").sum(numeric_only=True).to_string())
print("SOURCE_HASH", provenance["source_sha256_after"])
