| Material | Kind | Planted problem | Grade | $/item | Net gain @1.7B | Raw gain (top rung) | Placebo | Hackability | Suite overlap | Public overlap | Flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| clone_arith-quick | env | 80% copied from the free public set | C | 213.43 | +17.5 [+9.4, +25.6] | +18.3 | +0.8 | 0% | 0% | 90% | mostly_public |
| contaminated-quick | dataset | bad: 25% reworded copies of held-out suite items | D | 0.00 | +4.2 [-3.3, +11.6] | +4.2 | -14.2 | - | 45% | 0% | contaminated |
| good_cot-quick | dataset | good: correct answers with worked steps | B | 781.25 | +2.5 [-5.5, +10.5] | +2.5 | -12.5 | - | 0% | 0% | none |
| good_short-quick | dataset | good: correct answers only (chat 'messages' format) | F | 0.00 | -9.2 [-13.9, -4.4] | -9.2 | -14.2 | - | 0% | 0% | no_measurable_gain, harmful |
| hintleak_arith-quick | env | prompt carries the answer | D | 0.00 | +4.2 [-1.2, +9.5] | +4.2 | +0.0 | 100% | 0% | 0% | gameable_grader, transfer_gap |
| mirror_strings-quick | env | none, but a different skill (reversal) | D | 0.00 | +0.0 [+0.0, +0.0] | +0.0 | +0.0 | 0% | 0% | 0% | no_learning_signal, no_measurable_gain |
| noisy_50-quick | dataset | bad: half the answers wrong | C | 0.00 | +0.8 [-6.2, +7.9] | +0.8 | -13.3 | - | 0% | 0% | no_measurable_gain |
| northwind_arith-quick | env | none: honest final-answer grader | A | 914.08 | +21.7 [+15.0, +28.4] | +21.7 | -3.3 | 0% | 0% | 23% | none |
| offtopic-quick | dataset | useless: text-editing tasks, no arithmetic | D | 0.00 | -5.0 [-10.2, +0.2] | -5.0 | -5.8 | - | 0% | 0% | no_measurable_gain |
| public_arith-quick | env | free baseline | C | 0.00 | +21.7 [+14.4, +28.9] | +21.7 | +0.0 | 0% | 0% | 100% | mostly_public |
| quickgrade_arith-quick | env | grader accepts any reply containing the answer | D | 0.00 | +21.7 [+14.0, +29.4] | +21.7 | -5.0 | 100% | 0% | 48% | gameable_grader |
| shapeonly_arith-quick | env | grader only checks the number of digits | D | 0.00 | -0.8 [-9.4, +7.7] | +7.5 | +8.3 | 100% | 0% | 47% | gameable_grader, no_measurable_gain |
| wrong_all-quick | dataset | bad: every answer wrong | D | 0.00 | -5.8 [-12.2, +0.5] | -5.8 | -12.5 | - | 0% | 0% | no_measurable_gain |
