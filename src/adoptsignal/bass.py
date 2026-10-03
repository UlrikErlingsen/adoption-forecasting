"""Bass diffusion model: forecasting, published analogs, and fitting to adoption history."""

from __future__ import annotations

from dataclasses import dataclass, field
import warnings as warnings_module

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from . import limits
from .errors import DataProblem

MINIMUM_FIT_PERIODS = 5
# Large files: rows are reduced to one row per period before the (compute-bound) fit.
COUNT_ROWS = "(count rows: one row per adopter)"
DATE_GROUPINGS = {"week": "W", "month": "M", "quarter": "Q", "year": "Y"}

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
    standard_errors: dict[str, float] | None = None
    parameter_correlations: dict[str, float] | None = None
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
    if periods < 1:
        raise DataProblem("Choose one or more forecast periods.")
    cumulative = 0.0
    rows = []
    for step in range(int(periods)):
        adopters = (p + q * cumulative / m) * (m - cumulative)
        # With a large p+q the discrete step can overshoot the market
        # potential; cap it so cumulative adoption never exceeds m.
        adopters = min(max(adopters, 0.0), m - cumulative)
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


def _parse_dates(values: pd.Series) -> pd.Series:
    """Dates from a period column: one inferred format for the whole column (fast), mixed formats only for leftovers.

    Numbers are never read as dates (pandas would take 1, 2, 3 as nanoseconds after 1970).
    """
    if pd.api.types.is_datetime64_any_dtype(values):
        return values
    if pd.api.types.is_numeric_dtype(values):
        return pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    with warnings_module.catch_warnings():
        warnings_module.simplefilter("ignore", UserWarning)
        dates = pd.to_datetime(values, errors="coerce")
        leftovers = dates.isna() & values.notna()
        if leftovers.any() and leftovers.sum() < len(values):
            dates = dates.copy()
            dates[leftovers] = pd.to_datetime(values[leftovers], errors="coerce", format="mixed")
        elif leftovers.all():
            dates = pd.to_datetime(values, errors="coerce", format="mixed")
    return dates


