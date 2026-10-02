"""Leakage-safe baseline training for gegenpressing detection."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.annotation_audit import annotation_quality_checks
from src.gegenpressing_features import BASELINE_FEATURE_COLUMNS


def prepare_baseline_dataset(
    features: pd.DataFrame,
    model_manifest: pd.DataFrame,
) -> pd.DataFrame:
    """Merge feature-only rows with split and manual behavior labels."""

    manifest_columns = [
        "candidate_id",
        "match_id",
        "split",
        "gegenpressing_label",
        "label_status",
        "eligible_for_detection_training",
    ]
    missing = set(manifest_columns).difference(model_manifest.columns)
    if missing:
        raise ValueError(f"Model manifest tidak lengkap: {sorted(missing)}")
    if features["candidate_id"].duplicated().any():
        raise ValueError("candidate_id duplikat pada feature table")

    dataset = features.merge(
        model_manifest[manifest_columns],
        on=["candidate_id", "match_id"],
        how="inner",
        validate="one_to_one",
    )
    if len(dataset) != len(features):
        raise ValueError("Sebagian feature row tidak memiliki model manifest")
    return dataset


def baseline_readiness(
    annotations: pd.DataFrame,
    dataset: pd.DataFrame,
    minimum_per_class_per_split: int = 5,
) -> pd.Series:
    """Return final-training gates without modifying annotations."""

    annotation_checks = annotation_quality_checks(annotations)
    usable = dataset[dataset["eligible_for_detection_training"]].copy()
    counts = pd.crosstab(usable["split"], usable["gegenpressing_label"])
    required_splits = {"train", "validation", "test"}
    both_classes = all(
        split in counts.index
        and 0 in counts.columns
        and 1 in counts.columns
        and counts.loc[split, 0] > 0
        and counts.loc[split, 1] > 0
        for split in required_splits
    )
    enough_per_class = all(
        split in counts.index
        and 0 in counts.columns
        and 1 in counts.columns
        and counts.loc[split, 0] >= minimum_per_class_per_split
        and counts.loc[split, 1] >= minimum_per_class_per_split
        for split in required_splits
    )
    return pd.concat([annotation_checks, pd.Series({
        "both_classes_in_every_split": both_classes,
        "minimum_per_class_in_every_split": enough_per_class,
        "uncertain_excluded": bool(
            (~dataset.loc[
                dataset["gegenpressing_label"].eq(-1),
                "eligible_for_detection_training",
            ]).all()
        ),
    }, name="passed")]).rename("passed")


def _build_models(random_state: int) -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                random_state=random_state,
            )),
        ]),
        "xgboost": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", XGBClassifier(
                n_estimators=200,
                max_depth=3,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=random_state,
                n_jobs=4,
            )),
        ]),
    }


def choose_validation_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    if len(thresholds) == 0:
        return 0.5
    f1_values = 2 * precision[:-1] * recall[:-1] / (
        precision[:-1] + recall[:-1] + 1e-12
    )
    return float(thresholds[int(np.nanargmax(f1_values))])


def classification_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    predictions = (probabilities >= threshold).astype(int)
    result = {
        "samples": int(len(y_true)),
        "positive_rate": float(np.mean(y_true)),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "confusion_matrix": confusion_matrix(
            y_true,
            predictions,
            labels=[0, 1],
        ).tolist(),
    }
    if len(np.unique(y_true)) == 2:
        result["roc_auc"] = float(roc_auc_score(y_true, probabilities))
        result["pr_auc"] = float(average_precision_score(y_true, probabilities))
    else:
        result["roc_auc"] = None
        result["pr_auc"] = None
    return result


def run_baseline_training(
    dataset: pd.DataFrame,
    annotations: pd.DataFrame,
    output_dir: str | Path,
    *,
    final_run: bool,
    random_state: int = 42,
    minimum_per_class_per_split: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Train baselines and save models, predictions, metrics, and metadata."""

    readiness = baseline_readiness(
        annotations,
        dataset,
        minimum_per_class_per_split=minimum_per_class_per_split,
    )
    if final_run and not readiness.all():
        failed = readiness[~readiness].index.tolist()
        raise RuntimeError(f"Final training gate gagal: {failed}")

    usable = dataset[dataset["eligible_for_detection_training"]].copy()
    if usable.empty:
        raise ValueError("Belum ada label biner untuk training")

    split_frames = {
        split: usable[usable["split"].eq(split)].copy()
        for split in ("train", "validation", "test")
    }
    for split, frame in split_frames.items():
        if frame.empty:
            raise ValueError(f"Split {split} tidak memiliki label usable")
        if frame["gegenpressing_label"].nunique() < 2:
            raise ValueError(f"Split {split} hanya memiliki satu kelas")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models = _build_models(random_state)
    metric_records = []
    prediction_records = []

    train = split_frames["train"]
    validation = split_frames["validation"]
    x_train = train[BASELINE_FEATURE_COLUMNS]
    y_train = train["gegenpressing_label"].astype(int).to_numpy()

    for model_name, model in models.items():
        fit_parameters = {}
        if model_name == "xgboost":
            fit_parameters["classifier__sample_weight"] = compute_sample_weight(
                class_weight="balanced",
                y=y_train,
            )
        model.fit(x_train, y_train, **fit_parameters)
        validation_probabilities = model.predict_proba(
            validation[BASELINE_FEATURE_COLUMNS]
        )[:, 1]
        threshold = choose_validation_threshold(
            validation["gegenpressing_label"].astype(int).to_numpy(),
            validation_probabilities,
        )

        for split, frame in split_frames.items():
            y_true = frame["gegenpressing_label"].astype(int).to_numpy()
            probabilities = model.predict_proba(
                frame[BASELINE_FEATURE_COLUMNS]
            )[:, 1]
            metrics = classification_metrics(y_true, probabilities, threshold)
            metric_records.append({
                "model": model_name,
                "split": split,
                **{key: value for key, value in metrics.items() if key != "confusion_matrix"},
                "confusion_matrix": json.dumps(metrics["confusion_matrix"]),
            })
            for candidate_id, match_id, truth, probability in zip(
                frame["candidate_id"],
                frame["match_id"],
                y_true,
                probabilities,
            ):
                prediction_records.append({
                    "model": model_name,
                    "split": split,
                    "candidate_id": candidate_id,
                    "match_id": match_id,
                    "y_true": int(truth),
                    "probability": float(probability),
                    "threshold": threshold,
                    "y_pred": int(probability >= threshold),
                })

        joblib.dump(model, output_dir / f"{model_name}.joblib")

    metrics_table = pd.DataFrame(metric_records)
    predictions = pd.DataFrame(prediction_records)
    metrics_table.to_csv(output_dir / "metrics.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    metadata = {
        "final_run": bool(final_run),
        "random_state": random_state,
        "features": BASELINE_FEATURE_COLUMNS,
        "usable_samples": int(len(usable)),
        "split_counts": {
            split: int(len(frame)) for split, frame in split_frames.items()
        },
        "readiness": {key: bool(value) for key, value in readiness.items()},
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metrics_table, predictions, readiness
