from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EpisodeSampleConfig:
    pre_seconds: float = 2.0
    post_seconds: float = 2.0
    regain_horizon_seconds: float = 5.0
    frame_rate_hz: int = 25
    k_neighbors: int = 4

    @property
    def expected_frame_count(self):
        duration = self.pre_seconds + self.post_seconds
        return int(round(duration * self.frame_rate_hz)) + 1


def load_match(data_dir, match_id):
    data_dir = Path(data_dir)
    tracking_path = data_dir / f"{match_id}_tracking.csv"
    events_path = data_dir / f"{match_id}_events.csv"

    if not tracking_path.exists() or not events_path.exists():
        raise FileNotFoundError(
            f"Tracking/event file untuk {match_id} tidak lengkap di {data_dir}"
        )

    tracking = pd.read_csv(tracking_path)
    events = pd.read_csv(events_path)

    tracking["timestamp"] = pd.to_timedelta(
        tracking["timestamp"],
        errors="coerce",
    )
    tracking = tracking.sort_values(
        ["period_id", "timestamp", "frame_id"]
    ).reset_index(drop=True).copy()

    return tracking, events


def detect_turnover_candidates(
    tracking,
    match_id,
    regain_horizon_seconds=5.0,
):
    working = tracking.copy()
    working["prev_owning_team"] = (
        working.groupby("period_id")["ball_owning_team_id"].shift(1)
    )
    working["team_changed"] = (
        working["ball_owning_team_id"].notna()
        & working["prev_owning_team"].notna()
        & (
            working["ball_owning_team_id"]
            != working["prev_owning_team"]
        )
    )

    changes = working[
        working["team_changed"]
        & (working["ball_state"] == "alive")
    ].copy()
    changes = changes.sort_values(
        ["period_id", "timestamp", "frame_id"]
    ).reset_index(drop=True)
    changes["time_seconds"] = changes["timestamp"].dt.total_seconds()

    records = []
    for period_id, group in changes.groupby("period_id", sort=False):
        group = group.reset_index(drop=True)
        times = group["time_seconds"].to_numpy(dtype=float)
        owners = group["ball_owning_team_id"].to_numpy()
        losing_teams = group["prev_owning_team"].to_numpy()

        for local_idx, row in group.iterrows():
            loss_seconds = times[local_idx]
            losing_team = losing_teams[local_idx]
            upper = np.searchsorted(
                times,
                loss_seconds + regain_horizon_seconds,
                side="right",
            )

            regain_idx = None
            for future_idx in range(local_idx + 1, upper):
                if owners[future_idx] == losing_team:
                    regain_idx = future_idx
                    break

            regain_found = regain_idx is not None
            regain_timestamp = pd.NaT
            regain_frame = pd.NA
            regain_gap_seconds = np.nan

            if regain_found:
                regain_row = group.iloc[regain_idx]
                regain_timestamp = pd.Timedelta(regain_row["timestamp"])
                regain_frame = int(regain_row["frame_id"])
                regain_gap_seconds = times[regain_idx] - loss_seconds

            loss_frame = int(row["frame_id"])
            candidate_id = f"{match_id}_P{int(period_id)}_F{loss_frame}"
            records.append({
                "candidate_id": candidate_id,
                "match_id": match_id,
                "period_id": int(period_id),
                "loss_timestamp": pd.Timedelta(row["timestamp"]),
                "loss_frame": loss_frame,
                "losing_team": losing_team,
                "opponent_team": row["ball_owning_team_id"],
                "regain_found": bool(regain_found),
                "label_regain_5s": int(regain_found),
                "regain_timestamp": regain_timestamp,
                "regain_frame": regain_frame,
                "regain_gap_seconds": regain_gap_seconds,
            })

    candidates = pd.DataFrame(records)
    if not candidates.empty:
        candidates["regain_timestamp"] = pd.to_timedelta(
            candidates["regain_timestamp"],
            errors="coerce",
        )

    return candidates


