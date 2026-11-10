"""Write out/h5_final.sha256: scorer, soft-score helper, frozen config, and every h5 material and suite file.
h5_score.py final refuses to score if any of these changed.

    python scripts/h5_freeze.py
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / "scripts" / f for f in ("h5_score.py", "h5_soft.py", "h5_config.json")] + sorted((ROOT / "examples" / "h5").rglob("*"))
lines = [hashlib.sha256(f.read_bytes()).hexdigest() + "  " + str(f.relative_to(ROOT)) for f in files if f.is_file()]
combined = hashlib.sha256("\n".join(lines).encode()).hexdigest()
(ROOT / "out" / "h5_final.sha256").write_text(f"# h5 frozen before any final run; combined {combined}\n" + "\n".join(lines) + "\n")
print(len(lines), "files; combined", combined)
