"""
download_datasets.py
======================
Script untuk mengunduh dataset penelitian VAEP-Track:
1. Metrica Sports Sample Open Data (3 laga) -- untuk prototyping pipeline
2. Sportec Open DFL Dataset / Bassek et al. (2025) (7 laga Bundesliga) -- dataset utama

Prasyarat:
    pip install kloppy pandas

Cara pakai:
    python download_datasets.py
"""

import os
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path("data")
METRICA_DIR = OUTPUT_DIR / "metrica_sample"
SPORTEC_DIR = OUTPUT_DIR / "sportec_idsse"

# 7 match ID resmi Sportec Open DFL Dataset (Bassek et al., 2025)
SPORTEC_MATCH_IDS = [
    "J03WPY", "J03WMX", "J03WN1", "J03WOH", "J03WOY", "J03WQQ", "J03WR9",
]

# Metrica Sample Data: 3 pertandingan tersedia (match_id 1, 2, 3)
METRICA_MATCH_IDS = [1, 2, 3]


def ensure_dirs():
    METRICA_DIR.mkdir(parents=True, exist_ok=True)
    SPORTEC_DIR.mkdir(parents=True, exist_ok=True)


def download_metrica():
    """Unduh Metrica Sports Sample Open Data lewat kloppy, simpan sebagai CSV lokal."""
    from kloppy import metrica

    print("\n=== Mengunduh Metrica Sports Sample Data ===")
    for match_id in METRICA_MATCH_IDS:
        try:
            print(f"  - Memuat match_id={match_id} ...")
            dataset = metrica.load_open_data(match_id=match_id)
            df = dataset.to_df()
            out_path = METRICA_DIR / f"metrica_match_{match_id}_tracking.csv"
            df.to_csv(out_path, index=False)
            print(f"    tersimpan -> {out_path} ({len(df)} baris)")
        except Exception as e:
            print(f"    GAGAL untuk match_id={match_id}: {e}")


def download_sportec():
    """Unduh Sportec Open DFL Dataset (Bassek et al., 2025) lewat kloppy."""
    from kloppy import sportec

    print("\n=== Mengunduh Sportec Open DFL Dataset (Bassek et al., 2025) ===")
    for match_id in SPORTEC_MATCH_IDS:
        try:
            print(f"  - Memuat match_id={match_id} ...")
            tracking = sportec.load_open_tracking_data(match_id=match_id)
            events = sportec.load_open_event_data(match_id=match_id)

            tracking_df = tracking.to_df()
            events_df = events.to_df()

            tracking_out = SPORTEC_DIR / f"{match_id}_tracking.csv"
            events_out = SPORTEC_DIR / f"{match_id}_events.csv"

            tracking_df.to_csv(tracking_out, index=False)
            events_df.to_csv(events_out, index=False)

            print(f"    tracking -> {tracking_out} ({len(tracking_df)} baris)")
            print(f"    events   -> {events_out} ({len(events_df)} baris)")
        except Exception as e:
            print(f"    GAGAL untuk match_id={match_id}: {e}")


def verify():
    """Cek ringkas: apakah semua file berhasil terunduh."""
    print("\n=== Verifikasi Hasil Unduhan ===")

    metrica_files = list(METRICA_DIR.glob("*.csv"))
    sportec_files = list(SPORTEC_DIR.glob("*.csv"))

    print(f"Metrica: {len(metrica_files)} file ditemukan di {METRICA_DIR}")
    print(f"Sportec: {len(sportec_files)} file ditemukan di {SPORTEC_DIR}")

    expected_sportec = len(SPORTEC_MATCH_IDS) * 2  # tracking + events per match
    if len(sportec_files) < expected_sportec:
        print(f"  PERINGATAN: diharapkan {expected_sportec} file Sportec, "
              f"hanya {len(sportec_files)} yang berhasil. Cek log di atas untuk match yang gagal.")
    else:
        print("  Semua file Sportec berhasil diunduh lengkap.")


if __name__ == "__main__":
    ensure_dirs()
    download_metrica()
    download_sportec()
    verify()
    print("\nSelesai. Data tersimpan di folder ./data/")
