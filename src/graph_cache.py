"""Materialize fixed-shape temporal graph tensors for model training."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import torch

from src.idsse_episode_dataset import EpisodeSampleConfig, build_episode_sample, load_match


def build_graph_cache(
    candidates: pd.DataFrame,
    data_dir: str | Path,
    cache_dir: str | Path,
    *,
    config: EpisodeSampleConfig | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    """Save one tensor dictionary per strict-valid annotation candidate."""

    config = config or EpisodeSampleConfig()
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    required = {
        "candidate_id",
        "match_id",
        "period_id",
        "loss_frame",
        "loss_timestamp",
        "losing_team",
        "opponent_team",
    }
    missing = required.difference(candidates.columns)
    if missing:
        raise ValueError(f"Kolom kandidat tidak lengkap: {sorted(missing)}")
    if candidates["candidate_id"].duplicated().any():
        raise ValueError("candidate_id duplikat pada graph cache input")

    records = []
    ordered = candidates.sort_values(["match_id", "period_id", "loss_frame"])
    for match_id, match_candidates in ordered.groupby("match_id", sort=False):
        tracking, events = load_match(data_dir, match_id)
        for _, candidate in match_candidates.iterrows():
            cache_path = cache_dir / f"{candidate['candidate_id']}.pt"
            if cache_path.exists() and not overwrite:
                item = torch.load(cache_path, map_location="cpu", weights_only=True)
            else:
                event = candidate.to_dict()
                if "label_regain_5s" not in event:
                    event["label_regain_5s"] = int(
                        event.get("quick_regain_success", 0)
                    )
                sample = build_episode_sample(
                    event,
                    tracking,
                    events,
                    config=config,
                    materialize_graphs=True,
                )
                if not sample["audit"]["strict_valid"]:
                    raise ValueError(
                        f"Sample tidak strict-valid: {candidate['candidate_id']}"
                    )
                item = {
                    "candidate_id": str(candidate["candidate_id"]),
                    "match_id": str(match_id),
                    "x": torch.as_tensor(
                        sample["node_features"],
                        dtype=torch.float32,
                    ),
                    "edge_index": torch.stack([
                        torch.as_tensor(edges, dtype=torch.long)
                        for edges in sample["edge_index"]
                    ]),
                    "node_mask": torch.as_tensor(
                        sample["node_mask"],
                        dtype=torch.bool,
                    ),
                    "relative_times": torch.as_tensor(
                        sample["relative_times"],
                        dtype=torch.float32,
                    ),
                }
                temporary_path = cache_path.with_suffix(".tmp")
                torch.save(item, temporary_path)
                temporary_path.replace(cache_path)

            x = item["x"]
            edge_index = item["edge_index"]
            node_mask = item["node_mask"]
            records.append({
                "candidate_id": item["candidate_id"],
                "match_id": item["match_id"],
                "cache_file": cache_path.name,
                "frames": int(x.shape[0]),
                "nodes": int(x.shape[1]),
                "node_features": int(x.shape[2]),
                "edges_per_frame_min": int(edge_index.shape[-1]),
                "edges_per_frame_max": int(edge_index.shape[-1]),
                "invalid_node_observations": int((~node_mask).sum().item()),
            })

    return pd.DataFrame(records).sort_values("candidate_id").reset_index(drop=True)


def audit_graph_cache(
    cache_manifest: pd.DataFrame,
    expected_candidates: pd.DataFrame,
    config: EpisodeSampleConfig | None = None,
) -> pd.Series:
    """Verify fixed temporal and graph dimensions for all cached samples."""

    config = config or EpisodeSampleConfig()
    expected_ids = set(expected_candidates["candidate_id"])
    actual_ids = set(cache_manifest["candidate_id"])
    return pd.Series({
        "candidate_id_unique": not cache_manifest["candidate_id"].duplicated().any(),
        "candidate_ids_complete": actual_ids == expected_ids,
        "all_101_frames": bool(
            cache_manifest["frames"].eq(config.expected_frame_count).all()
        ),
        "all_23_nodes": bool(cache_manifest["nodes"].eq(23).all()),
        "all_6_node_features": bool(cache_manifest["node_features"].eq(6).all()),
        "all_92_edges_per_frame": bool(
            cache_manifest["edges_per_frame_min"].eq(92).all()
            and cache_manifest["edges_per_frame_max"].eq(92).all()
        ),
        "all_nodes_valid": bool(
            cache_manifest["invalid_node_observations"].eq(0).all()
        ),
    }, name="passed")
