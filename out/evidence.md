| Material | Kind | Planted problem | Grade | $/item | Net gain @1.7B | Raw gain (top rung) | Placebo | Hackability | Suite overlap | Public overlap | Flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| clone_arith-quick | env | 80% copied from the free public set | F | 0.00 | not trained (screening only) | - | - | 0% | 0% | 90% | copied_from_public, screen_only |
| contaminated-quick | dataset | bad: 25% reworded copies of held-out suite items | D | 0.00 | not trained (screening only) | - | - | - | 46% | 0% | contaminated, screen_only |
| duplicated-quick | dataset | bad: 20 examples repeated 30 times | C | 2,776.04 | +5.3 [+0.1, +10.6] | +5.3 | -6.0 | - | 0% | 0% | duplicated |
| good_cot-quick | dataset | good: correct answers with worked steps | A | 2,915.62 | +9.3 [+3.0, +15.6] | +9.3 | -6.7 | - | 0% | 0% | none |
| good_short-quick | dataset | good: correct answers only (chat 'messages' format) | F | 0.00 | -10.0 [-14.6, -5.4] | -10.0 | -10.7 | - | 0% | 0% | suppresses_reasoning, no_measurable_gain, harmful |
| gsm8k_clone-quick | dataset | redundant: slice of the free GSM8K train set | F | 0.00 | not trained (screening only) | - | - | - | 0% | 100% | copied_from_public, screen_only |
| hintleak_arith-quick | env | prompt carries the answer | D | 0.00 | not trained (screening only) | - | - | 100% | 0% | 0% | gameable_grader, answer_leakage, screen_only |
| mirror_strings-quick | env | none, but a different skill (reversal) | D | 0.00 | +0.0 [+0.0, +0.0] | +0.0 | +0.0 | 0% | 0% | 0% | no_learning_signal, no_measurable_gain |
| noisy_50-quick | dataset | bad: half the answers wrong | D | 0.00 | not trained (screening only) | - | - | - | 0% | 0% | noisy_labels, screen_only |
| northwind_arith-quick | env | none: honest final-answer grader | A | 843.63 | +20.0 [+14.3, +25.7] | +20.0 | -4.0 | 0% | 0% | 23% | none |
| offtopic-quick | dataset | useless: text-editing tasks, no arithmetic | D | 0.00 | -0.7 [-4.5, +3.1] | -0.7 | -7.3 | - | 0% | 0% | off_topic, no_measurable_gain |
| public_arith-quick | env | free baseline | F | 0.00 | not trained (screening only) | - | - | 0% | 0% | 100% | copied_from_public, screen_only |
| quickgrade_arith-quick | env | grader accepts any reply containing the answer | D | 0.00 | not trained (screening only) | - | - | 100% | 0% | 48% | gameable_grader, screen_only |
| shapeonly_arith-quick | env | grader only checks the number of digits | D | 0.00 | not trained (screening only) | - | - | 100% | 0% | 47% | gameable_grader, screen_only |
| wrong_all-quick | dataset | bad: every answer wrong | D | 0.00 | not trained (screening only) | - | - | - | 0% | 0% | noisy_labels, screen_only |

Good-vs-bad decision accuracy of the ranking: 0.662 over 40 pairs (good = good_cot-quick, good_short-quick, mirror_strings-quick, northwind_arith-quick).
