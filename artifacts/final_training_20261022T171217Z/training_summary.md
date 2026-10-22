# Final Training Summary

Status: FINAL

## Data and split

- Usable labels: 264
- Train samples: 184
- Validation samples: 40
- Test samples: 40
- Unique test candidates: 40
- Split unit: match
- Decision threshold source: validation

## Models

- Logistic regression with median imputation, scaling, and balanced classes
- XGBoost with median imputation and balanced sample weights
- Temporal GNN with two GCN layers, frame pooling, and GRU
- Temporal GNN device: cuda
- Temporal GNN best epoch: 21

## Test metrics

| model | samples | threshold | precision | recall | f1 | roc_auc | pr_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | 40 | 0.3126 | 0.8387 | 0.8125 | 0.8254 | 0.5508 | 0.8512 |
| temporal_gnn | 40 | 0.2996 | 0.8108 | 0.9375 | 0.8696 | 0.6758 | 0.8657 |
| xgboost | 40 | 0.2557 | 0.7778 | 0.8750 | 0.8235 | 0.6680 | 0.9062 |

## Test metrics by match

| model | match_id | samples | precision | recall | f1 | roc_auc | pr_auc |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | J03WPY | 40 | 0.8387 | 0.8125 | 0.8254 | 0.5508 | 0.8512 |
| temporal_gnn | J03WPY | 40 | 0.8108 | 0.9375 | 0.8696 | 0.6758 | 0.8657 |
| xgboost | J03WPY | 40 | 0.7778 | 0.8750 | 0.8235 | 0.6680 | 0.9062 |

## Interpretation boundary

Results are evaluated on a match-level holdout. The IDSSE source contains seven matches, so conclusions remain specific to this proof-of-concept dataset and must not be presented as broad professional-football generalization.