def prepare_adoption_series(
    frame: pd.DataFrame,
    period_column: str,
    adopters_column: str,
    *,
    sum_rows_per_period: bool = False,
    group_dates_by: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Validate and order an adoption history; returns the series and honest warnings.

    Large files (millions of rows: one row per store, region, channel, day or adopter) are reduced to one row per
    period before fitting, vectorized and only when asked: ``sum_rows_per_period`` sums rows that share a period
    label, ``group_dates_by`` ("week", "month", "quarter" or "year") first turns dates into calendar periods, and
    ``adopters_column=COUNT_ROWS`` counts rows instead of reading a count column. What was aggregated is recorded
    in ``series.attrs["aggregation"]`` (for exports) and in a warning. Without these options the behaviour is
    unchanged: repeated period labels are refused.
    """
    warnings: list[str] = []
    count_rows = adopters_column == COUNT_ROWS
    for column in (period_column, *(() if count_rows else (adopters_column,))):
        if column not in frame.columns:
            raise DataProblem(f"The column “{column}” is not in the file.")
    if period_column == adopters_column:
        raise DataProblem("The period and adopters columns must be different.")
    if group_dates_by is not None and group_dates_by not in DATE_GROUPINGS:
        raise DataProblem("Group dates by week, month, quarter or year.")
    input_rows = len(frame)
    period = frame[period_column]
    if group_dates_by is not None:
        dates = _parse_dates(period)
        unparsed = int(dates.isna().sum())
        if unparsed == len(dates):
            raise DataProblem(
                f"The period column “{period_column}” does not contain dates, so it cannot be grouped by "
                f"{group_dates_by}. Choose 'as in the file' or a date column."
            )
        if unparsed:
            warnings.append(f"{unparsed:,} rows whose period is not a date were dropped before grouping.")
        period = dates.dt.to_period(DATE_GROUPINGS[group_dates_by])
    adopters = pd.Series(1, index=frame.index, dtype="int64") if count_rows else frame[adopters_column]
    series = pd.DataFrame({"period": period, "new_adopters": adopters})
    if group_dates_by is not None:
        series = series[series["period"].notna()]
    aggregate = sum_rows_per_period or count_rows or group_dates_by is not None
    if not aggregate and series["period"].astype(str).str.strip().duplicated().any():
        raise DataProblem(
            "Some period labels appear more than once. Each period must be one row; aggregate duplicates first, "
            "or tick “Sum rows that share a period” if the rows are stores, regions, channels or transactions."
        )
    series["new_adopters"] = pd.to_numeric(series["new_adopters"], errors="coerce")
    dropped = int(series["new_adopters"].isna().sum())
    series = series.dropna(subset=["new_adopters"])
    if dropped:
        warnings.append(
            f"{dropped:,} rows without a numeric adoption count were dropped — if these were real periods with "
            "missing data, the model's equal-period assumption is violated."
        )
    if (series["new_adopters"] < 0).any():
        raise DataProblem("Adoption counts cannot be negative. Use first-time adopters (or sales) per period.")
    aggregation = None
    if aggregate:
        if group_dates_by is not None:
            # Calendar periods sort chronologically; empty periods inside the range count as zero adopters.
            totals = series.groupby("period", sort=True)["new_adopters"].sum()
            if len(totals):
                full_range = pd.period_range(totals.index.min(), totals.index.max(), freq=totals.index.freq)
                limits.check_history_periods(len(full_range))
                filled = len(full_range) - len(totals)
                totals = totals.reindex(full_range, fill_value=0)
                if filled:
                    warnings.append(f"{filled:,} {group_dates_by}s without any rows were counted as zero adopters.")
            series = pd.DataFrame({"period": totals.index.astype(str), "new_adopters": totals.to_numpy()})
        else:
            labels = series["period"].astype(str).str.strip()
            totals = series.groupby(labels, sort=False)["new_adopters"].sum()
            series = pd.DataFrame({"period": totals.index.to_numpy(), "new_adopters": totals.to_numpy()})
        how = "counted" if count_rows else "summed"
        unit = f"{group_dates_by}s" if group_dates_by else "periods"
        warnings.append(
            f"{input_rows:,} rows were {how} into {len(series):,} {unit} before fitting (one row per period); "
            "the exports record this."
        )
        aggregation = {
            "input_rows": input_rows,
            "periods_after_aggregation": len(series),
            "adopters": "row count" if count_rows else f"sum of {adopters_column}",
            "date_grouping": group_dates_by or "none",
        }
    if len(series) < MINIMUM_FIT_PERIODS:
        raise DataProblem(f"At least {MINIMUM_FIT_PERIODS} periods with numeric adoption counts are required.")
    if float(series["new_adopters"].sum()) <= 0:
        raise DataProblem("The adoption column contains no positive values.")
    order = pd.to_numeric(series["period"], errors="coerce")
    if order.notna().all():
        series = series.assign(_order=order).sort_values("_order").drop(columns="_order")
        spacing = np.diff(order.sort_values().to_numpy(dtype=float))
        if len(spacing) and not np.allclose(spacing, spacing[0], rtol=1e-6, atol=1e-9):
            warnings.append(
                "The numeric periods are not equally spaced. The Bass model assumes equal periods; "
                "irregular spacing bends the fitted curve."
            )
    series = series.reset_index(drop=True)
    limits.check_history_periods(len(series))
    if aggregation is not None:
        series.attrs["aggregation"] = aggregation
    return series, warnings


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
    covariance = None
    try:
        bounds = ([1e-6, 0.0, total], [0.5, 1.99, total * 100])
        start_clipped = tuple(float(np.clip(value, low, high)) for value, low, high in zip(start, *bounds))
        parameters, covariance = curve_fit(
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

    # "Clearly peaked" needs more than one wobble: at least two post-peak
    # periods whose average sits well below the peak observation.
    peak_index = int(np.argmax(adopters))
    post_peak = adopters[peak_index + 1 :]
    peaked = len(post_peak) >= 2 and float(post_peak.mean()) < 0.9 * float(adopters[peak_index])
    if not peaked:
        warnings.append(
            "The history has not clearly passed its sales peak yet (a single small decline is not clear "
            "evidence). Before the peak, market potential (m) is poorly identified and forecasts can change "
            "dramatically with one more period of data — treat this fit as provisional and refit as new "
            "periods arrive."
        )
    if r_squared < 0.5:
        warnings.append("The model explains less than half of the period-to-period variation; read the fit skeptically.")

    standard_errors = None
    parameter_correlations = None
    if method == "nls" and covariance is not None and np.isfinite(covariance).all():
        diagonal = np.sqrt(np.diag(covariance))
        if np.isfinite(diagonal).all() and (diagonal > 0).all():
            standard_errors = {"p": float(diagonal[0]), "q": float(diagonal[1]), "m": float(diagonal[2])}
            with np.errstate(invalid="ignore"):
                correlation = covariance / np.outer(diagonal, diagonal)
            parameter_correlations = {
                "p_q": float(correlation[0, 1]), "p_m": float(correlation[0, 2]), "q_m": float(correlation[1, 2]),
            }
    if standard_errors is None and method == "nls":
        warnings.append(
            "Parameter uncertainty could not be computed (the fit sits at a bound); read the estimates as "
            "point values only."
        )

    fitted = series.copy()
    fitted["fitted_new_adopters"] = predicted_new
    fitted["cumulative_adopters"] = cumulative_observed
    fitted["fitted_cumulative"] = predicted_cumulative
    return BassFit(
        p=p, q=q, m=m, method=method, r_squared=float(r_squared),
        fitted=fitted, peaked=peaked,
        standard_errors=standard_errors, parameter_correlations=parameter_correlations,
        warnings=warnings,
    )


def analog_suggestion(categories: list[str]) -> tuple[float, float]:
    """Mean p and q across chosen published analogs, clamped to usable forecasting ranges.

    Some published estimates sit at extremes (hybrid corn's p is 0.000, which
    would make the model degenerate), so suggestions are clamped to
    p ∈ [0.001, 0.1] and q ∈ [0.05, 0.9].
    """
    chosen = ANALOG_PARAMETERS[ANALOG_PARAMETERS["category"].isin(categories)]
    if chosen.empty:
        raise DataProblem("Choose at least one analog category.")
    p = float(np.clip(chosen["p"].mean(), 0.001, 0.1))
    q = float(np.clip(chosen["q"].mean(), 0.05, 0.9))
    return p, q


def forecast_beyond(fit: BassFit, periods: int) -> pd.DataFrame:
    """Forecast beyond the fitted history using the same continuous curve NLS fitted.

    Mixing estimation on the continuous curve with a discrete forward recursion
    would make the forecast disagree with the fit, so both use the closed form.
    """
    if periods < 1:
        raise DataProblem("Forecast at least one further period.")
    observed = len(fit.fitted)
    times = np.arange(observed, observed + periods + 1, dtype=float)
    cumulative = _cumulative_bass(times, fit.p, fit.q, fit.m)
    new_adopters = np.diff(cumulative)
    return pd.DataFrame(
        {
            "period_index": np.arange(observed + 1, observed + periods + 1),
            "forecast_new_adopters": np.maximum(new_adopters, 0.0),
            "forecast_cumulative": cumulative[1:],
        }
    )
