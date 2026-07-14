"""Bass diffusion model: forecasting, published analogs, and fitting to adoption history."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from .errors import DataProblem

MAX_PERIODS = 400
MINIMUM_FIT_PERIODS = 5

# Published Bass-parameter estimates for classic categories, widely reproduced in the
# diffusion literature (Sultan, Farley & Lehmann 1990; Lilien, Rangaswamy & De Bruyn 2017).
# Across hundreds of categories the averages are roughly p = 0.03 and q = 0.42
# (Van den Bulte & Stremersch 2004). Periods are years.
ANALOG_PARAMETERS = pd.DataFrame(
    [
        ("Black & white TV", 0.065, 0.335),
        ("Color TV", 0.021, 0.583),
        ("Room air conditioner", 0.010, 0.454),
        ("Clothes dryer", 0.073, 0.389),
        ("Ultrasound imaging", 0.003, 0.506),
        ("CD player", 0.028, 0.368),
        ("Cellular telephone", 0.005, 0.506),
        ("Steam iron", 0.036, 0.318),
        ("Microwave oven", 0.018, 0.337),
        ("Home PC", 0.003, 0.253),
        ("Hybrid corn (agriculture)", 0.000, 0.798),
        ("Cross-category average", 0.030, 0.420),
    ],
    columns=["category", "p", "q"],
)


@dataclass
class BassFit:
    """Fitted Bass parameters with diagnostics and honest warnings."""

    p: float
    q: float
    m: float
    method: str
    r_squared: float
    fitted: pd.DataFrame
    peaked: bool
    warnings: list[str] = field(default_factory=list)


def _validate_parameters(p: float, q: float, m: float) -> None:
    if not (0 < p < 1):
        raise DataProblem("The innovation parameter p must be between 0 and 1 (typical values: 0.001–0.1).")
    if not (0 <= q < 2):
        raise DataProblem("The imitation parameter q must be between 0 and 2 (typical values: 0.2–0.8).")
    if m <= 0:
        raise DataProblem("Market potential m must be a positive number of eventual adopters.")


def bass_curve(p: float, q: float, m: float, periods: int, start_period: int = 1) -> pd.DataFrame:
    """Discrete Bass adoption path: n(t) = (p + q·N/m)(m − N)."""
    _validate_parameters(p, q, m)
    if not (1 <= periods <= MAX_PERIODS):
        raise DataProblem(f"Choose between 1 and {MAX_PERIODS} forecast periods.")
    cumulative = 0.0
    rows = []
    for step in range(int(periods)):
        adopters = (p + q * cumulative / m) * (m - cumulative)
        adopters = max(adopters, 0.0)
        cumulative += adopters
        rows.append(
            {
                "period": start_period + step,
                "new_adopters": adopters,
                "cumulative_adopters": cumulative,
                "penetration_%": 100 * cumulative / m,
            }
        )
    return pd.DataFrame(rows)


def peak_time(p: float, q: float) -> float:
    """Continuous-time peak of non-cumulative adoption, t* = ln(q/p)/(p+q).

    Only meaningful when q > p; otherwise adoption is highest at launch.
    """
    if q <= p:
        return 0.0
    return float(np.log(q / p) / (p + q))


def peak_adoptions(p: float, q: float, m: float) -> float:
    """Continuous-time peak adoption rate, m(p+q)²/(4q); at launch (m·p) when q ≤ p."""
    if q <= p:
        return float(m * p)
    return float(m * (p + q) ** 2 / (4 * q))


def _cumulative_bass(t: np.ndarray, p: float, q: float, m: float) -> np.ndarray:
    exponent = np.exp(-(p + q) * t)
    return m * (1 - exponent) / (1 + (q / p) * exponent)


def prepare_adoption_series(
    frame: pd.DataFrame, period_column: str, adopters_column: str
) -> pd.DataFrame:
    """Validate and order an adoption history (one row per period, new adopters per period)."""
    for column in (period_column, adopters_column):
        if column not in frame.columns:
            raise DataProblem(f"The column “{column}” is not in the file.")
    if period_column == adopters_column:
        raise DataProblem("The period and adopters columns must be different.")
    series = frame[[period_column, adopters_column]].copy()
    series.columns = ["period", "new_adopters"]
    series["new_adopters"] = pd.to_numeric(series["new_adopters"], errors="coerce")
    series = series.dropna(subset=["new_adopters"])
    if len(series) < MINIMUM_FIT_PERIODS:
        raise DataProblem(f"At least {MINIMUM_FIT_PERIODS} periods with numeric adoption counts are required.")
    if (series["new_adopters"] < 0).any():
        raise DataProblem("Adoption counts cannot be negative. Use first-time adopters (or sales) per period.")
    if float(series["new_adopters"].sum()) <= 0:
        raise DataProblem("The adoption column contains no positive values.")
    order = pd.to_numeric(series["period"], errors="coerce")
    if order.notna().all():
        series = series.assign(_order=order).sort_values("_order").drop(columns="_order")
    series = series.reset_index(drop=True)
    if len(series) > MAX_PERIODS:
        raise DataProblem(f"This release supports up to {MAX_PERIODS} periods of history.")
    return series


def _ols_start(adopters: np.ndarray) -> tuple[float, float, float] | None:
    """Bass (1969) regression n(t) = a + b·N(t−1) + c·N(t−1)² for starting values."""
    lagged = np.concatenate([[0.0], np.cumsum(adopters)[:-1]])
    design = np.column_stack([np.ones_like(lagged), lagged, lagged**2])
    coefficients, *_ = np.linalg.lstsq(design, adopters, rcond=None)
    a, b, c = (float(value) for value in coefficients)
    if c >= 0:
        return None
    discriminant = b**2 - 4 * a * c
    if discriminant < 0:
        return None
    m = (-b - np.sqrt(discriminant)) / (2 * c)
    if m <= 0:
        return None
    p = a / m
    q = b + p
    if p <= 0 or q < 0:
        return None
    return p, q, m


def fit_bass(series: pd.DataFrame) -> BassFit:
    """Estimate p, q, m from adoption history (nonlinear least squares with an OLS start).

    Follows Srinivasan & Mason (1986): fit the continuous cumulative curve by NLS,
    using Bass's original regression only for starting values (and as a fallback).
    """
    adopters = series["new_adopters"].to_numpy(dtype=float)
    total = float(adopters.sum())
    start = _ols_start(adopters)
    if start is None:
        start = (0.03, 0.42, total * 2)

    time_index = np.arange(1, len(adopters) + 1, dtype=float)
    cumulative_observed = np.cumsum(adopters)
    method = "nls"
    warnings: list[str] = []
    try:
        bounds = ([1e-6, 0.0, total], [0.5, 1.99, total * 100])
        start_clipped = tuple(float(np.clip(value, low, high)) for value, low, high in zip(start, *bounds))
        parameters, _ = curve_fit(
            _cumulative_bass, time_index, cumulative_observed, p0=start_clipped, bounds=bounds, maxfev=20000
        )
        p, q, m = (float(value) for value in parameters)
    except Exception:
        if _ols_start(adopters) is None:
            raise DataProblem(
                "The Bass model could not be fitted to this history. It needs several periods of first-time "
                "adoption that rise and (ideally) fall again; strongly irregular series do not identify the model."
            )
        p, q, m = start
        method = "ols"
        warnings.append("Nonlinear fitting failed; the reported values come from Bass's original regression.")

    predicted_cumulative = _cumulative_bass(time_index, p, q, m)
    predicted_new = np.diff(np.concatenate([[0.0], predicted_cumulative]))
    residual = adopters - predicted_new
    variance = float(((adopters - adopters.mean()) ** 2).sum())
    r_squared = 1 - float((residual**2).sum()) / variance if variance > 0 else float("nan")

    peak_index = int(np.argmax(adopters))
    peaked = peak_index < len(adopters) - 1
    if not peaked:
        warnings.append(
            "The history has not clearly passed its sales peak yet. Before the peak, market potential (m) is "
            "poorly identified and forecasts can change dramatically with one more period of data — treat this "
            "fit as provisional and refit as new periods arrive."
        )
    if r_squared < 0.5:
        warnings.append("The model explains less than half of the period-to-period variation; read the fit skeptically.")

    fitted = series.copy()
    fitted["fitted_new_adopters"] = predicted_new
    fitted["cumulative_adopters"] = cumulative_observed
    fitted["fitted_cumulative"] = predicted_cumulative
    return BassFit(
        p=p, q=q, m=m, method=method, r_squared=float(r_squared),
        fitted=fitted, peaked=peaked, warnings=warnings,
    )


def analog_suggestion(categories: list[str]) -> tuple[float, float]:
    """Mean p and q across chosen published analogs."""
    chosen = ANALOG_PARAMETERS[ANALOG_PARAMETERS["category"].isin(categories)]
    if chosen.empty:
        raise DataProblem("Choose at least one analog category.")
    return float(chosen["p"].mean()), float(chosen["q"].mean())
