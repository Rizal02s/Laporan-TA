import tempfile
import unittest
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.annotation_audit import annotation_quality_checks, build_annotation_audit
from src.baseline_training import baseline_readiness
from src.model_evaluation import compare_model_prediction_sets, evaluate_predictions
from src.final_reporting import build_training_summary
from src.final_artifact_audit import audit_final_training_artifacts, sha256_file
from src.temporal_gnn_training import (
    GraphSequenceDataset,
    TemporalGNN,
    fit_graph_feature_normalizer,
)


class TrainingPipelineTests(unittest.TestCase):
    def test_incomplete_annotations_fail_final_readiness(self):
        annotations = pd.DataFrame({
            "candidate_id": ["c1", "c2", "c3"],
            "match_id": ["m1", "m1", "m1"],
            "is_gegenpressing": [1, 0, np.nan],
            "annotation_confidence": [3, 2, np.nan],
            "annotation_notes": ["", "", ""],
            "annotator": ["tester", "tester", np.nan],
        })
        rows = []
        for split in ("train", "validation", "test"):
            for label in (0, 1):
                rows.append({
                    "split": split,
                    "gegenpressing_label": label,
                    "eligible_for_detection_training": True,
                })
        dataset = pd.DataFrame(rows)
        readiness = baseline_readiness(
            annotations,
            dataset,
            minimum_per_class_per_split=1,
        )
        self.assertFalse(readiness["all_annotations_completed"])
        self.assertTrue(readiness["both_classes_in_every_split"])

    def test_annotation_quality_requires_uncertain_note(self):
        annotations = pd.DataFrame({
            "candidate_id": ["c1"],
            "match_id": ["m1"],
            "is_gegenpressing": [-1],
            "annotation_confidence": [1],
            "annotation_notes": [""],
            "annotator": ["tester"],
        })
        checks = annotation_quality_checks(annotations)
        self.assertFalse(checks["uncertain_have_notes"])

    def test_annotation_review_queue_is_blinded_from_outcome(self):
        annotations = pd.DataFrame({
            "candidate_id": ["c1", "c2"],
            "match_id": ["m1", "m1"],
            "period_id": [1, 1],
            "loss_timestamp": ["0 days 00:00:01", "0 days 00:00:02"],
            "loss_frame": [25, 50],
            "quick_regain_success": [1, 0],
            "is_gegenpressing": [-1, 1],
            "annotation_confidence": [2, 3],
            "annotation_notes": ["duel udara", ""],
            "annotated_at_utc": ["now", "now"],
            "annotator": ["tester", "tester"],
        })
        model_manifest = pd.DataFrame({
            "candidate_id": ["c1", "c2"],
            "split": ["train", "train"],
        })
        _, review, checks = build_annotation_audit(annotations, model_manifest)
        self.assertTrue(checks.all())
        self.assertEqual(review["candidate_id"].tolist(), ["c1"])
        self.assertNotIn("quick_regain_success", review.columns)

    def test_temporal_gnn_forward_shape(self):
        batch_size = 2
        frames = 3
        nodes = 23
        edges = 92
        x = torch.randn(batch_size, frames, nodes, 6)
        edge_index = torch.randint(
            low=0,
            high=nodes,
            size=(batch_size, frames, 2, edges),
        )
        node_mask = torch.ones(batch_size, frames, nodes, dtype=torch.bool)
        model = TemporalGNN()
        logits, embedding = model(x, edge_index, node_mask)
        self.assertEqual(tuple(logits.shape), (batch_size, 2))
        self.assertEqual(tuple(embedding.shape), (batch_size, 32))

    def test_evaluation_requires_identical_candidates(self):
        predictions = pd.DataFrame([
            {
                "model": "a",
                "split": "test",
                "candidate_id": "c1",
                "match_id": "m1",
                "y_true": 0,
                "probability": 0.2,
                "threshold": 0.5,
                "y_pred": 0,
            },
            {
                "model": "b",
                "split": "test",
                "candidate_id": "c2",
                "match_id": "m1",
                "y_true": 1,
                "probability": 0.8,
                "threshold": 0.5,
                "y_pred": 1,
            },
        ])
        checks = compare_model_prediction_sets(predictions)
        self.assertFalse(checks["identical_candidate_sets"])

    def test_evaluation_detects_inconsistent_records_and_thresholds(self):
        rows = []
        for model, match_id, threshold in (
            ("a", "m1", 0.5),
            ("b", "m2", 0.4),
        ):
            for split, candidate_id, truth, probability in (
                ("train", "c1", 0, 0.2),
                ("validation", "c2", 1, 0.8),
                ("test", "c3", 1, 0.55),
            ):
                rows.append({
                    "model": model,
                    "split": split,
                    "candidate_id": candidate_id,
                    "match_id": match_id,
                    "y_true": truth,
                    "probability": probability,
                    "threshold": threshold if split != "test" else threshold + 0.1,
                    "y_pred": int(probability >= threshold),
                })
        checks = compare_model_prediction_sets(pd.DataFrame(rows))
        self.assertTrue(checks["identical_candidate_sets"])
        self.assertFalse(checks["identical_candidate_records"])
        self.assertFalse(checks["one_threshold_per_model"])
        self.assertFalse(checks["predictions_match_threshold"])

    def test_graph_normalizer_is_fit_on_train_cache_and_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            train_item = {
                "x": torch.tensor([
                    [[1.0, 2.0, 3.0, 0.0, 1.0, 0.0]],
                    [[3.0, 4.0, 7.0, 0.0, 1.0, 0.0]],
                ]),
                "edge_index": torch.zeros((2, 2, 0), dtype=torch.long),
                "node_mask": torch.ones((2, 1), dtype=torch.bool),
            }
            torch.save(train_item, root / "train.pt")
            rows = pd.DataFrame([{
                "candidate_id": "c1",
                "match_id": "m1",
                "cache_file": "train.pt",
                "gegenpressing_label": 1,
            }])
            mean, std = fit_graph_feature_normalizer(rows, root)
            self.assertTrue(torch.allclose(mean, torch.tensor([2.0, 3.0, 5.0])))
            self.assertTrue(torch.allclose(std, torch.tensor([1.0, 1.0, 2.0])))
            normalized = GraphSequenceDataset(rows, root, mean, std)[0]["x"]
            self.assertTrue(torch.allclose(normalized[..., :3].mean((0, 1)), torch.zeros(3)))
            self.assertTrue(torch.equal(normalized[..., 3:], train_item["x"][..., 3:]))

    def test_match_level_metrics_keep_threshold(self):
        predictions = pd.DataFrame([
            {
                "model": "a",
                "split": "test",
                "candidate_id": "c1",
                "match_id": "m1",
                "y_true": 0,
                "probability": 0.2,
                "threshold": 0.5,
                "y_pred": 0,
            },
            {
                "model": "a",
                "split": "test",
                "candidate_id": "c2",
                "match_id": "m1",
                "y_true": 1,
                "probability": 0.8,
                "threshold": 0.5,
                "y_pred": 1,
            },
        ])
        split_metrics, match_metrics = evaluate_predictions(predictions)
        self.assertEqual(float(split_metrics.iloc[0]["f1"]), 1.0)
        self.assertEqual(float(match_metrics.iloc[0]["threshold"]), 0.5)

    def test_smoke_summary_is_marked_non_final(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            gnn = root / "gnn"
            evaluation = root / "evaluation"
            baseline.mkdir()
            gnn.mkdir()
            evaluation.mkdir()
            metadata = {
                "usable_samples": 6,
                "split_counts": {"train": 2, "validation": 2, "test": 2},
            }
            (baseline / "metadata.json").write_text(
                __import__("json").dumps(metadata),
                encoding="utf-8",
            )
            (gnn / "metadata.json").write_text(
                __import__("json").dumps({
                    "device": "cpu",
                    "best_epoch": 1,
                }),
                encoding="utf-8",
            )
            metric_row = {
                "model": "m",
                "split": "test",
                "match_id": "match",
                "samples": 2,
                "threshold": 0.5,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
                "roc_auc": 1.0,
                "pr_auc": 1.0,
            }
            pd.DataFrame([metric_row]).drop(columns="match_id").to_csv(
                evaluation / "split_metrics.csv",
                index=False,
            )
            pd.DataFrame([metric_row]).to_csv(
                evaluation / "match_metrics.csv",
                index=False,
            )
            pd.DataFrame([
                {"split": "test", "candidate_id": "c1"},
                {"split": "test", "candidate_id": "c2"},
            ]).to_csv(evaluation / "combined_predictions.csv", index=False)
            output = root / "summary.md"
            build_training_summary(
                baseline,
                gnn,
                evaluation,
                output,
                final_run=False,
            )
            self.assertIn("SMOKE TEST ONLY", output.read_text(encoding="utf-8"))

    def test_final_artifact_audit_accepts_complete_hashed_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "artifacts" / "final_training_incomplete_test"
            baseline = run / "baseline"
            gnn = run / "temporal_gnn"
            evaluation = run / "evaluation"
            processed = root / "data" / "processed"
            for path in (baseline, gnn, evaluation, processed):
                path.mkdir(parents=True, exist_ok=True)

            (run / "frozen_annotations.csv").write_text(
                "candidate_id,is_gegenpressing\nc1,1\n",
                encoding="utf-8",
            )
            (run / "frozen_model_manifest.csv").write_text("candidate_id\nc1\n")
            (run / "annotation_audit_summary.csv").write_text("queue\n1\n")
            (run / "annotation_review_queue.csv").write_text("candidate_id\n")
            (run / "annotation_audit_checks.json").write_text(
                json.dumps({"complete": True}),
                encoding="utf-8",
            )
            (run / "training_summary.md").write_text(
                "# Final Training Summary\n\nStatus: FINAL\n",
                encoding="utf-8",
            )
            (run / "environment.json").write_text("{}", encoding="utf-8")

            for path in (
                baseline / "logistic_regression.joblib",
                baseline / "xgboost.joblib",
                baseline / "metrics.csv",
                baseline / "predictions.csv",
                gnn / "temporal_gnn.pt",
                gnn / "metrics.csv",
                gnn / "predictions.csv",
                gnn / "training_history.csv",
                evaluation / "combined_predictions.csv",
                evaluation / "split_metrics.csv",
                evaluation / "match_metrics.csv",
                processed / "gegenpressing_baseline_features.csv",
                processed / "graph_cache_manifest.csv",
            ):
                path.write_text("value\n1\n", encoding="utf-8")

            (baseline / "metadata.json").write_text(
                json.dumps({"final_run": True}),
                encoding="utf-8",
            )
            (gnn / "metadata.json").write_text(
                json.dumps({"final_run": True}),
                encoding="utf-8",
            )
            (evaluation / "metadata.json").write_text(
                json.dumps({
                    "final_run": True,
                    "models": ["logistic_regression", "xgboost", "temporal_gnn"],
                    "checks": {"consistent": True},
                }),
                encoding="utf-8",
            )

            hash_paths = [
                run / "frozen_annotations.csv",
                run / "annotation_audit_summary.csv",
                run / "annotation_review_queue.csv",
                processed / "gegenpressing_baseline_features.csv",
                processed / "graph_cache_manifest.csv",
                baseline / "logistic_regression.joblib",
                baseline / "xgboost.joblib",
                gnn / "temporal_gnn.pt",
                evaluation / "split_metrics.csv",
                evaluation / "match_metrics.csv",
            ]
            hashes = {}
            for path in hash_paths:
                try:
                    key = path.relative_to(run).as_posix()
                except ValueError:
                    key = path.relative_to(root).as_posix()
                hashes[key] = sha256_file(path)
            (run / "run_manifest.json").write_text(
                json.dumps({
                    "status": "final_training_complete",
                    "artifact_sha256": hashes,
                }),
                encoding="utf-8",
            )

            checks = audit_final_training_artifacts(run, root)
            self.assertTrue(checks.all(), checks[~checks].index.tolist())


if __name__ == "__main__":
    unittest.main()
