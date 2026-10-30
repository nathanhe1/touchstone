"""Render an appraisal (report.json) as a readable report.md."""
from __future__ import annotations


def _pm(g: dict) -> str:
    return f"{g['gain']:+.1f} [{g['lo']:+.1f}, {g['hi']:+.1f}]"


def _money(x: float) -> str:
    return f"${x:,.2f}" if x < 100 else f"${x:,.0f}"


def render(r: dict) -> str:
    m, h = r["material"], r["heldout"]
    fcast = r.get("forecast_detail") or r["forecast"]
    kind = "dataset" if r["kind"] == "dataset" else "RL environment"
    net = fcast.get("headline", fcast["net"])
    how = "measured" if net.get("source") == "measured" else "forecast"
    out = []
    w = out.append
    w(f"# Touchstone appraisal: {m['name']}\n")
    w(f"**Grade {r['grade']}** · fair value **{_money(r['fair_value']['per_item'])} per "
      f"{'example' if r['kind'] == 'dataset' else 'task'}** · {how} net gain at {fcast['target']}: "
      + (f"**{net['point']:+.1f} pts** (range {net['lo']:+.1f} to {net['hi']:+.1f}) on the held-out suite\n"
         if net["point"] is not None else "not measured (quick mode stopped after screening)\n"))
    if r["flags"]:
        w("**Flags**\n")
        for f in r["flags"]:
            w(f"- **{f['code']}** ({f['severity']}): {f['text']}")
        w("")
    else:
        w("No flags.\n")

    w("## What was appraised\n")
    w(f"- {kind[0].upper() + kind[1:]}: `{m['path']}`")
    w(f"- SHA-256: `{m['sha256']}`")
    w(f"- Items: {m['n_items']:,} ({m['unique_items']:,} unique)")
    w(f"- Mode: {r['mode']} · runtime {r['runtime_s'] // 60} min {r['runtime_s'] % 60} s")
    w(f"- Models (real open weights, LoRA rank {r['recipe']['lora_r']}): "
      + ", ".join(f"{k} = `{v}`" for k, v in r["models"].items()) + "\n")

    w("## Held-out suite\n")
    w(f"- Suite: **{h['name']}** ({h['source']}), {h['n_items']} items")
    w(f"- Domain: {h['domain']}")
    w(f"- {h['description']}")
    w(f"- Never used for training. {h['n_items_untouched_by_material']} of {h['n_items']} suite items have no match "
      "in the appraised material; gains are also reported on that untouched subset.\n")

    w("## Transfer to the held-out suite\n")
    w("Accuracy points gained after training, with 90% bootstrap intervals over suite items "
      "(averaged over seeds). *Placebo* trains on the same prompts with "
      + ("answers shuffled between examples" if r["kind"] == "dataset" else "rewards shuffled within each batch")
      + "; *net* is material minus placebo, the value of the content itself.\n")
    w("| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |")
    w("|---|---|---|---|---|---|---|---|---|")
    if not r["rungs"]:
        w("No model was trained in this run: quick mode stopped after screening (see flags).\n")
    for size, g in r["rungs"].items():
        mat = g["material"]
        pl = g.get("placebo")
        w(f"| {size} | {g['seeds']} | {g['before']['accuracy']:.1f}% | {mat['after']['accuracy']:.1f}% | "
          f"{_pm(mat['acc_gain'])} | {_pm(pl['acc_gain']) if pl else '-'} | "
          f"{_pm(g['net']['acc']) if 'net' in g else '-'} | {_pm(mat['acc_gain_clean'])} | {_pm(mat['cand_gain'])} |")
    w("\n*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong "
      "ones: a smooth score that moves even when small models are rarely fully right.\n")

    if r["kind"] == "env":
        tc, a = r.get("transfer_check"), r["grader_audit"]
        w("## Grader audit\n")
        w(f"Known-wrong and junk answers fed to `verify()` on {a['n_probed']} sampled tasks "
          f"({'reference answers available' if a['has_reference'] else 'no reference answers: reference-free probes only'}). "
          f"Hackability = most reward any probe earns; flagged at 20%.\n")
        w("| Probe | Reward earned |")
        w("|---|---|")
        for k, v in sorted(a["per_exploit"].items(), key=lambda kv: -kv[1]):
            w(f"| {k} | {100 * v:.0f}% |")
        if a.get("has_reference"):
            w(f"\nThe grader accepts {100 * a['reference_accept_rate']:.0f}% of reference answers. "
              f"The answer appears verbatim in {100 * a['answer_in_prompt']:.0f}% of prompts.")
        w(f"\n**Training reward vs held-out transfer** at {tc['rung']}: environment reward "
          f"{tc['env_reward_gain_pts']:+.1f} pts, held-out accuracy {tc['heldout_gain_pts']:+.1f} pts"
          + (" (transfer gap: flagged)" if tc["transfer_gap"] else "") + ".\n")
        w("| Size | Env reward before | after (material) | after (placebo) |")
        w("|---|---|---|---|")
        for size, g in r["rungs"].items():
            pl = g.get("placebo", {}).get("env_reward_after")
            w(f"| {size} | {100 * g['env_reward_before']:.0f}% | {100 * g['material']['env_reward_after']:.0f}% | "
              f"{'-' if pl is None else f'{100 * pl:.0f}%'} |")
        w("")

    w("## Overlap\n")
    o = r.get("overlap_detail") or r["overlap"]
    w(f"- With the held-out suite: **{100 * o['heldout'].get('suite_share', 0):.1f}%** of suite items appear in the "
      f"material; **{100 * o['heldout']['rate']:.1f}%** of the material matches the suite "
      f"(exact {100 * o['heldout']['exact']:.1f}%, near-duplicate {100 * o['heldout']['near']:.1f}%, "
      f"reworded {100 * o['heldout']['paraphrase']:.1f}%)")
    pub = o["public"]
    w(f"- With free public data ({pub['baseline']}): **{100 * pub['rate']:.1f}%**")
    w(f"- Internal duplicates: {100 * o['duplicates']['dup_rate']:.1f}%")
    for ex in (o["heldout"].get("examples") or [])[:2]:
        w(f"  - suite match ({ex['kind']}): \"{ex['item']}\" ~ \"{ex['matches']}\"")
    for ex in (pub.get("examples") or [])[:2]:
        w(f"  - public match ({ex['kind']}): \"{ex['item']}\" ~ \"{ex['matches']}\"")
    w("")

    w(f"## Forecast at {fcast['target']}\n")
    w(f"Method: **{fcast['method']}**. {fcast['method_note']}\n")
    w("| | Point | Range |")
    w("|---|---|---|")
    for arm in ("material", "placebo", "net"):
        if arm in fcast:
            x = fcast[arm]
            w(f"| {arm} | {x['point']:+.1f} pts | {x['lo']:+.1f} to {x['hi']:+.1f} |")
    if "measured_at_target" in fcast:
        mt = fcast["measured_at_target"]
        w(f"\nMeasured at {fcast['target']} in this run: material {mt['material']:+.1f} pts, net {mt['net']:+.1f} pts.")
    w(f"\nBuyer models larger than {fcast['target']} are not forecast: we have not validated the method beyond the "
      "largest size we can train, and RL/SFT gains often shrink as base models get stronger.\n")

    fv = r["fair_value"]
    w("## Grade and fair value\n")
    w(f"- Grade **{r['grade']}** from net gain {net['point']:+.1f} pts (A >= 5, B >= 2, C >= 0.5, else D; F if "
      "training measurably hurts), capped by the flags above.")
    if fv["blocked_by"]:
        w(f"- Not priced: blocked by {', '.join(fv['blocked_by'])}.")
    else:
        w(f"- Value = {net['point']:.2f} pts x ${fv['dollars_per_point']:,.0f} per point x {fv['novel_share']:.2f} "
          f"(share not already free) = {_money(fv['total'])}, over {m['unique_items']:,} unique items = "
          f"**{_money(fv['per_item'])} per item**.")
    w(f"- $ per point is an assumption (set with --dollars-per-point), not a measurement.\n")

    w("## Limits of this appraisal\n")
    w("- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale "
      "better than absolute gains do.")
    w("- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).")
    w("- The held-out suite measures one domain. Skills outside it are not credited.")
    w("- See METHOD.md for how each number is computed and validated.")
    return "\n".join(out) + "\n"
