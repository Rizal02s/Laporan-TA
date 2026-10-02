from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Audit final-training gates without training models.",
    )
    args = parser.parse_args()

    from src.baseline_training import (
        baseline_readiness,
        prepare_baseline_dataset,
        run_baseline_training,
    )
    from src.annotation_audit import build_annotation_audit
    from src.model_evaluation import save_evaluation_artifacts
    from src.final_reporting import build_training_summary
    from src.final_artifact_audit import audit_final_training_artifacts, sha256_file
    from src.research_readiness import build_model_manifest
    from src.temporal_gnn_training import prepare_gnn_dataset, train_temporal_gnn

    processed = ROOT / "data" / "processed"
    annotations_path = processed / "gegenpressing_annotation_manifest.csv"
    annotations = pd.read_csv(annotations_path)
    episodes = pd.read_csv(processed / "episode_manifest.csv")
    features = pd.read_csv(processed / "gegenpressing_baseline_features.csv")
    cache_manifest = pd.read_csv(processed / "graph_cache_manifest.csv")
    model_manifest = build_model_manifest(episodes, annotations)
    baseline_dataset = prepare_baseline_dataset(features, model_manifest)
    gnn_dataset = prepare_gnn_dataset(model_manifest, cache_manifest)
    readiness = baseline_readiness(annotations, baseline_dataset)

    print("Final-training readiness:")
    print(readiness.to_string())
    if not readiness.all():
        print("NOT_READY")
        return 0 if args.check_only else 2
    if args.check_only:
        print("READY")
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging_dir = ROOT / "artifacts" / f"final_training_incomplete_{timestamp}"
    final_output_dir = ROOT / "artifacts" / f"final_training_{timestamp}"
    baseline_dir = staging_dir / "baseline"
    gnn_dir = staging_dir / "temporal_gnn"
    evaluation_dir = staging_dir / "evaluation"
    staging_dir.mkdir(parents=True, exist_ok=False)

    frozen_annotations = staging_dir / "frozen_annotations.csv"
    shutil.copy2(annotations_path, frozen_annotations)
    model_manifest.to_csv(staging_dir / "frozen_model_manifest.csv", index=False)
    annotation_summary, annotation_review, annotation_checks = build_annotation_audit(
        annotations,
        model_manifest,
    )
    annotation_summary.to_csv(
        staging_dir / "annotation_audit_summary.csv",
        index=False,
    )
    annotation_review.to_csv(
        staging_dir / "annotation_review_queue.csv",
        index=False,
    )
    (staging_dir / "annotation_audit_checks.json").write_text(
        json.dumps({key: bool(value) for key, value in annotation_checks.items()}, indent=2),
        encoding="utf-8",
    )

    run_baseline_training(
        baseline_dataset,
        annotations,
        baseline_dir,
        final_run=True,
        random_state=42,
    )
    train_temporal_gnn(
        gnn_dataset,
        annotations,
        processed / "graph_cache",
        gnn_dir,
        final_run=True,
        random_state=42,
        batch_size=8,
        max_epochs=100,
        patience=15,
    )
    save_evaluation_artifacts(
        [baseline_dir / "predictions.csv", gnn_dir / "predictions.csv"],
        evaluation_dir,
        final_run=True,
    )
    build_training_summary(
        baseline_dir,
        gnn_dir,
        evaluation_dir,
        staging_dir / "training_summary.md",
        final_run=True,
    )

    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
        git_dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
        ).strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_commit = None
        git_dirty = None

    import platform
    import sklearn
    import torch
    import torch_geometric
    import xgboost

    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_geometric": torch_geometric.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        ),
        "scikit_learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
    }
    (staging_dir / "environment.json").write_text(
        json.dumps(environment, indent=2),
        encoding="utf-8",
    )

    checksum_paths = [
        frozen_annotations,
        staging_dir / "annotation_audit_summary.csv",
        staging_dir / "annotation_review_queue.csv",
        processed / "gegenpressing_baseline_features.csv",
        processed / "graph_cache_manifest.csv",
        baseline_dir / "logistic_regression.joblib",
        baseline_dir / "xgboost.joblib",
        gnn_dir / "temporal_gnn.pt",
        evaluation_dir / "split_metrics.csv",
        evaluation_dir / "match_metrics.csv",
    ]
    manifest = {
        "created_at_utc": timestamp,
        "annotation_sha256": sha256_file(frozen_annotations),
        "feature_sha256": sha256_file(
            processed / "gegenpressing_baseline_features.csv"
        ),
        "graph_cache_manifest_sha256": sha256_file(
            processed / "graph_cache_manifest.csv"
        ),
        "random_state": 42,
        "status": "final_training_complete",
        "artifact_sha256": {
            str(path.relative_to(staging_dir))
            if path.is_relative_to(staging_dir)
            else str(path.relative_to(ROOT)): sha256_file(path)
            for path in checksum_paths
        },
    }
    (staging_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    artifact_checks = audit_final_training_artifacts(staging_dir, ROOT)
    (staging_dir / "artifact_audit.json").write_text(
        json.dumps({key: bool(value) for key, value in artifact_checks.items()}, indent=2),
        encoding="utf-8",
    )
    if not artifact_checks.all():
        failed = artifact_checks[~artifact_checks].index.tolist()
        raise RuntimeError(
            f"Audit artefak final gagal: {failed}. Staging dipertahankan di {staging_dir}"
        )
    staging_dir.rename(final_output_dir)
    print(final_output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
