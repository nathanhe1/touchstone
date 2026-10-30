| Demo | Run | Grade | $/item | Net gain [90%] | Flags | Wall time | Device |
|---|---|---|---|---|---|---|---|
| good-dataset | 0 | A | 3,817.71 | +7.3 [+1.7, +12.9] |  | 136.3 s | mps |
| good-dataset | 1 | A | 3,817.71 | +7.3 [+1.7, +12.9] |  | 136.4 s | mps |
| contaminated-dataset | 0 | D | 0.00 | screening only | contaminated, screen_only | 5.9 s | mps |
| contaminated-dataset | 1 | D | 0.00 | screening only | contaminated, screen_only | 5.3 s | mps |
| noisy-dataset | 0 | D | 0.00 | screening only | noisy_labels, screen_only | 5.0 s | mps |
| noisy-dataset | 1 | D | 0.00 | screening only | noisy_labels, screen_only | 5.0 s | mps |
| gameable-env | 0 | D | 0.00 | screening only | gameable_grader, screen_only | 22.2 s | mps |
| gameable-env | 1 | D | 0.00 | screening only | gameable_grader, screen_only | 22.9 s | mps |

Stable grade and flags across reruns: good-dataset: yes, contaminated-dataset: yes, noisy-dataset: yes, gameable-env: yes
