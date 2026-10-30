"""The stable, public shape of report.json (documented in docs/API.md).

The pipeline produces a detailed report; ``public_report`` adds the compact
top-level fields the website and API clients rely on and keeps every detail
under ``*_detail`` keys. Field names here are a contract: change them only with
a version bump.
"""
from __future__ import annotations

SCHEMA_VERSION = "1.0"


def headline_where(fd: dict) -> str:
    """Where the headline gain comes from, in words: an uncalibrated forecast is just the gain at the largest
    trained size, so it is reported as a measurement there rather than as a number at the target size."""
    if fd.get("method") == "rank_largest" and fd.get("smooth", {}).get("rung"):
        return f"measured at {fd['smooth']['rung']}"
    return f"{fd.get('headline', {}).get('source', 'forecast')} at {fd.get('target')}"


def basis_text(fd: dict) -> str:
    return f"net gain {headline_where(fd)}"


def summary_text(r: dict) -> str:
    m, h = r["material"], r["heldout"]
    hl = r["forecast_detail"]["headline"]
    kind = "dataset" if r["kind"] == "dataset" else "RL environment"
    blocks = [f["code"].replace("_", " ") for f in r["flags"] if f["severity"] == "block"]
    s = f"{m['name']} ({kind}, {m['n_items']:,} items) earns grade {r['grade']}. "
    if hl["point"] is None:
        s += "Screening found a blocking problem, so quick mode did not train a model. "
    else:
        s += (f"Net gain on the held-out {h['name']} suite ({h['domain']}): {hl['point']:+.1f} points "
              f"(range {hl['lo']:+.1f} to {hl['hi']:+.1f}, {headline_where(r['forecast_detail'])}). ")
    if blocks:
        s += "Not priced because of: " + ", ".join(blocks) + "."
    else:
        s += (f"Fair value ${r['fair_value']['per_item']:,.2f} per item at "
              f"${r['fair_value'].get('dollars_per_point', 0):,.0f} per point (the buyer's assumption).")
    return s


def public_report(r: dict) -> dict:
    """Return r with the compact API fields added (idempotent)."""
    if "overlap_detail" not in r:
        r["overlap_detail"] = r.pop("overlap")
    if "forecast_detail" not in r:
        r["forecast_detail"] = r.pop("forecast")
    od, fd = r["overlap_detail"], r["forecast_detail"]
    r["schema_version"] = SCHEMA_VERSION
    r["fair_value_per_item"] = r["fair_value"]["per_item"]
    r["overlap"] = {"suite": round(max(od["heldout"].get("suite_share", 0.0), od["heldout"]["rate"]), 4),
                    "public": round(od["public"]["rate"], 4),
                    "duplicates": round(od["duplicates"]["dup_rate"], 4)}
    r["probes"] = dict(r.get("grader_audit", {}).get("per_exploit", {}))
    gains = {}
    for size, g in r["rungs"].items():
        n = g["net"]["acc"] if "net" in g else g["material"]["acc_gain"]
        gains[size] = {"net": n["gain"], "lo": n["lo"], "hi": n["hi"],
                       "raw": g["material"]["acc_gain"]["gain"],
                       "placebo": g.get("placebo", {}).get("acc_gain", {}).get("gain")}
    r["gains_by_size"] = gains
    hl = fd["headline"]
    r["forecast"] = {"value": hl["point"], "lo": hl["lo"], "hi": hl["hi"], "target": fd["target"],
                     "method": "measured" if hl.get("source") == "measured" else fd["method"],
                     "source": hl.get("source", "forecast"),
                     "smooth_value": (fd.get("smooth") or {}).get("point"),
                     "smooth_lo": (fd.get("smooth") or {}).get("lo"), "smooth_hi": (fd.get("smooth") or {}).get("hi")}
    r["summary"] = summary_text(r)
    return r
