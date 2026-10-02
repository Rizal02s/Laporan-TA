"""Quality checks and blinded review tables for gegenpressing annotations."""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_ANNOTATION_COLUMNS = {
    "candidate_id",
    "match_id",
    "is_gegenpressing",
    "annotation_confidence",
    "annotation_notes",
    "annotator",
}


def annotation_quality_checks(annotations: pd.DataFrame) -> pd.Series:
    """Validate annotation completeness and metadata without inspecting outcome."""

    missing = REQUIRED_ANNOTATION_COLUMNS.difference(annotations.columns)
    if missing:
        raise ValueError(f"Kolom anotasi tidak lengkap: {sorted(missing)}")

    labels = pd.to_numeric(annotations["is_gegenpressing"], errors="coerce")
    confidence = pd.to_numeric(
        annotations["annotation_confidence"],
        errors="coerce",
    )
    completed = labels.notna()
    uncertain = labels.eq(-1)
    notes_present = annotations["annotation_notes"].fillna("").str.strip().ne("")
    annotator_present = annotations["annotator"].fillna("").str.strip().ne("")

    return pd.Series({
        "all_annotations_completed": bool(completed.all()),
        "all_labels_valid": bool(labels.loc[completed].isin([-1, 0, 1]).all()),
        "candidate_id_unique": not annotations["candidate_id"].duplicated().any(),
        "confidence_complete": bool(confidence.loc[completed].notna().all()),
        "confidence_valid": bool(confidence.loc[completed].isin([1, 2, 3]).all()),
        "uncertain_have_notes": bool((~uncertain | notes_present).all()),
        "annotator_complete": bool(annotator_present.loc[completed].all()),
    }, name="passed")


def build_annotation_audit(
    annotations: pd.DataFrame,
    model_manifest: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Return label summaries, a blinded review queue, and integrity checks."""

    checks = annotation_quality_checks(annotations)
    split_map = model_manifest[["candidate_id", "split"]].drop_duplicates()
    working = annotations.merge(
        split_map,
        on="candidate_id",
        how="left",
        validate="one_to_one",
    )
    if working["split"].isna().any():
        missing_ids = working.loc[working["split"].isna(), "candidate_id"].tolist()
        raise ValueError(f"Kandidat anotasi tidak memiliki split: {missing_ids[:5]}")

    working["label"] = pd.to_numeric(
        working["is_gegenpressing"],
        errors="coerce",
    )
    working["confidence"] = pd.to_numeric(
        working["annotation_confidence"],
        errors="coerce",
    )
    working["completed"] = working["label"].notna()
    working["usable"] = working["label"].isin([0, 1])
    working["positive"] = working["label"].eq(1)
    working["negative"] = working["label"].eq(0)
    working["uncertain"] = working["label"].eq(-1)
    working["low_confidence"] = working["confidence"].eq(1)

    summary = (
        working.groupby(["split", "match_id"], observed=True)
        .agg(
            queue=("candidate_id", "size"),
            completed=("completed", "sum"),
            usable=("usable", "sum"),
            positive=("positive", "sum"),
            negative=("negative", "sum"),
            uncertain=("uncertain", "sum"),
            low_confidence=("low_confidence", "sum"),
        )
        .reset_index()
        .sort_values(["split", "match_id"])
        .reset_index(drop=True)
    )
    for column in (
        "queue",
        "completed",
        "usable",
        "positive",
        "negative",
        "uncertain",
        "low_confidence",
    ):
        summary[column] = summary[column].astype(int)

    review_mask = working["uncertain"] | working["low_confidence"]
    review = working.loc[review_mask].copy()
    review["review_reason"] = np.select(
        [
            review["uncertain"] & review["low_confidence"],
            review["uncertain"],
            review["low_confidence"],
        ],
        ["uncertain_and_low_confidence", "uncertain", "low_confidence"],
        default="",
    )
    review_columns = [
        "candidate_id",
        "match_id",
        "split",
        "period_id",
        "loss_timestamp",
        "loss_frame",
        "is_gegenpressing",
        "annotation_confidence",
        "annotation_notes",
        "annotated_at_utc",
        "annotator",
        "review_reason",
    ]
    review = review[[column for column in review_columns if column in review.columns]]
    return summary, review.reset_index(drop=True), checks
