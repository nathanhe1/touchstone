| Demo | Run | Grade | $/item | Net gain [90%] | Flags | Wall time | Device |
|---|---|---|---|---|---|---|---|
| good-dataset | 0 | A | 76.35 | +7.3 [+1.7, +12.9] |  | 270.7 s | mps |
| good-dataset | 1 | A | 76.35 | +7.3 [+1.7, +12.9] |  | 269.5 s | mps |
| contaminated-dataset | 0 | D | 0.00 | screening only | contaminated, screen_only | 122.7 s | mps |
| contaminated-dataset | 1 | D | 0.00 | screening only | contaminated, screen_only | 119.5 s | mps |
| noisy-dataset | 0 | D | 0.00 | screening only | noisy_labels, screen_only | 6.4 s | mps |
| noisy-dataset | 1 | D | 0.00 | screening only | noisy_labels, screen_only | 5.4 s | mps |
| gameable-env | 0 | D | 0.00 | screening only | gameable_grader, screen_only | 22.0 s | mps |
| gameable-env | 1 | D | 0.00 | screening only | gameable_grader, screen_only | 22.1 s | mps |

Stable grade and flags across reruns: good-dataset: yes, contaminated-dataset: yes, noisy-dataset: yes, gameable-env: yes
