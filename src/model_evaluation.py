"""Shared evaluation outputs for baseline and temporal GNN models."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.baseline_training import classification_metrics


def evaluate_predictions(
    predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate split-level and match-level metrics without retuning thresholds."""

    required = {
        "model",
        "split",
        "candidate_id",
        "match_id",
        "y_true",
        "probability",
        "threshold",
        "y_pred",
    }
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Prediction columns tidak lengkap: {sorted(missing)}")
    if predictions.duplicated(["model", "candidate_id"]).any():
        raise ValueError("Prediksi duplikat untuk model dan candidate_id")

    def metric_record(group: pd.DataFrame) -> dict[str, object]:
        thresholds = group["threshold"].dropna().unique()
        if len(thresholds) != 1:
            raise ValueError("Satu grup evaluasi memiliki threshold tidak konsisten")
        metrics = classification_metrics(
            group["y_true"].astype(int).to_numpy(),
            group["probability"].astype(float).to_numpy(),
            float(thresholds[0]),
        )
        return {
            **{key: value for key, value in metrics.items() if key != "confusion_matrix"},
            "confusion_matrix": json.dumps(metrics["confusion_matrix"]),
        }

    split_records = []
    for (model, split), group in predictions.groupby(["model", "split"]):
        split_records.append({
            "model": model,
            "split": split,
            **metric_record(group),
        })

    match_records = []
    for (model, split, match_id), group in predictions.groupby(
        ["model", "split", "match_id"]
    ):
        match_records.append({
            "model": model,
            "split": split,
            "match_id": match_id,
            **metric_record(group),
        })
    return pd.DataFrame(split_records), pd.DataFrame(match_records)


def compare_model_prediction_sets(predictions: pd.DataFrame) -> pd.Series:
    """Verify that every model is evaluated on identical candidates by split."""

    required = {
        "model",
        "split",
        "candidate_id",
        "match_id",
        "y_true",
        "probability",
        "threshold",
        "y_pred",
    }
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Prediction columns tidak lengkap: {sorted(missing)}")

    models = sorted(predictions["model"].unique())
    reference_candidates = None
    reference_records = None
    identical_candidates = True
    identical_records = True
    for model in models:
        model_frame = predictions.loc[
            predictions["model"].eq(model),
            ["candidate_id", "split", "match_id", "y_true"],
        ]
        model_candidates = set(model_frame["candidate_id"])
        model_records = set(model_frame.itertuples(index=False, name=None))
        if reference_candidates is None:
            reference_candidates = model_candidates
            reference_records = model_records
        else:
            identical_candidates &= model_candidates == reference_candidates
            identical_records &= model_records == reference_records

    threshold_counts = predictions.groupby("model")["threshold"].nunique(dropna=False)
    split_counts = predictions.groupby("match_id")["split"].nunique(dropna=False)
    expected_predictions = (
        predictions["probability"].astype(float)
        >= predictions["threshold"].astype(float)
    ).astype(int)
    observed_predictions = pd.to_numeric(
        predictions["y_pred"],
        errors="coerce",
    )
    required_splits = {"train", "validation", "test"}
    all_splits_per_model = all(
        set(group["split"]) == required_splits
        for _, group in predictions.groupby("model")
    )
    return pd.Series({
        "at_least_two_models": len(models) >= 2,
        "unique_model_candidate_pairs": not predictions.duplicated(
            ["model", "candidate_id"]
        ).any(),
        "identical_candidate_sets": identical_candidates,
        "identical_candidate_records": identical_records,
        "all_splits_per_model": all_splits_per_model,
        "test_split_present": "test" in set(predictions["split"]),
        "threshold_present": bool(predictions["threshold"].notna().all()),
        "one_threshold_per_model": bool(threshold_counts.eq(1).all()),
        "one_split_per_match": bool(split_counts.eq(1).all()),
        "binary_ground_truth": bool(predictions["y_true"].isin([0, 1]).all()),
        "probabilities_in_unit_interval": bool(
            predictions["probability"].between(0, 1, inclusive="both").all()
        ),
        "predictions_match_threshold": bool(
            observed_predictions.notna().all()
            and observed_predictions.astype(int).eq(expected_predictions).all()
        ),
    }, name="passed")


def save_evaluation_artifacts(
    prediction_files: list[str | Path],
    output_dir: str | Path,
    *,
    final_run: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    """Combine prediction files and save comparable evaluation tables."""

    tables = [pd.read_csv(path) for path in prediction_files]
    predictions = pd.concat(tables, ignore_index=True)
    checks = compare_model_prediction_sets(predictions)
    if not checks.all():
        failed = checks[~checks].index.tolist()
        raise ValueError(f"Evaluation comparison gate gagal: {failed}")

    split_metrics, match_metrics = evaluate_predictions(predictions)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_dir / "combined_predictions.csv", index=False)
    split_metrics.to_csv(output_dir / "split_metrics.csv", index=False)
    match_metrics.to_csv(output_dir / "match_metrics.csv", index=False)
    metadata = {
        "final_run": bool(final_run),
        "models": sorted(predictions["model"].unique().tolist()),
        "checks": {key: bool(value) for key, value in checks.items()},
        "test_candidates": int(
            predictions.loc[predictions["split"].eq("test"), "candidate_id"].nunique()
        ),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return predictions, split_metrics, match_metrics, checks
