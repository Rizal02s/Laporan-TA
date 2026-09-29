from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Rectangle
import numpy as np
import pandas as pd

from .idsse_episode_dataset import build_player_team_map


@dataclass(frozen=True)
class AnnotationConfig:
    """Configuration for manual gegenpressing annotation support."""

    decision_seconds: float = 2.0
    frame_rate_hz: int = 25
    direct_pressure_radius_m: float = 4.572
    approach_radius_m: float = 10.0
    min_approach_rate_mps: float = 1.0
    min_sustained_seconds: float = 0.4
    local_radius_m: float = 15.0
    pitch_length_m: float = 105.0
    pitch_width_m: float = 68.0

    @property
    def minimum_sustained_frames(self):
        return int(round(self.min_sustained_seconds * self.frame_rate_hz))


ANNOTATION_COLUMNS = [
    "is_gegenpressing",
    "annotation_confidence",
    "annotation_notes",
    "annotated_at_utc",
    "annotator",
]


def _longest_true_run(values):
    longest = 0
    current = 0
    for value in np.asarray(values, dtype=bool):
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _select_spaced_stratified(group, target_per_class, rng, min_spacing_seconds):
    working = group.copy()
    working["loss_seconds"] = pd.to_timedelta(
        working["loss_timestamp"]
    ).dt.total_seconds()
    working = working.iloc[rng.permutation(len(working))].copy()

    quotas = {0: target_per_class, 1: target_per_class}
    selected_indices = []
    selected_times = {}

    for idx, row in working.iterrows():
        label = int(row["label_regain_5s"])
        if label not in quotas or quotas[label] == 0:
            continue

        key = int(row["period_id"])
        previous_times = selected_times.setdefault(key, [])
        if any(
            abs(float(row["loss_seconds"]) - previous) < min_spacing_seconds
            for previous in previous_times
        ):
            continue

        selected_indices.append(idx)
        previous_times.append(float(row["loss_seconds"]))
        quotas[label] -= 1
        if all(value == 0 for value in quotas.values()):
            break

    if any(value > 0 for value in quotas.values()):
        missing = {key: value for key, value in quotas.items() if value > 0}
        raise ValueError(
            "Sampel terpisah waktu tidak mencukupi untuk kuota label: "
            f"{missing}. Turunkan min_spacing_seconds atau samples_per_match."
        )

    return group.loc[selected_indices].copy()


def build_annotation_manifest(
    episode_manifest,
    samples_per_match=40,
    random_state=42,
    min_spacing_seconds=2.0,
):
    """Create a balanced, reproducible manual-annotation queue."""

    if samples_per_match % 2:
        raise ValueError("samples_per_match harus genap agar label outcome seimbang.")

    source = episode_manifest.copy()
    source = source[source["strict_valid"].astype(bool)].copy()
    source = source.drop_duplicates("candidate_id")
    rng = np.random.default_rng(random_state)
    requested_per_class = samples_per_match // 2
    sampled = []

    for match_id, group in source.groupby("match_id", sort=True):
        label_counts = group["label_regain_5s"].astype(int).value_counts()
        maximum_target_per_class = min(
            requested_per_class,
            int(label_counts.get(0, 0)),
            int(label_counts.get(1, 0)),
        )
        if maximum_target_per_class == 0:
            raise ValueError(f"{match_id} tidak memiliki kedua outcome strict-valid.")

        match_sample = None
        target_per_class = maximum_target_per_class
        while target_per_class > 0 and match_sample is None:
            for _ in range(50):
                attempt_rng = np.random.default_rng(rng.integers(0, 2**32 - 1))
                try:
                    match_sample = _select_spaced_stratified(
                        group,
                        target_per_class=target_per_class,
                        rng=attempt_rng,
                        min_spacing_seconds=min_spacing_seconds,
                    )
                    break
                except ValueError:
                    continue
            if match_sample is None:
                target_per_class -= 1

        if match_sample is None:
            raise ValueError(f"Tidak dapat memilih queue anotasi untuk {match_id}.")
        match_sample = match_sample.iloc[rng.permutation(len(match_sample))].copy()
        match_sample["sample_target_per_outcome"] = target_per_class
        match_sample["within_match_order"] = np.arange(1, len(match_sample) + 1)
        sampled.append(match_sample)

    result = pd.concat(sampled, ignore_index=True)
    result = result.sort_values(
        ["match_id", "within_match_order"]
    ).reset_index(drop=True)
    result.insert(0, "annotation_order", np.arange(1, len(result) + 1))
    result = result.rename(columns={"label_regain_5s": "quick_regain_success"})

    for column in ANNOTATION_COLUMNS:
        result[column] = pd.NA

    result["is_gegenpressing"] = result["is_gegenpressing"].astype("Int64")
    result["annotation_confidence"] = result[
        "annotation_confidence"
    ].astype("Int64")
    return result


