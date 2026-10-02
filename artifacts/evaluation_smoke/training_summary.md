# Smoke Test Training Summary

Status: SMOKE TEST ONLY - DO NOT REPORT AS FINAL RESULTS

## Data and split

- Usable labels: 26
- Train samples: 20
- Validation samples: 3
- Test samples: 3
- Unique test candidates: 3
- Split unit: match
- Decision threshold source: validation

## Models

- Logistic regression with median imputation, scaling, and balanced classes
- XGBoost with median imputation and balanced sample weights
- Temporal GNN with two GCN layers, frame pooling, and GRU
- Temporal GNN device: cuda
- Temporal GNN best epoch: 15

## Test metrics

| model | samples | threshold | precision | recall | f1 | roc_auc | pr_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | 3 | 0.8541 | 0.6667 | 1.0000 | 0.8000 | 0.5000 | 0.8333 |
| temporal_gnn | 3 | 0.7510 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| xgboost | 3 | 0.8795 | 1.0000 | 0.5000 | 0.6667 | 0.5000 | 0.8333 |

## Test metrics by match

| model | match_id | samples | precision | recall | f1 | roc_auc | pr_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | J03WPY | 3 | 0.6667 | 1.0000 | 0.8000 | 0.5000 | 0.8333 |
| temporal_gnn | J03WPY | 3 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| xgboost | J03WPY | 3 | 1.0000 | 0.5000 | 0.6667 | 0.5000 | 0.8333 |

## Interpretation boundary

Results are evaluated on a match-level holdout. The IDSSE source contains seven matches, so conclusions remain specific to this proof-of-concept dataset and must not be presented as broad professional-football generalization.
