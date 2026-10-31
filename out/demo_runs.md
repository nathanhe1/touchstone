| Demo | Run | Grade | $/item | Net gain [90%] | Flags | Wall time | Device |
|---|---|---|---|---|---|---|---|
| good-dataset | 0 | A | 76.35 | +7.3 [+1.7, +12.9] |  | 411.5 s | mps |
| good-dataset | 1 | A | 76.35 | +7.3 [+1.7, +12.9] |  | 388.6 s | mps |
| contaminated-dataset | 0 | D | 0.00 | screening only | contaminated, screen_only | 146.6 s | mps |
| contaminated-dataset | 1 | D | 0.00 | screening only | contaminated, screen_only | 128.9 s | mps |
| noisy-dataset | 0 | D | 0.00 | screening only | noisy_labels, screen_only | 134.8 s | mps |
| noisy-dataset | 1 | D | 0.00 | screening only | noisy_labels, screen_only | 132.4 s | mps |
| gameable-env | 0 | D | 0.00 | screening only | gameable_grader, screen_only | 28.2 s | mps |
| gameable-env | 1 | D | 0.00 | screening only | gameable_grader, screen_only | 29.3 s | mps |

Stable grade and flags across reruns: good-dataset: yes, contaminated-dataset: yes, noisy-dataset: yes, gameable-env: yes
