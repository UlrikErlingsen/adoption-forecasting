from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from adoptsignal.bass import (
    ANALOG_PARAMETERS,
    analog_suggestion,
    bass_curve,
    fit_bass,
    forecast_beyond,
    peak_adoptions,
    peak_time,
    prepare_adoption_series,
)
from adoptsignal.errors import DataProblem
from adoptsignal.io import load_data


ROOT = Path(__file__).parents[1]


def test_bass_curve_is_s_shaped_and_bounded():
    curve = bass_curve(p=0.02, q=0.45, m=100_000, periods=40)
    assert len(curve) == 40
    assert curve["cumulative_adopters"].is_monotonic_increasing
    assert curve["cumulative_adopters"].iloc[-1] <= 100_000
    assert curve["penetration_%"].iloc[-1] > 95
    peak_period = int(curve["new_adopters"].idxmax()) + 1
    # The discrete recursion peaks a little later than the continuous formula's
    # t* ≈ 6.6 — a known discretization gap, so only a sensible range is asserted.
    assert 5 <= peak_period <= 12


def test_peak_formulas_match_known_values():
    assert np.isclose(peak_time(0.02, 0.45), np.log(0.45 / 0.02) / 0.47)
    assert np.isclose(peak_adoptions(0.02, 0.45, 100_000), 100_000 * 0.47**2 / (4 * 0.45))
    assert peak_time(0.1, 0.05) == 0.0
    assert np.isclose(peak_adoptions(0.1, 0.05, 1000), 100.0)


def test_parameter_validation_is_friendly():
    with pytest.raises(DataProblem, match="innovation parameter"):
        bass_curve(p=0, q=0.4, m=1000, periods=10)
    with pytest.raises(DataProblem, match="imitation parameter"):
        bass_curve(p=0.02, q=2.5, m=1000, periods=10)
    with pytest.raises(DataProblem, match="Market potential"):
        bass_curve(p=0.02, q=0.4, m=-5, periods=10)
    with pytest.raises(DataProblem, match="forecast periods"):
        bass_curve(p=0.02, q=0.4, m=1000, periods=0)


def test_fit_recovers_known_parameters_from_demo():
    frame = load_data(ROOT / "examples" / "demo_smartlock_sales.csv").tables["adoption"]
    series, warnings = prepare_adoption_series(frame, "quarter", "units_sold")
    assert warnings == []
    fit = fit_bass(series)
    assert fit.method == "nls"
    assert fit.peaked
    assert fit.r_squared > 0.9
    assert np.isclose(fit.q, 0.45, atol=0.10)
    assert np.isclose(fit.m, 120_000, rtol=0.15)
    assert 0.001 < fit.p < 0.06


def test_prepeak_history_is_flagged_as_provisional():
    frame = load_data(ROOT / "examples" / "demo_mealkit_early.csv").tables["adoption"]
    series, _ = prepare_adoption_series(frame, "quarter", "new_subscribers")
    fit = fit_bass(series)
    assert not fit.peaked
    assert any("peak" in warning for warning in fit.warnings)


def test_series_validation_errors():
    frame = pd.DataFrame({"period": [1, 2, 3], "adopters": [10, 20, 30]})
    with pytest.raises(DataProblem, match="At least 5 periods"):
        prepare_adoption_series(frame, "period", "adopters")
    with pytest.raises(DataProblem, match="not in the file"):
        prepare_adoption_series(frame, "missing", "adopters")
    with pytest.raises(DataProblem, match="must be different"):
        prepare_adoption_series(frame, "period", "period")
    negatives = pd.DataFrame({"period": range(6), "adopters": [5, 3, -2, 4, 6, 7]})
    with pytest.raises(DataProblem, match="negative"):
        prepare_adoption_series(negatives, "period", "adopters")


def test_numeric_periods_are_sorted_before_fitting():
    clean = bass_curve(0.02, 0.5, 50_000, 12)
    shuffled = pd.DataFrame(
        {"year": clean["period"].tolist()[::-1], "adopters": clean["new_adopters"].tolist()[::-1]}
    )
    series, _ = prepare_adoption_series(shuffled, "year", "adopters")
    assert series["period"].tolist() == clean["period"].tolist()
    fit = fit_bass(series)
    assert np.isclose(fit.q, 0.5, atol=0.05)


def test_analog_suggestion_averages_published_values():
    p, q = analog_suggestion(["Color TV", "Home PC"])
    assert np.isclose(p, (0.021 + 0.003) / 2)
    assert np.isclose(q, (0.583 + 0.253) / 2)
    clamped_p, clamped_q = analog_suggestion(["Hybrid corn (agriculture)"])
    assert clamped_p >= 0.001
    assert clamped_q <= 0.9
    with pytest.raises(DataProblem, match="analog"):
        analog_suggestion(["Not a category"])
    assert {"category", "p", "q"} <= set(ANALOG_PARAMETERS.columns)


def test_discrete_curve_never_exceeds_market_potential():
    curve = bass_curve(p=0.05, q=1.99, m=10_000, periods=30)
    assert float(curve["cumulative_adopters"].max()) <= 10_000 + 1e-6
    assert float(curve["penetration_%"].max()) <= 100 + 1e-9


def test_single_final_dip_is_not_treated_as_peaked():
    rising = bass_curve(0.02, 0.5, 50_000, 8)["new_adopters"].tolist()
    rising[-1] = rising[-2] * 0.97
    frame = pd.DataFrame({"period": range(1, 9), "adopters": rising})
    series, _ = prepare_adoption_series(frame, "period", "adopters")
    fit = fit_bass(series)
    assert not fit.peaked
    assert any("peak" in warning for warning in fit.warnings)


def test_duplicate_periods_are_rejected_and_gaps_warned():
    duplicated = pd.DataFrame({"period": [1, 2, 2, 3, 4, 5], "adopters": [5, 8, 9, 12, 15, 18]})
    with pytest.raises(DataProblem, match="more than once"):
        prepare_adoption_series(duplicated, "period", "adopters")
    irregular = pd.DataFrame({"period": [1, 2, 3, 7, 8, 9], "adopters": [5, 8, 12, 15, 13, 10]})
    _, warnings = prepare_adoption_series(irregular, "period", "adopters")
    assert any("equally spaced" in warning for warning in warnings)
    gappy = pd.DataFrame({"period": range(1, 8), "adopters": [5, 8, None, 12, 15, 13, 10]})
    _, warnings = prepare_adoption_series(gappy, "period", "adopters")
    assert any("dropped" in warning for warning in warnings)


def test_fit_reports_joint_uncertainty_and_consistent_forecast():
    frame = load_data(ROOT / "examples" / "demo_smartlock_sales.csv").tables["adoption"]
    series, _ = prepare_adoption_series(frame, "quarter", "units_sold")
    fit = fit_bass(series)
    assert fit.standard_errors is not None
    assert set(fit.standard_errors) == {"p", "q", "m"}
    assert all(value > 0 for value in fit.standard_errors.values())
    assert set(fit.parameter_correlations) == {"p_q", "p_m", "q_m"}
    forward = forecast_beyond(fit, 8)
    assert len(forward) == 8
    assert forward["forecast_cumulative"].is_monotonic_increasing
    assert float(forward["forecast_cumulative"].iloc[-1]) <= fit.m
    # The first forecast step continues the fitted curve exactly.
    expected_first = float(fit.m and (forward["forecast_cumulative"].iloc[0] - fit.fitted["fitted_cumulative"].iloc[-1]))
    assert np.isclose(float(forward["forecast_new_adopters"].iloc[0]), expected_first, rtol=1e-9)
