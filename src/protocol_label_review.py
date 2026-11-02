"""Independent review of labels for the two-model protocol."""
import json
import platform
import tempfile
from pathlib import Path
from importlib.metadata import version

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import cohen_kappa_score

from src.annotation_audit import annotation_quality_checks
from src.final_artifact_audit import sha256_file
from src.research_readiness import build_model_manifest


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def audit_source(source, processed):
    a = pd.read_csv(source)
    checks = annotation_quality_checks(a)
    assert_valid = build_model_manifest(pd.read_csv(processed / "episode_manifest.csv"), a)
    if not checks.all() or set(a.candidate_id) != set(assert_valid.candidate_id):
        raise ValueError("Periksa integritas anotasi dan cakupan episode sebelum audit.")
    if not a.set_index("candidate_id").match_id.sort_index().equals(
        assert_valid.set_index("candidate_id").match_id.sort_index()
    ):
        raise ValueError("Identitas pertandingan tidak cocok.")
    return a.set_index("candidate_id", drop=False)


def cohorts(a):
    priority = a.annotation_confidence.eq(1) | a.is_gegenpressing.eq(-1) | a.annotator.eq("codex_ai_review")
    controls = []
    for _, group in a[~priority].sort_index().groupby(["match_id", "is_gegenpressing"]):
        controls.extend(group.sample(n=min(5, len(group)), random_state=42).index)
    return sorted(a.index[priority]), sorted(controls)


def make_form(path, ids, cache, digest, title):
    episodes = {}
    for cid in np.random.default_rng(42).permutation(ids):
        item = torch.load(cache / f"{cid}.pt", weights_only=True, map_location="cpu")
        mask = (item["relative_times"] >= -1e-5) & (item["relative_times"] <= 2.00001)
        times = item["relative_times"][mask]
        if (item["candidate_id"] != cid or len(times) != 51
                or not torch.allclose(times, torch.arange(51) / 25, atol=1e-5)
                or not item["node_mask"][mask].all()):
            raise ValueError(f"Graf tidak sesuai: {cid}")
        x = item["x"][mask]
        teams = (x[0, :, 4] + 2*x[0, :, 3]).int().tolist()
        xy = (x[:, :, :2] * 1000).round().int().reshape(51, -1).tolist()
        episodes[cid] = {"teams": teams, "frames": xy}
    payload = dict(role=path.stem, title=title, hash=digest, episodes=episodes)
    template = Path(__file__).with_name("label_review_form.html").read_text(encoding="utf-8-sig")
    path.write_text(template.replace("__DATA__", json.dumps(payload, separators=(",", ":"))), encoding="utf-8")


def prepare(source, processed, out):
    a = audit_source(source, processed)
    priority, controls = cohorts(a)
    digest = sha256_file(source)
    out.mkdir(parents=True, exist_ok=True)
    setup = out / "audit.json"
    if setup.exists() and json.loads(setup.read_text(encoding="utf-8"))["source_sha256"] != digest:
        raise ValueError("Gunakan folder baru untuk versi sumber yang berbeda.")
    cache = processed / "graph_cache"
    make_form(out / "penilai_utama.html", priority, cache, digest, "Putaran mandiri penilai utama")
    make_form(out / "penilai_kedua.html", priority + controls, cache, digest, "Putaran mandiri penilai kedua")
    stats = a.groupby(["match_id", "is_gegenpressing"]).size().unstack(fill_value=0)
    stats.to_csv(out / "kelas_per_pertandingan.csv")
    write_json(setup, dict(source_sha256=digest, n=len(a), positif=int(a.is_gegenpressing.eq(1).sum()),
                          negatif=int(a.is_gegenpressing.eq(0).sum()), prioritas=priority, sampel=controls,
                          seed=42, python=platform.python_version(),
                          libraries={p: version(p) for p in ("numpy", "pandas", "torch", "scikit-learn")},
                          checks={k:bool(v) for k,v in annotation_quality_checks(a).items()}))
    return len(a), len(priority), len(controls)


def answers(out, role, expected, digest):
    path = out / f"{role}.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = data["answers"]
    if data["hash"] != digest or data["role"] != role or set(rows) != set(expected):
        raise ValueError(f"Versi, peran, atau daftar jawaban belum sesuai: {role}")
    for cid, row in rows.items():
        if (row["label"] not in (-1, 0, 1) or row["confidence"] not in (1, 2, 3)
                or not str(row["notes"]).strip() or not str(row["person"]).strip()
                or not pd.notna(pd.to_datetime(row["utc"], utc=True, errors="coerce"))):
            raise ValueError(f"Jawaban tidak lengkap: {role}, {cid}")
    if len({r["person"].strip().casefold() for r in rows.values()}) != 1:
        raise ValueError(f"Nama atau inisial harus konsisten: {role}")
    return rows


