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

## Forecast, primary metric: accuracy at the small size -> accuracy at the larger size

| Experiment | Spearman | Decision accuracy | n |
|---|---|---|---|
| RL, tiny GPTs, L -> XL (3 seeds) | 0.168 | 0.555 | 16 |
| RL, real models, 135M -> 360M | 0.67 | 0.742 | 12 |
| Datasets, real models, 135M (standard 135M) -> 360M | 0.476 | 0.75 | 8 |
| Datasets, real models, 135M (quick recipe) -> 360M | 0.582 | 0.724 | 13 |
| Datasets, real models, 135M (lr / 10) -> 360M | 0.68 | 0.724 | 13 |

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
