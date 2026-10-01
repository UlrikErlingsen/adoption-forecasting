"""Regenerate the fictional example datasets. All records are synthetic."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(ROOT / "src"))

from adoptsignal.examples import DEMOS, demo_csv_bytes  # noqa: E402


if __name__ == "__main__":
    EXAMPLES.mkdir(exist_ok=True)
    for filename in DEMOS:
        (EXAMPLES / filename).write_bytes(demo_csv_bytes(filename))
    print("Wrote example files to", EXAMPLES)
