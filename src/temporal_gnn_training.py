"""Temporal GNN training and evaluation for VAEP-Track."""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torch_geometric.nn import GCNConv

from src.baseline_training import (
    baseline_readiness,
    choose_validation_threshold,
    classification_metrics,
)


CONTINUOUS_FEATURE_INDICES = (0, 1, 2)


class GraphSequenceDataset(Dataset):
    def __init__(
        self,
        rows: pd.DataFrame,
        cache_dir: str | Path,
        feature_mean: torch.Tensor | np.ndarray | None = None,
        feature_std: torch.Tensor | np.ndarray | None = None,
    ):
        self.rows = rows.reset_index(drop=True).copy()
        self.cache_dir = Path(cache_dir)
        if (feature_mean is None) != (feature_std is None):
            raise ValueError("feature_mean dan feature_std harus diberikan bersama")
        self.feature_mean = (
            None
            if feature_mean is None
            else torch.as_tensor(feature_mean, dtype=torch.float32)
        )
        self.feature_std = (
            None
            if feature_std is None
            else torch.as_tensor(feature_std, dtype=torch.float32)
        )

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, object]:
        row = self.rows.iloc[index]
        item = torch.load(
            self.cache_dir / row["cache_file"],
            map_location="cpu",
            weights_only=True,
        )
        x = item["x"].clone()
        node_mask = item["node_mask"]
        if self.feature_mean is not None:
            continuous = (
                x[..., CONTINUOUS_FEATURE_INDICES] - self.feature_mean
            ) / self.feature_std
            x[..., CONTINUOUS_FEATURE_INDICES] = torch.where(
                node_mask.unsqueeze(-1),
                continuous,
                torch.zeros_like(continuous),
            )
        return {
            "candidate_id": row["candidate_id"],
            "match_id": row["match_id"],
            "x": x,
            "edge_index": item["edge_index"],
            "node_mask": node_mask,
            "y": torch.tensor(int(row["gegenpressing_label"]), dtype=torch.long),
        }


def collate_graph_sequences(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "candidate_id": [item["candidate_id"] for item in items],
        "match_id": [item["match_id"] for item in items],
        "x": torch.stack([item["x"] for item in items]),
        "edge_index": torch.stack([item["edge_index"] for item in items]),
        "node_mask": torch.stack([item["node_mask"] for item in items]),
        "y": torch.stack([item["y"] for item in items]),
    }


