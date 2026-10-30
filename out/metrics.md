## Red flags (precision / recall over all flags)

| Set (engine) | All flags P / R | Weakest recalls | Exactly right |
|---|---|---|---|
| dev, round 1 | 1.0 / 0.941 | noisy 0.8, public 1.0 | 95% |
| dev, round 2 | 1.0 / 0.941 | noisy 0.8, public 1.0 | 95% |
| test v1 (23), round 1 | 1.0 / 0.842 | noisy 0.333, public 0.5 | 87% |
| test v2 (63), round 1 | 0.972 / 0.761 | noisy 0.182, public 0.6 | 81% |

## Forecast, primary metric: accuracy at the small size -> accuracy at the larger size

| Experiment | Spearman | Decision accuracy | n |
|---|---|---|---|
| RL, tiny GPTs, L -> XL (3 seeds) | 0.168 | 0.555 | 16 |
| Datasets, real models, 135M (standard 135M) -> 360M | 0.476 | 0.75 | 8 |
| Datasets, real models, 135M (quick recipe) -> 360M | 0.582 | 0.724 | 13 |
| Datasets, real models, 135M (lr / 10) -> 360M | 0.68 | 0.724 | 13 |
