"""Generate a human-readable record for a completed training run."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _format_metric(value) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value):.4f}"


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    rows = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if column in {
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "pr_auc",
                "threshold",
            }:
                values.append(_format_metric(value))
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return rows


def build_training_summary(
    baseline_dir: str | Path,
    gnn_dir: str | Path,
    evaluation_dir: str | Path,
    output_path: str | Path,
    *,
    final_run: bool,
) -> Path:
    """Write a Markdown summary from saved, already-evaluated artifacts."""

    baseline_dir = Path(baseline_dir)
    gnn_dir = Path(gnn_dir)
    evaluation_dir = Path(evaluation_dir)
    output_path = Path(output_path)
    split_metrics = pd.read_csv(evaluation_dir / "split_metrics.csv")
    match_metrics = pd.read_csv(evaluation_dir / "match_metrics.csv")
    combined_predictions = pd.read_csv(
        evaluation_dir / "combined_predictions.csv"
    )
    baseline_metadata = json.loads(
        (baseline_dir / "metadata.json").read_text(encoding="utf-8")
    )
    gnn_metadata = json.loads(
        (gnn_dir / "metadata.json").read_text(encoding="utf-8")
    )

    test_metrics = split_metrics[split_metrics["split"].eq("test")].copy()
    test_match_metrics = match_metrics[match_metrics["split"].eq("test")].copy()
    unique_test_samples = combined_predictions.loc[
        combined_predictions["split"].eq("test"),
        "candidate_id",
    ].nunique()

    title = (
        "# Final Training Summary"
        if final_run
        else "# Smoke Test Training Summary"
    )
    lines = [
        title,
        "",
        (
            "Status: FINAL"
            if final_run
            else "Status: SMOKE TEST ONLY - DO NOT REPORT AS FINAL RESULTS"
        ),
        "",
        "## Data and split",
        "",
        f"- Usable labels: {baseline_metadata['usable_samples']}",
        f"- Train samples: {baseline_metadata['split_counts']['train']}",
        f"- Validation samples: {baseline_metadata['split_counts']['validation']}",
        f"- Test samples: {baseline_metadata['split_counts']['test']}",
        f"- Unique test candidates: {unique_test_samples}",
        "- Split unit: match",
        "- Decision threshold source: validation",
        "",
        "## Models",
        "",
        "- Logistic regression with median imputation, scaling, and balanced classes",
        "- XGBoost with median imputation and balanced sample weights",
        "- Temporal GNN with two GCN layers, frame pooling, and GRU",
        f"- Temporal GNN device: {gnn_metadata['device']}",
        f"- Temporal GNN best epoch: {gnn_metadata['best_epoch']}",
        "",
        "## Test metrics",
        "",
    ]
    lines.extend(_markdown_table(
        test_metrics,
        [
            "model",
            "samples",
            "threshold",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "pr_auc",
        ],
    ))
    lines.extend([
        "",
        "## Test metrics by match",
        "",
    ])
    lines.extend(_markdown_table(
        test_match_metrics,
        [
            "model",
            "match_id",
            "samples",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "pr_auc",
        ],
    ))
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "Results are evaluated on a match-level holdout. The IDSSE source contains "
        "seven matches, so conclusions remain specific to this proof-of-concept "
        "dataset and must not be presented as broad professional-football "
        "generalization.",
        "",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
