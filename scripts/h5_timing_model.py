"""Turn measured runs into the timing model scripts/h5_matrix.py plans with: seconds and peak GB per arm and rung.

    python scripts/h5_timing_model.py out/h5_timing.json out/h5/timing out/h5/timing2 out/h5/ladder ...

Keys: "<arm>|<rung>" for short-reply families (32-token replies) and "<arm>|<rung>|long" for worked-solution families
(256-token or longer replies). The largest measured wall time per key is kept (conservative), and peak memory gets 2 GB
of headroom. `packing` is how many runs of a rung share the card at once (by memory, at most 6), discounted to 60%
efficiency for GPU contention. The 70% throughput factor and the 15% reserve are applied by h5_matrix.py.
"""
import json
import sys
from pathlib import Path

PARAMS = {"q3-0.6B": 0.6e9, "q3-1.7B": 1.7e9, "q3-4B": 4.0e9, "q3-8B": 8.2e9, "q25-0.5B": 0.5e9, "q25-1.5B": 1.5e9,
          "q25-7B": 7.6e9, "135M": 1.35e8, "360M": 3.6e8, "1.7B": 1.7e9}


def main():
    dest, dirs = sys.argv[1], sys.argv[2:]
    sec, mem = {}, {}
    for d in dirs:
        for f in Path(d).glob("*.json"):
            r = json.loads(f.read_text())
            j = r.get("job") or {}
            if "wall_s" not in r or r.get("refused"):
                continue
            arm = "sft" if j["arm"].startswith("sft") else ("rl" if j["arm"] in ("rl", "rltr") else j["arm"])
            long = r.get("recipe", {}).get("max_new", 32) > 64
            k = f"{arm}|{j['size']}" + ("|long" if long else "")
            sec[k] = max(sec.get(k, 0), r["wall_s"])
            if r.get("peak_mem_gb"):
                mem[k] = max(mem.get(k, 0), r["peak_mem_gb"] + 2)
    packing = {}
    for s in PARAMS:
        m = max([v for k, v in mem.items() if k.split("|")[1] == s] or [30])
        packing[s] = max(1.0, min(6, int(30 // m)) * 0.6)
    out = {"seconds": sec, "mem": {**{k.rsplit('|long', 1)[0]: v for k, v in mem.items()}, **mem}, "packing": packing, "params": PARAMS,
           "sources": dirs}
    Path(dest).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
