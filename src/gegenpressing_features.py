"""Feature extraction for the VAEP-Track gegenpressing baseline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.gegenpressing_annotation import AnnotationConfig, compute_annotation_context
from src.idsse_episode_dataset import load_match


BASELINE_FEATURE_COLUMNS = [
    "max_total_pressers",
    "max_direct_pressers",
    "max_approaching_pressers",
    "pressure_duration_s",
    "collective_pressure_duration_s",
    "sustained_pressure_cue",
    "sustained_collective_cue",
    "minimum_losing_distance_m",
    "maximum_approach_rate_mps",
    "max_losing_players_within_10m",
    "mean_local_compactness_m",
    "team_stretch_change_m",
]


def build_baseline_feature_table(
    candidates: pd.DataFrame,
    data_dir: str | Path,
    config: AnnotationConfig | None = None,
) -> pd.DataFrame:
    """Extract behavior cues for every candidate without using outcome labels."""

    config = config or AnnotationConfig()
    required_columns = {
        "candidate_id",
        "match_id",
        "period_id",
        "loss_frame",
        "loss_timestamp",
        "losing_team",
        "opponent_team",
    }
    missing = required_columns.difference(candidates.columns)
    if missing:
        raise ValueError(f"Kolom kandidat tidak lengkap: {sorted(missing)}")
    if candidates["candidate_id"].duplicated().any():
        raise ValueError("candidate_id duplikat pada kandidat feature extraction")

    records = []
    ordered = candidates.sort_values(
        ["match_id", "period_id", "loss_frame"]
    )
    for match_id, match_candidates in ordered.groupby("match_id", sort=False):
        tracking, events = load_match(data_dir, match_id)
        for _, candidate in match_candidates.iterrows():
            context = compute_annotation_context(
                candidate,
                tracking,
                events,
                config,
            )
            record = {
                "candidate_id": candidate["candidate_id"],
                "match_id": match_id,
                "period_id": int(candidate["period_id"]),
                "loss_frame": int(candidate["loss_frame"]),
                "loss_timestamp": candidate["loss_timestamp"],
            }
            record.update(context["summary"].to_dict())
            records.append(record)

    features = pd.DataFrame(records)
    boolean_columns = [
        "sustained_pressure_cue",
        "sustained_collective_cue",
    ]
    for column in boolean_columns:
        features[column] = features[column].astype(bool)
    return features[
        [
            "candidate_id",
            "match_id",
            "period_id",
            "loss_frame",
            "loss_timestamp",
            *BASELINE_FEATURE_COLUMNS,
        ]
    ]


def audit_baseline_feature_table(
    features: pd.DataFrame,
    expected_candidates: pd.DataFrame,
) -> pd.Series:
    """Check row identity and feature integrity before model training."""

    expected_ids = set(expected_candidates["candidate_id"])
    actual_ids = set(features["candidate_id"])
    numeric_features = features[BASELINE_FEATURE_COLUMNS].apply(
        pd.to_numeric,
        errors="coerce",
    )
    checks = {
        "candidate_id_unique": not features["candidate_id"].duplicated().any(),
        "candidate_ids_complete": actual_ids == expected_ids,
        "feature_columns_complete": set(BASELINE_FEATURE_COLUMNS).issubset(features.columns),
        "no_infinite_numeric_values": bool(
            (~numeric_features.isin([float("inf"), float("-inf")])).all().all()
        ),
        "outcome_not_in_features": "quick_regain_success" not in features.columns
        and "label_regain_5s" not in features.columns,
        "gegenpressing_label_not_in_features": "is_gegenpressing" not in features.columns,
    }
    return pd.Series(checks, name="passed")
