## Red flags (precision / recall over all flags)

| Set (engine) | All flags P / R | Weakest recalls | Exactly right |
|---|---|---|---|
| dev, round 1 | 1.0 / 0.941 | noisy 0.8, public 1.0 | 95% |
| dev, round 2 | 1.0 / 0.941 | noisy 0.8, public 1.0 | 95% |
| dev, round 3 | 1.0 / 1.0 | noisy 1.0, public 1.0 | 100% |
| test v1 (23), round 1 | 1.0 / 0.842 | noisy 0.333, public 0.5 | 87% |
| test v1 (23), round 3 (now dev data) | 1.0 / 1.0 | noisy 1.0, public 1.0 | 100% |
| test v2 (63), round 1 | 0.972 / 0.761 | noisy 0.182, public 0.6 | 81% |
| test v2 (63), round 2 (now dev data) | 0.974 / 0.804 | noisy 0.182, public 1.0 | 84% |
| test v2 (63), round 3 (now dev data) | 0.958 / 1.0 | noisy 1.0, public 1.0 | 97% |
| **test v3 (87), frozen, round 2 engine** | 0.886 / 0.5 | noisy 0.05, public 0.364 | 61% |
| **test v3 (87), frozen, round 3 engine** | 0.95 / 0.919 | noisy 1.0, public 1.0 | 92% |

## Forecast, primary metric: accuracy at the small size -> accuracy at the larger size

| Experiment | Spearman | Decision accuracy | n |
|---|---|---|---|
| RL, tiny GPTs, L -> XL (3 seeds) | 0.168 | 0.555 | 16 |
| RL, real models, 135M -> 360M | 0.67 | 0.742 | 12 |
| Datasets, real models, 135M (standard 135M) -> 360M | 0.476 | 0.75 | 8 |
| Datasets, real models, 135M (quick recipe) -> 360M | 0.582 | 0.724 | 13 |
| Datasets, real models, 135M (lr / 10) -> 360M | 0.68 | 0.724 | 13 |

## Test v4: real public data, frozen, scored once

| n | Precision | Recall | Exactly right | Clean draws with a false flag |
|---|---|---|---|---|
| 70 | 0.512 | 0.688 | 47 of 70 | 13 of 31 |

## h4: fine-tuning, 8 unseen classification families, frozen, scored once. Bar 0.80 on screen-passing pairs

Noise ceiling at 1.7B: 0.766 screen-passing, 0.878 all pairs.

| Candidate | Screen-passing | 90% interval | p | All pairs |
|---|---|---|---|---|
| acc_final 360M -> 1.7B | 0.609 | [0.433, 0.759] | 0.0004 | 0.731 |
| sftlr 360M -> 1.7B | 0.447 | [0.257, 0.625] | 0.149 | 0.576 |
| truncated 1.7B net of placebo -> 1.7B | 0.683 | [0.534, 0.819] | 0.0007 | 0.805 |
| acc_final 135M -> 1.7B | 0.578 | [0.413, 0.732] | 0.0059 | 0.705 |
| acc_final 135M -> 360M | 0.774 | [0.638, 0.88] | 0.0001 | 0.882 |
| sftlr 135M -> 360M | 0.547 | [0.344, 0.746] | 0.0798 | 0.62 |

## Forecast, round 3: 135M -> 360M, accuracy to accuracy, 600 items (METHOD.md, pre-registered)

| Set | Signal | Spearman | Decision, all pairs | Decision, resolvable pairs | Resolvable / all | Ceiling |
|---|---|---|---|---|---|---|
| dev | acc_final | 0.544 | 0.705 | 0.711 | 38 / 78 | None |
| dev | acc_late | 0.516 | 0.705 | 0.684 | 38 / 78 | None |
| dev | acc_all_ckpts | 0.522 | 0.705 | 0.684 | 38 / 78 | None |
| dev | smooth_final | 0.571 | 0.718 | 0.711 | 38 / 78 | None |
| dev | smooth_late | 0.467 | 0.679 | 0.658 | 38 / 78 | None |
| dev | reward_gain | 0.341 | 0.628 | 0.605 | 38 / 78 | None |
| dev | ens_acc_smooth | 0.538 | 0.718 | 0.684 | 38 / 78 | None |
| dev | grad_sim | 0.28 | 0.59 | 0.553 | 38 / 78 | None |
| dev | ens_acc_smooth_grad | 0.549 | 0.705 | 0.711 | 38 / 78 | None |

## All-data-types eval (new, small, not part of test v3)

| Set | Precision | Recall | n |
|---|---|---|---|
| eval half, rules as frozen before the run | 0.727 | 1.0 | 32 |
