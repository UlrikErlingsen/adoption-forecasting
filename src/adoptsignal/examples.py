"""Fictional demo adoption histories. All records are synthetic.

One generator for the in-app demos and the committed files in ``examples/`` (``scripts/generate_examples.py``
writes them), so the app works the same from a source checkout and from an installed wheel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .bass import bass_curve


def noisy_history(p: float, q: float, m: float, periods: int, seed: int, label: str) -> pd.DataFrame:
    """A Bass curve with deterministic multiplicative noise, labelled by quarter."""
    rng = np.random.default_rng(seed)
    clean = bass_curve(p, q, m, periods)
    noisy = clean[["period"]].copy()
    noisy.insert(0, "quarter", [f"Q{(index % 4) + 1} {2020 + index // 4}" for index in range(periods)])
    noise = rng.normal(1.0, 0.06, size=periods)
    noisy[label] = np.maximum(0, np.round(clean["new_adopters"] * noise)).astype(int)
    return noisy.drop(columns="period")


DEMOS = {
    # Smart-lock sales: p=0.02, q=0.45, m=120,000 — 16 quarters, clearly past the peak.
    "demo_smartlock_sales.csv": {"p": 0.02, "q": 0.45, "m": 120_000, "periods": 16, "seed": 5, "label": "units_sold"},
    # Meal-kit subscriptions: only 6 quarters — before the peak (shows the honesty warning).
    "demo_mealkit_early.csv": {"p": 0.015, "q": 0.50, "m": 80_000, "periods": 6, "seed": 9, "label": "new_subscribers"},
}


def demo_history(filename: str) -> pd.DataFrame:
    """The fictional demo history saved as ``examples/<filename>``."""
    return noisy_history(**DEMOS[filename])


def demo_csv_bytes(filename: str) -> bytes:
    """The demo history as the exact CSV bytes committed in ``examples/`` (LF line endings on every platform)."""
    return demo_history(filename).to_csv(index=False, lineterminator="\n").encode("utf-8")