def build_player_team_map(events):
    return (
        events[["player_id", "team_id"]]
        .dropna()
        .drop_duplicates()
        .groupby("player_id")["team_id"]
        .first()
        .to_dict()
    )


def _tracking_player_ids(tracking):
    return sorted({
        column[:-2]
        for column in tracking.columns
        if column.startswith("DFL-OBJ-") and column.endswith("_x")
    })


def _period_context(tracking, period_id):
    period_tracking = tracking[
        tracking["period_id"] == period_id
    ].reset_index(drop=True)

    return {
        "tracking": period_tracking,
        "frame_ids": period_tracking["frame_id"].to_numpy(dtype=int),
        "time_seconds": (
            period_tracking["timestamp"].dt.total_seconds().to_numpy(dtype=float)
        ),
    }


def _loss_row(period_context, loss_frame):
    frame_ids = period_context["frame_ids"]
    position = int(np.searchsorted(frame_ids, loss_frame))

    if position >= len(frame_ids) or frame_ids[position] != loss_frame:
        return None

    return period_context["tracking"].iloc[position]


def _window_rows(period_context, loss_seconds, config):
    times = period_context["time_seconds"]
    start_seconds = loss_seconds - config.pre_seconds
    end_seconds = loss_seconds + config.post_seconds
    start = int(np.searchsorted(times, start_seconds, side="left"))
    end = int(np.searchsorted(times, end_seconds, side="right"))
    return period_context["tracking"].iloc[start:end].copy()


def _active_roster(
    loss_row,
    player_ids,
    player_team_map,
    losing_team,
    opponent_team,
):
    active_player_ids = []

    if loss_row is None:
        return active_player_ids

    episode_teams = {losing_team, opponent_team}
    for player_id in player_ids:
        x = loss_row.get(f"{player_id}_x", np.nan)
        y = loss_row.get(f"{player_id}_y", np.nan)
        team_id = player_team_map.get(player_id)

        if team_id in episode_teams and pd.notna(x) and pd.notna(y):
            active_player_ids.append(player_id)

    return active_player_ids


def _node_arrays(
    window,
    active_player_ids,
    player_team_map,
    losing_team,
    opponent_team,
):
    node_ids = active_player_ids + ["BALL"]
    frame_count = len(window)
    node_count = len(node_ids)
    features = np.zeros((frame_count, node_count, 6), dtype=np.float32)
    node_mask = np.zeros((frame_count, node_count), dtype=bool)

    for node_idx, player_id in enumerate(active_player_ids):
        x = window[f"{player_id}_x"].to_numpy(dtype=float)
        y = window[f"{player_id}_y"].to_numpy(dtype=float)
        speed_col = f"{player_id}_s"
        if speed_col in window.columns:
            speed = window[speed_col].fillna(0).to_numpy(dtype=float)
        else:
            speed = np.zeros(frame_count, dtype=float)

        valid = np.isfinite(x) & np.isfinite(y)
        node_mask[:, node_idx] = valid
        features[valid, node_idx, 0] = x[valid]
        features[valid, node_idx, 1] = y[valid]
        features[:, node_idx, 2] = speed
        features[:, node_idx, 4] = float(
            player_team_map.get(player_id) == losing_team
        )
        features[:, node_idx, 5] = float(
            player_team_map.get(player_id) == opponent_team
        )

    ball_idx = node_count - 1
    ball_x = window["ball_x"].to_numpy(dtype=float)
    ball_y = window["ball_y"].to_numpy(dtype=float)
    ball_valid = np.isfinite(ball_x) & np.isfinite(ball_y)
    ball_speed = window["ball_speed"].fillna(0).to_numpy(dtype=float)
    node_mask[:, ball_idx] = ball_valid
    features[ball_valid, ball_idx, 0] = ball_x[ball_valid]
    features[ball_valid, ball_idx, 1] = ball_y[ball_valid]
    features[:, ball_idx, 2] = ball_speed
    features[:, ball_idx, 3] = 1.0

    return node_ids, features, node_mask


