"""Regenerate the fictional example datasets. All records are synthetic."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(ROOT / "src"))

from adoptsignal.bass import bass_curve  # noqa: E402


def _noisy_history(p: float, q: float, m: float, periods: int, seed: int, label: str):
    rng = np.random.default_rng(seed)
    clean = bass_curve(p, q, m, periods)
    noisy = clean[["period"]].copy()
    noisy.insert(0, "quarter", [f"Q{(index % 4) + 1} {2020 + index // 4}" for index in range(periods)])
    noise = rng.normal(1.0, 0.06, size=periods)
    noisy[label] = np.maximum(0, np.round(clean["new_adopters"] * noise)).astype(int)
    return noisy.drop(columns="period")


if __name__ == "__main__":
    EXAMPLES.mkdir(exist_ok=True)
    # Smart-lock sales: p=0.02, q=0.45, m=120,000 — 16 quarters, clearly past the peak.
    _noisy_history(0.02, 0.45, 120_000, 16, seed=5, label="units_sold").to_csv(
        EXAMPLES / "demo_smartlock_sales.csv", index=False
    )
    # Meal-kit subscriptions: same market, only 6 quarters — before the peak (shows the honesty warning).
    _noisy_history(0.015, 0.50, 80_000, 6, seed=9, label="new_subscribers").to_csv(
        EXAMPLES / "demo_mealkit_early.csv", index=False
    )
    print("Wrote example files to", EXAMPLES)
