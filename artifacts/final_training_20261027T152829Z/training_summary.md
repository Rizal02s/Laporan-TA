# Final Training Summary

Status: FINAL

## Data and split

- Usable labels: 1873
- Train samples: 1355
- Validation samples: 195
- Test samples: 323
- Unique test candidates: 323
- Split unit: match
- Decision threshold source: validation

## Models

- Logistic regression with median imputation, scaling, and balanced classes
- XGBoost with median imputation and balanced sample weights
- Temporal GNN with two GCN layers, frame pooling, and GRU
- Temporal GNN device: cuda
- Temporal GNN best epoch: 5

## Test metrics

| model | samples | threshold | precision | recall | f1 | roc_auc | pr_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | 323 | 0.2917 | 0.8286 | 0.9062 | 0.8657 | 0.7231 | 0.9077 |
| temporal_gnn | 323 | 0.6002 | 0.8901 | 0.9492 | 0.9187 | 0.8764 | 0.9533 |
| xgboost | 323 | 0.3125 | 0.8368 | 0.9414 | 0.8860 | 0.7342 | 0.9061 |

## Test metrics by match

| model | match_id | samples | precision | recall | f1 | roc_auc | pr_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | J03WPY | 323 | 0.8286 | 0.9062 | 0.8657 | 0.7231 | 0.9077 |
| temporal_gnn | J03WPY | 323 | 0.8901 | 0.9492 | 0.9187 | 0.8764 | 0.9533 |
| xgboost | J03WPY | 323 | 0.8368 | 0.9414 | 0.8860 | 0.7342 | 0.9061 |

## Interpretation boundary

Results are evaluated on a match-level holdout. The IDSSE source contains seven matches, so conclusions remain specific to this proof-of-concept dataset and must not be presented as broad professional-football generalization.