def _graph_edges(features, node_mask, k_neighbors):
    edge_indices = []
    edge_attributes = []

    for frame_features, frame_mask in zip(features, node_mask):
        valid_indices = np.flatnonzero(frame_mask)
        positions = frame_features[valid_indices, :2]
        frame_edges = []
        frame_distances = []

        if len(valid_indices) > k_neighbors:
            distance_matrix = np.linalg.norm(
                positions[:, None, :] - positions[None, :, :],
                axis=2,
            )

            for local_source, source_idx in enumerate(valid_indices):
                order = np.argsort(distance_matrix[local_source])
                order = order[order != local_source][:k_neighbors]

                for local_target in order:
                    frame_edges.append([
                        int(source_idx),
                        int(valid_indices[local_target]),
                    ])
                    frame_distances.append([
                        float(distance_matrix[local_source, local_target])
                    ])

        edge_indices.append(
            np.asarray(frame_edges, dtype=np.int64).reshape(-1, 2).T
        )
        edge_attributes.append(
            np.asarray(frame_distances, dtype=np.float32).reshape(-1, 1)
        )

    return edge_indices, edge_attributes


def _evaluate_sample(
    event,
    window,
    active_player_ids,
    player_team_map,
    node_mask,
    loss_row_found,
    config,
):
    frame_ids = window["frame_id"].to_numpy(dtype=int)
    timestamps = window["timestamp"].dt.total_seconds().to_numpy(dtype=float)
    losing_count = sum(
        player_team_map.get(player_id) == event["losing_team"]
        for player_id in active_player_ids
    )
    opponent_count = sum(
        player_team_map.get(player_id) == event["opponent_team"]
        for player_id in active_player_ids
    )

    complete_window = len(window) == config.expected_frame_count
    continuous_frames = (
        len(frame_ids) > 1 and np.all(np.diff(frame_ids) == 1)
    )
    expected_step = 1.0 / config.frame_rate_hz
    regular_timestamps = (
        len(timestamps) > 1
        and np.allclose(np.diff(timestamps), expected_step, atol=1e-6)
    )
    invalid_node_observations = int((~node_mask).sum())
    max_invalid_nodes_per_frame = (
        int((~node_mask).sum(axis=1).max()) if len(node_mask) else 0
    )
    ball_invalid_frames = (
        int((~node_mask[:, -1]).sum()) if node_mask.shape[1] else 0
    )

    reasons = []
    if not loss_row_found:
        reasons.append("missing_loss_frame")
    if len(active_player_ids) != 22:
        reasons.append("active_player_count_not_22")
    if losing_count != 11 or opponent_count != 11:
        reasons.append("team_split_not_11_11")
    if not complete_window:
        reasons.append("incomplete_window")
    if not continuous_frames:
        reasons.append("non_contiguous_frames")
    if not regular_timestamps:
        reasons.append("irregular_timestamps")
    if invalid_node_observations > 0:
        reasons.append("invalid_node_positions")

    return {
        "candidate_id": event["candidate_id"],
        "match_id": event["match_id"],
        "period_id": int(event["period_id"]),
        "loss_frame": int(event["loss_frame"]),
        "loss_timestamp": event["loss_timestamp"],
        "label_regain_5s": int(event["label_regain_5s"]),
        "frame_count": int(len(window)),
        "expected_frame_count": config.expected_frame_count,
        "active_player_count": int(len(active_player_ids)),
        "losing_player_count": int(losing_count),
        "opponent_player_count": int(opponent_count),
        "invalid_node_observations": invalid_node_observations,
        "max_invalid_nodes_per_frame": max_invalid_nodes_per_frame,
        "ball_invalid_frames": ball_invalid_frames,
        "complete_window": bool(complete_window),
        "continuous_frames": bool(continuous_frames),
        "regular_25hz": bool(regular_timestamps),
        "strict_valid": len(reasons) == 0,
        "failure_reasons": "|".join(reasons),
    }


