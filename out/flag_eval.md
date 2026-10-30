## dev

| Flag | Positives | Before: precision / recall | After: precision / recall |
|---|---|---|---|
| gameable_grader | 3 | 1.0 / 0.667 | 1.0 / 1.0 |
| answer_leakage | 1 | None / 0.0 | 1.0 / 1.0 |
| contaminated | 1 | None / 0.0 | 1.0 / 1.0 |
| copied_from_public | 3 | 1.0 / 0.667 | 1.0 / 1.0 |
| duplicated | 1 | None / 0.0 | 1.0 / 1.0 |
| noisy_labels | 5 | None / 0.0 | 1.0 / 0.8 |
| off_topic | 3 | None / 0.0 | 1.0 / 1.0 |
| all | 17 | 1.0 / 0.235 | 1.0 / 0.941 |

Items with exactly the right flag set: before 41%, after 95% (n=22).

## test

| Flag | Positives | Before: precision / recall | After: precision / recall |
|---|---|---|---|
| gameable_grader | 6 | 1.0 / 0.333 | 1.0 / 1.0 |
| answer_leakage | 1 | None / 0.0 | 1.0 / 1.0 |
| contaminated | 3 | None / 0.0 | 1.0 / 1.0 |
| copied_from_public | 2 | None / 0.0 | 1.0 / 0.5 |
| duplicated | 2 | None / 0.0 | 1.0 / 1.0 |
| noisy_labels | 3 | None / 0.0 | 1.0 / 0.333 |
| off_topic | 2 | None / 0.0 | 1.0 / 1.0 |
| all | 19 | 1.0 / 0.105 | 1.0 / 0.842 |

Items with exactly the right flag set: before 26%, after 87% (n=23).
