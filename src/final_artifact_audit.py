"""Verify a completed VAEP-Track training run before it is marked final."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


EXPECTED_FILES = (
    "frozen_annotations.csv",
    "frozen_model_manifest.csv",
    "annotation_audit_summary.csv",
    "annotation_review_queue.csv",
    "annotation_audit_checks.json",
    "training_summary.md",
    "environment.json",
    "run_manifest.json",
    "baseline/logistic_regression.joblib",
    "baseline/xgboost.joblib",
    "baseline/metrics.csv",
    "baseline/predictions.csv",
    "baseline/metadata.json",
    "temporal_gnn/temporal_gnn.pt",
    "temporal_gnn/metrics.csv",
    "temporal_gnn/predictions.csv",
    "temporal_gnn/training_history.csv",
    "temporal_gnn/metadata.json",
    "evaluation/combined_predictions.csv",
    "evaluation/split_metrics.csv",
    "evaluation/match_metrics.csv",
    "evaluation/metadata.json",
)

CRITICAL_HASH_PATHS = {
    "frozen_annotations.csv",
    "annotation_audit_summary.csv",
    "annotation_review_queue.csv",
    "data/processed/gegenpressing_baseline_features.csv",
    "data/processed/graph_cache_manifest.csv",
    "baseline/logistic_regression.joblib",
    "baseline/xgboost.joblib",
    "temporal_gnn/temporal_gnn.pt",
    "evaluation/split_metrics.csv",
    "evaluation/match_metrics.csv",
}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_final_training_artifacts(
    run_dir: str | Path,
    project_root: str | Path,
) -> pd.Series:
    """Return strict integrity checks for a staged final-training directory."""

    run_dir = Path(run_dir)
    project_root = Path(project_root)
    files_complete = all(
        (run_dir / relative).is_file() and (run_dir / relative).stat().st_size > 0
        for relative in EXPECTED_FILES
    )
    if not files_complete:
        return pd.Series({"all_expected_files_nonempty": False}, name="passed")

    baseline_metadata = _read_json(run_dir / "baseline" / "metadata.json")
    gnn_metadata = _read_json(run_dir / "temporal_gnn" / "metadata.json")
    evaluation_metadata = _read_json(run_dir / "evaluation" / "metadata.json")
    annotation_checks = _read_json(run_dir / "annotation_audit_checks.json")
    run_manifest = _read_json(run_dir / "run_manifest.json")
    annotations = pd.read_csv(run_dir / "frozen_annotations.csv")
    summary = (run_dir / "training_summary.md").read_text(encoding="utf-8")

    artifact_hashes = run_manifest.get("artifact_sha256", {})
    normalized_hash_keys = {Path(key).as_posix() for key in artifact_hashes}
    hashes_match = True
    for key, expected_hash in artifact_hashes.items():
        relative = Path(key)
        artifact_path = run_dir / relative
        if not artifact_path.exists():
            artifact_path = project_root / relative
        if not artifact_path.is_file() or sha256_file(artifact_path) != expected_hash:
            hashes_match = False
            break

    labels = pd.to_numeric(annotations["is_gegenpressing"], errors="coerce")
    evaluation_checks = evaluation_metadata.get("checks", {})
    checks = {
        "all_expected_files_nonempty": files_complete,
        "baseline_marked_final": baseline_metadata.get("final_run") is True,
        "gnn_marked_final": gnn_metadata.get("final_run") is True,
        "evaluation_marked_final": evaluation_metadata.get("final_run") is True,
        "expected_models_present": set(evaluation_metadata.get("models", []))
        == {"logistic_regression", "xgboost", "temporal_gnn"},
        "evaluation_checks_passed": bool(evaluation_checks)
        and all(evaluation_checks.values()),
        "annotation_checks_passed": bool(annotation_checks)
        and all(annotation_checks.values()),
        "frozen_annotations_complete": bool(labels.notna().all()),
        "run_manifest_complete": run_manifest.get("status")
        == "final_training_complete",
        "critical_hashes_listed": CRITICAL_HASH_PATHS.issubset(normalized_hash_keys),
        "artifact_hashes_match": bool(artifact_hashes) and hashes_match,
        "summary_marked_final": "Status: FINAL" in summary
        and "SMOKE TEST ONLY" not in summary,
    }
    return pd.Series(checks, name="passed")