class TemporalGNN(nn.Module):
    """GCN frame encoder followed by a GRU temporal encoder."""

    def __init__(
        self,
        in_channels: int = 6,
        graph_hidden_channels: int = 32,
        temporal_hidden_channels: int = 32,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.gcn1 = GCNConv(in_channels, graph_hidden_channels)
        self.gcn2 = GCNConv(graph_hidden_channels, graph_hidden_channels)
        self.graph_norm = nn.LayerNorm(graph_hidden_channels)
        self.temporal = nn.GRU(
            graph_hidden_channels,
            temporal_hidden_channels,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(temporal_hidden_channels, 2)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        node_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch_size, frames, nodes, features = x.shape
        edges_per_frame = edge_index.shape[-1]
        flat_x = x.reshape(batch_size * frames * nodes, features)

        graph_offsets = (
            torch.arange(batch_size * frames, device=x.device)
            .reshape(batch_size, frames, 1, 1)
            * nodes
        )
        flat_edge_index = (
            edge_index + graph_offsets
        ).permute(2, 0, 1, 3).reshape(2, batch_size * frames * edges_per_frame)

        hidden = torch.relu(self.gcn1(flat_x, flat_edge_index))
        hidden = torch.relu(self.gcn2(hidden, flat_edge_index))
        hidden = self.graph_norm(hidden)
        hidden = hidden.reshape(batch_size, frames, nodes, -1)

        mask = node_mask.unsqueeze(-1).to(hidden.dtype)
        frame_embeddings = (hidden * mask).sum(dim=2) / mask.sum(dim=2).clamp_min(1.0)
        temporal_output, _ = self.temporal(frame_embeddings)
        episode_embedding = temporal_output[:, -1, :]
        logits = self.classifier(self.dropout(episode_embedding))
        return logits, episode_embedding


def prepare_gnn_dataset(
    model_manifest: pd.DataFrame,
    cache_manifest: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "candidate_id",
        "match_id",
        "split",
        "gegenpressing_label",
        "label_status",
        "eligible_for_detection_training",
    ]
    cache_ids = set(cache_manifest["candidate_id"])
    annotation_queue = model_manifest[
        model_manifest["candidate_id"].isin(cache_ids)
    ][columns].copy()
    dataset = annotation_queue.merge(
        cache_manifest[["candidate_id", "match_id", "cache_file"]],
        on=["candidate_id", "match_id"],
        how="inner",
        validate="one_to_one",
    )
    if len(dataset) != len(cache_manifest):
        raise ValueError("Graph cache dan annotation queue tidak cocok")
    return dataset


def fit_graph_feature_normalizer(
    train_rows: pd.DataFrame,
    cache_dir: str | Path,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Fit continuous-node feature statistics using train episodes only."""

    cache_dir = Path(cache_dir)
    observations = []
    for cache_file in train_rows["cache_file"]:
        item = torch.load(
            cache_dir / cache_file,
            map_location="cpu",
            weights_only=True,
        )
        observations.append(
            item["x"][item["node_mask"]][:, CONTINUOUS_FEATURE_INDICES]
        )
    if not observations:
        raise ValueError("Train split kosong; normalizer GNN tidak dapat dihitung")
    values = torch.cat(observations, dim=0).float()
    feature_mean = values.mean(dim=0)
    feature_std = values.std(dim=0, unbiased=False).clamp_min(1e-6)
    return feature_mean, feature_std


def _set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def _move_batch(batch: dict[str, object], device: torch.device) -> dict[str, object]:
    moved = dict(batch)
    for key in ("x", "edge_index", "node_mask", "y"):
        moved[key] = batch[key].to(device)
    return moved


def _predict(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str], float]:
    model.eval()
    probabilities = []
    truths = []
    candidate_ids = []
    match_ids = []
    loss_sum = 0.0
    sample_count = 0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for batch in loader:
            batch = _move_batch(batch, device)
            logits, _ = model(batch["x"], batch["edge_index"], batch["node_mask"])
            batch_size = int(batch["y"].shape[0])
            loss_sum += float(criterion(logits, batch["y"]).item()) * batch_size
            sample_count += batch_size
            probabilities.extend(torch.softmax(logits, dim=1)[:, 1].cpu().tolist())
            truths.extend(batch["y"].cpu().tolist())
            candidate_ids.extend(batch["candidate_id"])
            match_ids.extend(batch["match_id"])
    return (
        np.asarray(truths, dtype=int),
        np.asarray(probabilities, dtype=float),
        candidate_ids,
        match_ids,
        loss_sum / sample_count,
    )


def train_temporal_gnn(
    dataset: pd.DataFrame,
    annotations: pd.DataFrame,
    cache_dir: str | Path,
    output_dir: str | Path,
    *,
    final_run: bool,
    random_state: int = 42,
    batch_size: int = 4,
    max_epochs: int = 60,
    patience: int = 10,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4,
    minimum_per_class_per_split: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    """Train with validation early stopping and evaluate once on test."""

    readiness = baseline_readiness(
        annotations,
        dataset,
        minimum_per_class_per_split=minimum_per_class_per_split,
    )
    if final_run and not readiness.all():
        failed = readiness[~readiness].index.tolist()
        raise RuntimeError(f"Final training gate gagal: {failed}")

    usable = dataset[dataset["eligible_for_detection_training"]].copy()
    split_rows = {
        split: usable[usable["split"].eq(split)].copy()
        for split in ("train", "validation", "test")
    }
    for split, rows in split_rows.items():
        if rows.empty or rows["gegenpressing_label"].nunique() < 2:
            raise ValueError(f"Split {split} belum memiliki dua kelas")

    _set_seeds(random_state)
    generator = torch.Generator().manual_seed(random_state)
    feature_mean, feature_std = fit_graph_feature_normalizer(
        split_rows["train"],
        cache_dir,
    )
    loaders = {
        split: DataLoader(
            GraphSequenceDataset(
                rows,
                cache_dir,
                feature_mean=feature_mean,
                feature_std=feature_std,
            ),
            batch_size=batch_size,
            shuffle=split == "train",
            collate_fn=collate_graph_sequences,
            generator=generator if split == "train" else None,
        )
        for split, rows in split_rows.items()
    }

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TemporalGNN().to(device)
    train_labels = split_rows["train"]["gegenpressing_label"].astype(int)
    class_counts = train_labels.value_counts().reindex([0, 1], fill_value=1)
    class_weights = len(train_labels) / (2.0 * class_counts.to_numpy(dtype=float))
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(class_weights, dtype=torch.float32, device=device)
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )

    best_state = None
    best_validation_loss = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0
    history_records = []

    for epoch in range(1, max_epochs + 1):
        model.train()
        batch_losses = []
        for batch in loaders["train"]:
            batch = _move_batch(batch, device)
            optimizer.zero_grad(set_to_none=True)
            logits, _ = model(batch["x"], batch["edge_index"], batch["node_mask"])
            loss = criterion(logits, batch["y"])
            loss.backward()
            optimizer.step()
            batch_losses.append(float(loss.item()))

        _, _, _, _, validation_loss = _predict(
            model,
            loaders["validation"],
            device,
        )
        train_loss = float(np.mean(batch_losses))
        history_records.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "validation_loss": validation_loss,
        })
        if validation_loss < best_validation_loss - 1e-5:
            best_validation_loss = validation_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= patience:
            break

    if best_state is None:
        raise RuntimeError("Training tidak menghasilkan model state")
    model.load_state_dict(best_state)

    validation_truth, validation_probability, _, _, _ = _predict(
        model,
        loaders["validation"],
        device,
    )
    threshold = choose_validation_threshold(
        validation_truth,
        validation_probability,
    )
    metric_records = []
    prediction_records = []
    for split, loader in loaders.items():
        truths, probabilities, candidate_ids, match_ids, loss = _predict(
            model,
            loader,
            device,
        )
        metrics = classification_metrics(truths, probabilities, threshold)
        metric_records.append({
            "model": "temporal_gnn",
            "split": split,
            "loss": loss,
            **{key: value for key, value in metrics.items() if key != "confusion_matrix"},
            "confusion_matrix": json.dumps(metrics["confusion_matrix"]),
        })
        for candidate_id, match_id, truth, probability in zip(
            candidate_ids,
            match_ids,
            truths,
            probabilities,
        ):
            prediction_records.append({
                "model": "temporal_gnn",
                "split": split,
                "candidate_id": candidate_id,
                "match_id": match_id,
                "y_true": int(truth),
                "probability": float(probability),
                "threshold": threshold,
                "y_pred": int(probability >= threshold),
            })

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_table = pd.DataFrame(metric_records)
    predictions = pd.DataFrame(prediction_records)
    history = pd.DataFrame(history_records)
    torch.save({
        "state_dict": model.state_dict(),
        "model_config": {
            "in_channels": 6,
            "graph_hidden_channels": 32,
            "temporal_hidden_channels": 32,
            "dropout": 0.2,
        },
        "threshold": threshold,
        "feature_normalizer": {
            "indices": list(CONTINUOUS_FEATURE_INDICES),
            "mean": feature_mean.tolist(),
            "std": feature_std.tolist(),
            "fit_split": "train",
        },
    }, output_dir / "temporal_gnn.pt")
    metrics_table.to_csv(output_dir / "metrics.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    history.to_csv(output_dir / "training_history.csv", index=False)
    metadata = {
        "final_run": bool(final_run),
        "device": str(device),
        "random_state": random_state,
        "best_epoch": best_epoch,
        "epochs_run": int(len(history)),
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "feature_normalizer": {
            "indices": list(CONTINUOUS_FEATURE_INDICES),
            "mean": feature_mean.tolist(),
            "std": feature_std.tolist(),
            "fit_split": "train",
        },
        "usable_samples": int(len(usable)),
        "split_counts": {
            split: int(len(rows)) for split, rows in split_rows.items()
        },
        "readiness": {key: bool(value) for key, value in readiness.items()},
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metrics_table, predictions, history, readiness