def initialize_annotation_manifest(
    episode_manifest_path,
    output_path,
    samples_per_match=40,
    random_state=42,
    min_spacing_seconds=2.0,
):
    """Load an existing queue or create it without overwriting prior labels."""

    output_path = Path(output_path)
    if output_path.exists():
        existing = pd.read_csv(output_path)
        for column in ("is_gegenpressing", "annotation_confidence"):
            existing[column] = pd.to_numeric(
                existing[column], errors="coerce"
            ).astype("Int64")
        return existing

    episode_manifest = pd.read_csv(episode_manifest_path)
    result = build_annotation_manifest(
        episode_manifest,
        samples_per_match=samples_per_match,
        random_state=random_state,
        min_spacing_seconds=min_spacing_seconds,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return result


def _player_ids(tracking):
    return sorted({
        column[:-2]
        for column in tracking.columns
        if column.startswith("DFL-OBJ-") and column.endswith("_x")
    })


def _active_players(loss_row, player_ids, player_team_map, team_id):
    return [
        player_id
        for player_id in player_ids
        if player_team_map.get(player_id) == team_id
        and pd.notna(loss_row.get(f"{player_id}_x"))
        and pd.notna(loss_row.get(f"{player_id}_y"))
    ]


def _positions_m(window, player_ids, config):
    positions = np.empty((len(window), len(player_ids), 2), dtype=float)
    for player_idx, player_id in enumerate(player_ids):
        positions[:, player_idx, 0] = (
            window[f"{player_id}_x"].to_numpy(dtype=float)
            * config.pitch_length_m
        )
        positions[:, player_idx, 1] = (
            window[f"{player_id}_y"].to_numpy(dtype=float)
            * config.pitch_width_m
        )
    return positions


def compute_annotation_context(candidate, tracking, events, config=None):
    """Calculate visual cues without assigning a gegenpressing label."""

    config = config or AnnotationConfig()
    candidate = dict(candidate)
    period_id = int(candidate["period_id"])
    loss_frame = int(candidate["loss_frame"])
    loss_seconds = pd.Timedelta(candidate["loss_timestamp"]).total_seconds()

    period = tracking[tracking["period_id"] == period_id].copy()
    period = period.sort_values(["timestamp", "frame_id"]).reset_index(drop=True)
    loss_rows = period[period["frame_id"] == loss_frame]
    if len(loss_rows) != 1:
        raise ValueError(f"Loss frame {loss_frame} tidak ditemukan secara unik.")
    loss_row = loss_rows.iloc[0]

    end_seconds = loss_seconds + config.decision_seconds
    time_seconds = period["timestamp"].dt.total_seconds()
    window = period[
        (time_seconds >= loss_seconds - 1e-9)
        & (time_seconds <= end_seconds + 1e-9)
    ].copy().reset_index(drop=True)
    if window.empty:
        raise ValueError("Window anotasi kosong.")

    player_team_map = build_player_team_map(events)
    all_player_ids = _player_ids(tracking)
    losing_players = _active_players(
        loss_row,
        all_player_ids,
        player_team_map,
        candidate["losing_team"],
    )
    opponent_players = _active_players(
        loss_row,
        all_player_ids,
        player_team_map,
        candidate["opponent_team"],
    )

    losing_positions = _positions_m(window, losing_players, config)
    opponent_positions = _positions_m(window, opponent_players, config)
    ball_positions = np.column_stack([
        window["ball_x"].to_numpy(dtype=float) * config.pitch_length_m,
        window["ball_y"].to_numpy(dtype=float) * config.pitch_width_m,
    ])

    losing_distances = np.linalg.norm(
        losing_positions - ball_positions[:, None, :], axis=2
    )
    opponent_distances = np.linalg.norm(
        opponent_positions - ball_positions[:, None, :], axis=2
    )
    dt = 1.0 / config.frame_rate_hz
    approach_rates = -np.gradient(losing_distances, dt, axis=0)

    direct_pressure = losing_distances <= config.direct_pressure_radius_m
    approaching_pressure = (
        (losing_distances <= config.approach_radius_m)
        & (approach_rates >= config.min_approach_rate_mps)
    )
    presser_mask = direct_pressure | approaching_pressure

    team_centroid = np.nanmean(losing_positions, axis=1)
    team_stretch = np.nanmean(
        np.linalg.norm(
            losing_positions - team_centroid[:, None, :], axis=2
        ),
        axis=1,
    )
    within_local = losing_distances <= config.local_radius_m
    local_compactness = np.full(len(window), np.nan, dtype=float)
    for frame_idx in range(len(window)):
        local_positions = losing_positions[frame_idx, within_local[frame_idx]]
        if len(local_positions) >= 2:
            local_centroid = local_positions.mean(axis=0)
            local_compactness[frame_idx] = np.mean(
                np.linalg.norm(local_positions - local_centroid, axis=1)
            )

    relative_times = (
        window["timestamp"].dt.total_seconds().to_numpy(dtype=float)
        - loss_seconds
    )
    metrics = pd.DataFrame({
        "relative_time_s": relative_times,
        "direct_pressers": direct_pressure.sum(axis=1),
        "approaching_pressers": approaching_pressure.sum(axis=1),
        "total_pressers": presser_mask.sum(axis=1),
        "losing_players_within_10m": (
            losing_distances <= config.approach_radius_m
        ).sum(axis=1),
        "losing_players_within_15m": within_local.sum(axis=1),
        "minimum_losing_distance_m": np.nanmin(losing_distances, axis=1),
        "maximum_approach_rate_mps": np.nanmax(approach_rates, axis=1),
        "nearest_opponent_to_ball_m": np.nanmin(opponent_distances, axis=1),
        "team_stretch_m": team_stretch,
        "local_compactness_m": local_compactness,
    })

    sustained_frames = config.minimum_sustained_frames
    pressure_run = _longest_true_run(metrics["total_pressers"] >= 1)
    collective_run = _longest_true_run(metrics["total_pressers"] >= 2)
    summary = pd.Series({
        "max_total_pressers": int(metrics["total_pressers"].max()),
        "max_direct_pressers": int(metrics["direct_pressers"].max()),
        "max_approaching_pressers": int(metrics["approaching_pressers"].max()),
        "pressure_duration_s": pressure_run / config.frame_rate_hz,
        "collective_pressure_duration_s": collective_run / config.frame_rate_hz,
        "sustained_pressure_cue": bool(pressure_run >= sustained_frames),
        "sustained_collective_cue": bool(collective_run >= sustained_frames),
        "minimum_losing_distance_m": float(
            metrics["minimum_losing_distance_m"].min()
        ),
        "maximum_approach_rate_mps": float(
            metrics["maximum_approach_rate_mps"].max()
        ),
        "max_losing_players_within_10m": int(
            metrics["losing_players_within_10m"].max()
        ),
        "mean_local_compactness_m": float(
            metrics["local_compactness_m"].mean()
        ),
        "team_stretch_change_m": float(
            metrics["team_stretch_m"].iloc[-1]
            - metrics["team_stretch_m"].iloc[0]
        ),
    })

    return {
        "candidate": candidate,
        "window": window,
        "relative_times": relative_times,
        "losing_players": losing_players,
        "opponent_players": opponent_players,
        "losing_positions": losing_positions,
        "opponent_positions": opponent_positions,
        "ball_positions": ball_positions,
        "losing_distances": losing_distances,
        "opponent_distances": opponent_distances,
        "approach_rates": approach_rates,
        "presser_mask": presser_mask,
        "metrics": metrics,
        "summary": summary,
        "config": config,
    }


def _draw_pitch(ax, config):
    length = config.pitch_length_m
    width = config.pitch_width_m
    ax.add_patch(Rectangle((0, 0), length, width, fill=False, color="#303030"))
    ax.plot([length / 2, length / 2], [0, width], color="#707070", lw=0.8)
    ax.add_patch(Circle((length / 2, width / 2), 9.15, fill=False, color="#909090"))
    ax.add_patch(Arc((0, width / 2), 18.3, 18.3, theta1=-53, theta2=53, color="#B0B0B0"))
    ax.add_patch(Arc((length, width / 2), 18.3, 18.3, theta1=127, theta2=233, color="#B0B0B0"))
    ax.set_xlim(-1, length + 1)
    ax.set_ylim(-1, width + 1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def plot_annotation_context(
    context,
    snapshot_times=(0.0, 0.5, 1.0, 1.5, 2.0),
):
    """Plot five snapshots and pressure cues without revealing regain outcome."""

    config = context["config"]
    fig, axes = plt.subplots(2, 3, figsize=(18, 9), constrained_layout=True)
    flat_axes = axes.ravel()

    for ax, target_time in zip(flat_axes[:5], snapshot_times):
        frame_idx = int(np.argmin(np.abs(context["relative_times"] - target_time)))
        _draw_pitch(ax, config)
        losing_positions = context["losing_positions"][frame_idx]
        opponent_positions = context["opponent_positions"][frame_idx]
        ball = context["ball_positions"][frame_idx]
        presser_mask = context["presser_mask"][frame_idx]

        ax.scatter(
            losing_positions[:, 0],
            losing_positions[:, 1],
            s=55,
            c="#D1495B",
            marker="o",
            label="Losing team",
            zorder=3,
        )
        ax.scatter(
            opponent_positions[:, 0],
            opponent_positions[:, 1],
            s=55,
            c="#277DA1",
            marker="^",
            label="Opponent",
            zorder=3,
        )
        ax.scatter(
            ball[0], ball[1], s=120, c="#111111", marker="*", zorder=5
        )
        ax.add_patch(Circle(
            ball,
            config.direct_pressure_radius_m,
            fill=False,
            color="#F4A261",
            lw=1.2,
        ))
        ax.add_patch(Circle(
            ball,
            config.approach_radius_m,
            fill=False,
            color="#E9C46A",
            lw=0.9,
            linestyle="--",
        ))

        if presser_mask.any():
            presser_positions = losing_positions[presser_mask]
            ax.scatter(
                presser_positions[:, 0],
                presser_positions[:, 1],
                s=150,
                facecolors="none",
                edgecolors="#2A9D8F",
                linewidths=2.2,
                zorder=4,
            )

        nearest_opponent = int(
            np.argmin(context["opponent_distances"][frame_idx])
        )
        carrier_proxy = opponent_positions[nearest_opponent]
        ax.scatter(
            carrier_proxy[0],
            carrier_proxy[1],
            s=155,
            facecolors="none",
            edgecolors="#264653",
            linewidths=2.2,
            zorder=4,
        )
        count = int(context["metrics"].iloc[frame_idx]["total_pressers"])
        ax.set_title(
            f"t={context['relative_times'][frame_idx]:.2f}s | cue pressers={count}"
        )

    cue_ax = flat_axes[5]
    metrics = context["metrics"]
    cue_ax.plot(
        metrics["relative_time_s"],
        metrics["total_pressers"],
        color="#2A9D8F",
        lw=2,
        label="Cue pressers",
    )
    cue_ax.plot(
        metrics["relative_time_s"],
        metrics["losing_players_within_10m"],
        color="#D1495B",
        lw=1.5,
        label="Losing players <=10m",
    )
    cue_ax.set_xlabel("Seconds after loss")
    cue_ax.set_ylabel("Player count")
    cue_ax.set_ylim(bottom=0)
    cue_ax.grid(alpha=0.2)
    distance_ax = cue_ax.twinx()
    distance_ax.plot(
        metrics["relative_time_s"],
        metrics["minimum_losing_distance_m"],
        color="#264653",
        linestyle="--",
        label="Nearest distance",
    )
    distance_ax.set_ylabel("Nearest losing player to ball (m)")
    handles, labels = cue_ax.get_legend_handles_labels()
    handles2, labels2 = distance_ax.get_legend_handles_labels()
    cue_ax.legend(handles + handles2, labels + labels2, loc="upper right")
    cue_ax.set_title("Pressure cues (not an automatic label)")

    candidate = context["candidate"]
    fig.suptitle(
        f"{candidate['candidate_id']} | losing team merah | opponent biru",
        fontsize=15,
    )
    return fig


def record_annotation(
    annotation_manifest,
    row_index,
    label,
    confidence,
    notes,
    annotator,
    output_path,
):
    """Record one decision and persist it immediately."""

    if label not in (-1, 0, 1):
        raise ValueError("label harus -1 (ragu), 0, atau 1.")
    if confidence not in (1, 2, 3):
        raise ValueError("confidence harus 1, 2, atau 3.")

    annotation_manifest.loc[row_index, "is_gegenpressing"] = label
    annotation_manifest.loc[row_index, "annotation_confidence"] = confidence
    annotation_manifest.loc[row_index, "annotation_notes"] = notes.strip()
    annotation_manifest.loc[row_index, "annotator"] = annotator.strip()
    annotation_manifest.loc[row_index, "annotated_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )
    annotation_manifest.to_csv(output_path, index=False)
    return annotation_manifest


def annotation_progress(annotation_manifest):
    labels = annotation_manifest["is_gegenpressing"]
    completed = int(labels.notna().sum())
    return pd.Series({
        "total_queue": int(len(annotation_manifest)),
        "completed": completed,
        "remaining": int(len(annotation_manifest) - completed),
        "gegenpressing": int((labels == 1).sum()),
        "non_gegenpressing": int((labels == 0).sum()),
        "uncertain": int((labels == -1).sum()),
    })
