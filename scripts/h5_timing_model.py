"""Turn measured runs into the timing model scripts/h5_matrix.py plans with: seconds and peak GB per arm and rung.

    python scripts/h5_timing_model.py out/h5_timing.json out/h5/timing out/h5/timing2 out/h5/ladder ...

Keys: "<arm>|<rung>" for short-reply families (32-token replies) and "<arm>|<rung>|long" for worked-solution families
(256-token replies, 512-token SFT sequences). The largest measured wall time per key is kept (conservative), and peak
memory gets 2 GB of headroom. `packing` is how many runs of a rung share the card at once (by memory, at most 6),
discounted to 60% efficiency for GPU contention.
"""
import json
import sys
from pathlib import Path

from touchstone_params import PARAMS  # noqa: F401  (see below)
