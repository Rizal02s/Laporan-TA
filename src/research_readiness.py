"""Build leakage-safe manifests for the VAEP-Track modelling stage."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_MATCH_SPLIT = {
    "J03WMX": "train",
    "J03WN1": "train",
    "J03WOH": "train",
    "J03WOY": "train",
    "J03WR9": "train",
    "J03WQQ": "validation",
    "J03WPY": "test",
}


def build_model_manifest(
    episode_manifest: pd.DataFrame,
    annotation_manifest: pd.DataFrame,
    match_split: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Return strict-valid episodes with match-level splits and manual labels."""

    match_split = dict(match_split or DEFAULT_MATCH_SPLIT)
    required_episode_columns = {
        "candidate_id",
        "match_id",
        "strict_valid",
        "label_regain_5s",
    }
    missing = required_episode_columns.difference(episode_manifest.columns)
    if missing:
        raise ValueError(f"Kolom episode manifest tidak lengkap: {sorted(missing)}")

    episodes = episode_manifest.copy()
    strict_valid = episodes["strict_valid"]
    if strict_valid.dtype != bool:
        strict_valid = strict_valid.astype(str).str.lower().eq("true")
    episodes = episodes[strict_valid].copy()
    episodes["split"] = episodes["match_id"].map(match_split)
    if episodes["split"].isna().any():
        unknown = sorted(episodes.loc[episodes["split"].isna(), "match_id"].unique())
        raise ValueError(f"Match belum memiliki split: {unknown}")

    annotation_columns = [
        "candidate_id",
        "is_gegenpressing",
        "annotation_confidence",
        "annotation_notes",
        "annotator",
        "pilot_selected",
        "pilot_order",
    ]
    available_columns = [
        column for column in annotation_columns if column in annotation_manifest.columns
    ]
    annotations = annotation_manifest[available_columns].copy()
    if annotations["candidate_id"].duplicated().any():
        raise ValueError("candidate_id duplikat pada annotation manifest")

    model_manifest = episodes.merge(
        annotations,
        on="candidate_id",
        how="left",
        validate="one_to_one",
    )
    model_manifest["gegenpressing_label"] = pd.to_numeric(
        model_manifest.get("is_gegenpressing"),
        errors="coerce",
    ).astype("Int64")
    model_manifest["label_status"] = "unlabeled"
    model_manifest.loc[
        model_manifest["gegenpressing_label"].isin([0, 1]),
        "label_status",
    ] = "usable"
    model_manifest.loc[
        model_manifest["gegenpressing_label"].eq(-1),
        "label_status",
    ] = "uncertain_excluded"
    model_manifest["eligible_for_detection_training"] = model_manifest[
        "label_status"
    ].eq("usable")

    return model_manifest.sort_values(
        ["split", "match_id", "period_id", "loss_frame"]
    ).reset_index(drop=True)


def build_match_split_manifest(model_manifest: pd.DataFrame) -> pd.DataFrame:
    """Summarize episode and annotation counts for each match."""

    summary = (
        model_manifest.groupby(["split", "match_id"], observed=True)
        .agg(
            strict_valid_episodes=("candidate_id", "size"),
            quick_regain_positive=("label_regain_5s", "sum"),
            annotated_usable=("eligible_for_detection_training", "sum"),
            annotated_uncertain=(
                "label_status",
                lambda values: int((values == "uncertain_excluded").sum()),
            ),
        )
        .reset_index()
    )
    summary["quick_regain_negative"] = (
        summary["strict_valid_episodes"] - summary["quick_regain_positive"]
    )
    return summary[
        [
            "split",
            "match_id",
            "strict_valid_episodes",
            "quick_regain_positive",
            "quick_regain_negative",
            "annotated_usable",
            "annotated_uncertain",
        ]
    ].sort_values(["split", "match_id"]).reset_index(drop=True)


def validate_model_manifest(model_manifest: pd.DataFrame) -> pd.Series:
    """Run the main leakage and label-integrity checks."""

    match_split_counts = model_manifest.groupby("match_id")["split"].nunique()
    checks = {
        "candidate_id_unique": not model_manifest["candidate_id"].duplicated().any(),
        "all_matches_have_one_split": bool(match_split_counts.eq(1).all()),
        "required_splits_present": set(model_manifest["split"].unique())
        == {"train", "validation", "test"},
        "only_binary_labels_trainable": bool(
            model_manifest.loc[
                model_manifest["eligible_for_detection_training"],
                "gegenpressing_label",
            ].isin([0, 1]).all()
        ),
        "uncertain_labels_excluded": bool(
            (~model_manifest.loc[
                model_manifest["gegenpressing_label"].eq(-1),
                "eligible_for_detection_training",
            ]).all()
        ),
    }
    return pd.Series(checks, name="passed")