def finalize(source, processed, out):
    a = audit_source(source, processed)
    digest = sha256_file(source)
    design = json.loads((out / "audit.json").read_text(encoding="utf-8"))
    priority, controls = cohorts(a)
    if (design["source_sha256"], design["prioritas"], design["sampel"]) != (digest, priority, controls):
        raise ValueError("Sumber atau sampel berubah. Periksa versi audit.")
    ids = priority + controls
    first = answers(out, "penilai_utama", priority, digest)
    second = answers(out, "penilai_kedua", ids, digest)
    second_name = next(iter(second.values()))["person"].strip().casefold()
    previous_names = {r["person"].strip().casefold() for r in first.values()}
    previous_names.update(a.loc[controls, "annotator"].str.strip().str.casefold())
    if second_name in previous_names:
        raise ValueError("Diperlukan dua penilai manusia yang berbeda.")
    reference = {cid:int(a.at[cid, "is_gegenpressing"]) for cid in controls}
    reference.update({cid:r["label"] for cid,r in first.items()})
    conflicts = [cid for cid in ids if reference[cid] != second[cid]["label"]]
    choices = first.copy()
    if conflicts:
        pd.DataFrame([dict(candidate_id=cid, label_utama=reference[cid],
                           alasan_utama=first[cid]["notes"] if cid in first else a.at[cid,"annotation_notes"],
                           label_kedua=second[cid]["label"], alasan_kedua=second[cid]["notes"])
                      for cid in conflicts]).to_csv(out / "perbedaan.csv", index=False)
        make_form(out / "kesepakatan.html", conflicts, processed / "graph_cache", digest,
                  "Keputusan bersama setelah diskusi. Catat alasan akhir atau pilih ragu.")
        if not (out / "kesepakatan.json").exists():
            return f"{len(conflicts)} perbedaan. Buka perbedaan.csv dan kesepakatan.html bersama, simpan kesepakatan.json lalu ulangi."
        choices.update(answers(out, "kesepakatan", conflicts, digest))
    for cid,r in choices.items():
        for key,col in [("label","is_gegenpressing"),("confidence","annotation_confidence"),
                        ("person","annotator"),("utc","annotated_at_utc"),("notes","annotation_notes")]:
            a.at[cid,col] = r[key]
    audit = []
    old = pd.read_csv(source).set_index("candidate_id")
    for cid in ids:
        new = int(a.at[cid,"is_gegenpressing"])
        audit.append(dict(candidate_id=cid,kelompok="prioritas" if cid in first else "sampel",
                          label_asal=int(old.at[cid,"is_gegenpressing"]),label_utama=reference[cid],
                          label_kedua=second[cid]["label"],label_akhir=new,
                          keputusan="dikeluarkan_ragu" if new==-1 else
                          ("diubah" if new != old.at[cid,"is_gegenpressing"] else "dipertahankan")))
    destination = out / "final"
    if destination.exists():
        raise FileExistsError(f"Versi final sudah ada: {destination}")
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        staged = Path(tmp) / "final"
        staged.mkdir()
        if not annotation_quality_checks(a).all():
            raise ValueError("Label hasil review belum lolos pemeriksaan.")
        a.to_csv(staged / "annotations.csv", index=False)
        pd.DataFrame(audit).to_csv(staged / "log_keputusan.csv", index=False)
        y1 = [reference[c] for c in controls]
        y2 = [second[c]["label"] for c in controls]
        write_json(staged / "ringkasan.json",dict(source_sha256=digest, final_sha256=sha256_file(staged/"annotations.csv"),
                   n=len(a), label_counts={str(k):int(v) for k,v in a.is_gegenpressing.value_counts().items()},
                   n_prioritas=len(priority), n_sampel=len(controls), n_perbedaan=len(conflicts),
                   kesepakatan_sampel_sebelum_diskusi=float(np.mean(np.equal(y1,y2))),
                   kappa_sampel_sebelum_diskusi=float(cohen_kappa_score(y1,y2,labels=[-1,0,1])),
                   catatan="Kesepakatan pada sampel berstrata, bukan estimasi prevalensi populasi."))
        staged.rename(destination)
    return str(destination / "annotations.csv")
