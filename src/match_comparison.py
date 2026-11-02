"""Compare the two existing detectors on paired, held-out matches."""
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import confusion_matrix, f1_score, recall_score, roc_auc_score

from src.annotation_audit import annotation_quality_checks
from src.baseline_training import prepare_baseline_dataset, run_baseline_training
from src.research_readiness import build_model_manifest
from src.temporal_gnn_training import prepare_gnn_dataset, train_temporal_gnn


MATCHES = ("J03WMX", "J03WN1", "J03WOH", "J03WOY", "J03WPY", "J03WQQ", "J03WR9")
SEED = 42


def validation_macro_threshold(y_true, probabilities):
    """Maximize validation macro-F1; ties favor 0.50, then the lower threshold."""
    def rank(percent):
        predicted = probabilities >= percent / 100
        score = f1_score(y_true, predicted, labels=[0, 1], average="macro", zero_division=0)
        return score, -abs(percent - 50), -percent

    return max(range(1, 100), key=rank) / 100


def load_inputs(processed, annotation_path):
    annotations = pd.read_csv(annotation_path)
    checks = annotation_quality_checks(annotations)
    if not checks.all():
        raise ValueError(f"Audit anotasi belum lolos: {checks[~checks].index.tolist()}")
    manifest = build_model_manifest(pd.read_csv(processed / "episode_manifest.csv"), annotations)
    if set(manifest.candidate_id) != set(annotations.candidate_id):
        raise ValueError("ID anotasi berbeda dari daftar episode strict-valid.")
    features = pd.read_csv(processed / "gegenpressing_baseline_features.csv")
    cache = pd.read_csv(processed / "graph_cache_manifest.csv")
    baseline = prepare_baseline_dataset(features, manifest)
    graphs = prepare_gnn_dataset(manifest, cache)
    for frame in (graphs, baseline):
        if set(frame.candidate_id) != set(manifest.candidate_id):
            raise ValueError("Cakupan episode fitur dan graf harus identik.")
    manifest = manifest[manifest.eligible_for_detection_training].copy()
    if set(manifest.match_id) != set(MATCHES):
        raise ValueError("Protokol memerlukan tujuh pertandingan yang terdaftar.")
    counts = pd.crosstab(manifest.match_id, manifest.gegenpressing_label).reindex(columns=[0, 1], fill_value=0)
    if (counts < 1).any().any():
        raise ValueError("Setiap pertandingan memerlukan kedua kelas untuk ROC-AUC.")
    return annotations, manifest, baseline, graphs


def crop_graphs(rows, source, target):
    """Check node/edge alignment and persist only the 51 post-loss frames."""
    expected = torch.arange(51, dtype=torch.float32) / 25
    for row in rows.itertuples():
        item = torch.load(source / row.cache_file, map_location="cpu", weights_only=True)
        times = item["relative_times"]
        keep = (times >= -1e-5) & (times <= 2 + 1e-5)
        if (item["candidate_id"], item["match_id"]) != (row.candidate_id, row.match_id):
            raise ValueError(f"Identitas graf tidak cocok: {row.candidate_id}")
        if keep.sum().item() != 51 or not torch.allclose(times[keep], expected, atol=1e-5):
            raise ValueError(f"Jendela graf tidak lengkap: {row.candidate_id}")
        clipped = {key: item[key][keep] for key in ("relative_times", "x", "edge_index", "node_mask")}
        torch.save(clipped, target / row.cache_file)


def run_comparison(inputs, processed, output_root, mode):
    if mode not in ("uji_coba", "tujuh_pertandingan"):
        raise ValueError("Mode eksperimen tidak dikenal.")
    annotations, manifest, baseline, graphs = inputs
    trial = mode == "uji_coba"
    if trial:
        manifest = pd.concat([
            group.sample(n=min(6, len(group)), random_state=SEED)
            for _, group in manifest.groupby(["match_id", "gegenpressing_label"])
        ])
    ids = set(manifest.candidate_id)
    baseline = baseline[baseline.candidate_id.isin(ids)].copy()
    graphs = graphs[graphs.candidate_id.isin(ids)].copy()
    run = output_root / f"{mode}_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}"
    run.mkdir(parents=True, exist_ok=False)
    print(f"Folder hasil: {run}", flush=True)
    manifest.drop(columns="split").to_csv(run / "episode_eksperimen.csv", index=False)
    annotations[annotations.candidate_id.isin(ids)].to_csv(run / "anotasi.csv", index=False)
    config = {
        "mode": mode, "status": "berjalan", "seed": SEED,
        "window_seconds": [0, 2], "frames": 51, "max_epochs": 1 if trial else 100,
        "patience": 15, "batch_size": 8, "python": platform.python_version(),
        "packages": {p: version(p) for p in ("pandas", "numpy", "scikit-learn", "xgboost", "torch", "torch-geometric")},
    }
    config_path = run / "protokol.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    predictions = []
    with TemporaryDirectory(dir=run, prefix="cache_51_") as temporary:
        cache = Path(temporary)
        crop_graphs(graphs, processed / "graph_cache", cache)
        for i, test in enumerate(MATCHES[:1] if trial else MATCHES):
            validation = MATCHES[(i + 1) % len(MATCHES)]
            folder = run / test
            for frame in (baseline, graphs):
                frame["split"] = frame.match_id.map({test: "test", validation: "validation"}).fillna("train")
            print(f"Putaran {i+1}: uji {test}, validasi {validation}", flush=True)
            options = dict(final_run=not trial, random_state=SEED, threshold_selector=validation_macro_threshold,
                           minimum_per_class_per_split=1)
            _, tree_preds, _ = run_baseline_training(
                baseline, annotations, folder / "xgboost", model_names=("xgboost",), **options)
            _, graph_preds, _, _ = train_temporal_gnn(
                graphs, annotations, cache, folder / "temporal_gnn", max_epochs=config["max_epochs"],
                batch_size=config["batch_size"], patience=config["patience"], **options)
            for table in (tree_preds, graph_preds):
                predictions.append(table[table.split.eq("test")].copy())
    held_out = pd.concat(predictions, ignore_index=True)
    expected_ids = set(manifest.loc[manifest.match_id.eq(MATCHES[0]), "candidate_id"]) if trial else ids
    for _, rows in held_out.groupby("model"):
        if rows.candidate_id.duplicated().any() or set(rows.candidate_id) != expected_ids:
            raise RuntimeError("Prediksi uji tidak lengkap atau berulang.")
    held_out.to_csv(run / "prediksi_uji.csv", index=False)
    records = []
    for (match, model), rows in held_out.groupby(["match_id", "model"]):
        truth, pred = rows.y_true, rows.y_pred
        tn, fp, fn, tp = confusion_matrix(truth, pred, labels=[0, 1]).ravel()
        r0, r1 = recall_score(truth, pred, labels=[0, 1], average=None)
        records.append(dict(match_id=match, model=model, n=len(rows), tn=tn, fp=fp, fn=fn, tp=tp,
                            recall_0=r0, recall_1=r1, macro_f1=f1_score(truth, pred, average="macro"),
                            roc_auc=roc_auc_score(truth, rows.probability)))
    scores = pd.DataFrame(records)
    scores.to_csv(run / "metrik_per_pertandingan.csv", index=False)
    pairs = scores.pivot(index="match_id", columns="model", values="macro_f1")
    pairs["selisih_gnn_minus_xgboost"] = pairs.temporal_gnn - pairs.xgboost
    pairs.loc["rata_rata_bobot_setara"] = pairs.mean()
    pairs.to_csv(run / "perbandingan_macro_f1.csv")
    config["status"] = "selesai"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return run, pairs