def build_episode_sample(
    event,
    tracking,
    events,
    config=None,
    materialize_graphs=True,
):
    config = config or EpisodeSampleConfig()
    event = dict(event)
    period_id = int(event["period_id"])
    loss_frame = int(event["loss_frame"])
    loss_timestamp = pd.Timedelta(event["loss_timestamp"])
    loss_seconds = loss_timestamp.total_seconds()

    player_team_map = build_player_team_map(events)
    player_ids = _tracking_player_ids(tracking)
    period_context = _period_context(tracking, period_id)
    loss_row = _loss_row(period_context, loss_frame)
    window = _window_rows(period_context, loss_seconds, config)
    active_player_ids = _active_roster(
        loss_row,
        player_ids,
        player_team_map,
        event["losing_team"],
        event["opponent_team"],
    )
    node_ids, features, node_mask = _node_arrays(
        window,
        active_player_ids,
        player_team_map,
        event["losing_team"],
        event["opponent_team"],
    )
    audit = _evaluate_sample(
        event,
        window,
        active_player_ids,
        player_team_map,
        node_mask,
        loss_row is not None,
        config,
    )

    sample = {
        "candidate_id": event["candidate_id"],
        "match_id": event["match_id"],
        "label": int(event["label_regain_5s"]),
        "node_ids": node_ids,
        "frame_ids": window["frame_id"].to_numpy(dtype=np.int64),
        "relative_times": (
            window["timestamp"].dt.total_seconds().to_numpy(dtype=float)
            - loss_seconds
        ).astype(np.float32),
        "node_features": features,
        "node_mask": node_mask,
        "audit": audit,
    }

    if materialize_graphs:
        edge_index, edge_attr = _graph_edges(
            features,
            node_mask,
            config.k_neighbors,
        )
        sample["edge_index"] = edge_index
        sample["edge_attr"] = edge_attr

    return sample


def audit_match(tracking, events, candidates, config=None):
    config = config or EpisodeSampleConfig()
    player_team_map = build_player_team_map(events)
    player_ids = _tracking_player_ids(tracking)
    period_contexts = {
        int(period_id): _period_context(tracking, period_id)
        for period_id in tracking["period_id"].dropna().unique()
    }
    audits = []

    for _, event_row in candidates.iterrows():
        event = event_row.to_dict()
        period_context = period_contexts[int(event["period_id"])]
        loss_row = _loss_row(period_context, int(event["loss_frame"]))
        window = _window_rows(
            period_context,
            pd.Timedelta(event["loss_timestamp"]).total_seconds(),
            config,
        )
        active_player_ids = _active_roster(
            loss_row,
            player_ids,
            player_team_map,
            event["losing_team"],
            event["opponent_team"],
        )
        _, _, node_mask = _node_arrays(
            window,
            active_player_ids,
            player_team_map,
            event["losing_team"],
            event["opponent_team"],
        )
        audits.append(_evaluate_sample(
            event,
            window,
            active_player_ids,
            player_team_map,
            node_mask,
            loss_row is not None,
            config,
        ))

    return pd.DataFrame(audits)


def audit_all_matches(
    data_dir,
    match_ids,
    config=None,
    verbose=True,
):
    config = config or EpisodeSampleConfig()
    candidate_tables = []
    audit_tables = []

    for match_id in match_ids:
        tracking, events = load_match(data_dir, match_id)
        candidates = detect_turnover_candidates(
            tracking,
            match_id,
            regain_horizon_seconds=config.regain_horizon_seconds,
        )
        audit = audit_match(
            tracking,
            events,
            candidates,
            config=config,
        )
        candidate_tables.append(candidates)
        audit_tables.append(audit)

        if verbose:
            print(
                f"{match_id}: candidates={len(candidates)}, "
                f"positive={int(candidates['label_regain_5s'].sum())}, "
                f"strict_valid={int(audit['strict_valid'].sum())}"
            )

    all_candidates = pd.concat(candidate_tables, ignore_index=True)
    all_audits = pd.concat(audit_tables, ignore_index=True)
    return all_candidates, all_audits
