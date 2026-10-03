"""Data limits: none locally (the old 200 MB / 1,000,000-row / 400-period limits are gone); demo caps with SIGNAL_PUBLIC=1."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from adoptsignal import limits
from adoptsignal.bass import COUNT_ROWS, bass_curve, fit_bass, prepare_adoption_series
from adoptsignal.errors import DataProblem, friendly_message
from adoptsignal.io import load_data

ROOT = Path(__file__).resolve().parents[1]


def _daily_csv(days: int, stores: int) -> bytes:
    """One row per store and day; daily totals follow a Bass curve."""
    dates = pd.date_range("2020-01-01", periods=days, freq="D")
    curve = bass_curve(0.01, 0.4, 40_000, days)["new_adopters"].to_numpy()
    per_store = np.maximum(np.round(np.repeat(curve / stores, stores)), 0).astype(int)
    frame = pd.DataFrame({
        "date": np.repeat(dates.strftime("%Y-%m-%d"), stores),
        "store": np.tile([f"S{i}" for i in range(stores)], days),
        "new_customers": per_store,
    })
    return frame.to_csv(index=False).encode("utf-8")


def test_local_mode_accepts_input_beyond_the_demo_caps(monkeypatch) -> None:
    monkeypatch.delenv("SIGNAL_PUBLIC", raising=False)
    monkeypatch.setattr(limits, "DEMO_MAX_TABLE_ROWS", 1_000)  # keep the test fast: shrink the demo caps instead
    monkeypatch.setattr(limits, "DEMO_MAX_TOTAL_CELLS", 3_000)
    monkeypatch.setattr(limits, "DEMO_MAX_HISTORY_PERIODS", 400)
    frame = load_data(_daily_csv(days=500, stores=4), name="daily.csv").tables["adoption"]
    assert len(frame) == 2_000 > limits.DEMO_MAX_TABLE_ROWS
    series, warnings = prepare_adoption_series(frame, "date", "new_customers", sum_rows_per_period=True)
    assert len(series) == 500 > limits.DEMO_MAX_HISTORY_PERIODS  # above the old 400-period limit too
    assert series.attrs["aggregation"]["input_rows"] == 2_000
    assert any("2,000 rows were summed into 500 periods" in warning for warning in warnings)
    assert fit_bass(series).m > 0


def test_public_demo_enforces_its_caps(monkeypatch) -> None:
    monkeypatch.setenv("SIGNAL_PUBLIC", "1")
    raw = _daily_csv(days=30, stores=2)
    monkeypatch.setattr(limits, "DEMO_MAX_UPLOAD_MB", 0)
    with pytest.raises(DataProblem, match="Uploads are limited to 0 MB. This is a limit of the public demo"):
        load_data(raw, name="daily.csv")
    monkeypatch.setattr(limits, "DEMO_MAX_UPLOAD_MB", 50)
    monkeypatch.setattr(limits, "DEMO_MAX_TABLE_ROWS", 10)
    with pytest.raises(DataProblem, match="more than 10 rows. This is a limit of the public demo"):
        load_data(raw, name="daily.csv")
    monkeypatch.setattr(limits, "DEMO_MAX_TABLE_ROWS", 1_000_000)
    monkeypatch.setattr(limits, "DEMO_MAX_TOTAL_CELLS", 10)
    with pytest.raises(DataProblem, match="more than 10 cells. This is a limit of the public demo"):
        load_data(raw, name="daily.csv")
    monkeypatch.setattr(limits, "DEMO_MAX_TOTAL_CELLS", 10_000_000)
    monkeypatch.setattr(limits, "DEMO_MAX_HISTORY_PERIODS", 20)
    frame = load_data(raw, name="daily.csv").tables["adoption"]
    with pytest.raises(DataProblem, match="the demo fits up to 20. Group dates"):
        prepare_adoption_series(frame, "date", "new_customers", sum_rows_per_period=True)
    monkeypatch.setattr(limits, "DEMO_MAX_UNCOMPRESSED_EXCEL_MB", 0)
    with pytest.raises(DataProblem, match="expands beyond 0 MB"):
        limits.check_workbook_expansion(1)


def test_date_grouping_and_row_counting_reduce_detailed_files() -> None:
    frame = load_data(_daily_csv(days=730, stores=3), name="daily.csv").tables["adoption"]
    monthly, warnings = prepare_adoption_series(frame, "date", "new_customers", group_dates_by="month")
    assert len(monthly) == 24 and monthly["period"].iloc[0] == "2020-01"
    assert monthly.attrs["aggregation"]["date_grouping"] == "month"
    assert monthly["new_adopters"].sum() == frame["new_customers"].sum()
    counted, _ = prepare_adoption_series(frame, "date", COUNT_ROWS, group_dates_by="quarter")
    assert counted["new_adopters"].sum() == len(frame) and counted.attrs["aggregation"]["adopters"] == "row count"
    with pytest.raises(DataProblem, match="does not contain dates"):
        prepare_adoption_series(frame, "new_customers", "store", group_dates_by="year")
    duplicated = pd.DataFrame({"period": [1, 2, 2, 3, 4, 5], "adopters": [5, 8, 9, 12, 15, 18]})
    with pytest.raises(DataProblem, match="Sum rows that share a period"):
        prepare_adoption_series(duplicated, "period", "adopters")


def test_out_of_memory_is_a_plain_message(monkeypatch) -> None:
    assert "not enough memory" in friendly_message(MemoryError())

    def no_memory(*args, **kwargs):
        raise MemoryError

    monkeypatch.setattr(pd, "read_csv", no_memory)
    with pytest.raises(DataProblem, match="not enough memory on this computer"):
        load_data(b"period,adopters\n1,2\n", name="x.csv")


def test_launchers_and_docker_pass_the_upload_cap() -> None:
    bat = (ROOT / "run_app.bat").read_text(encoding="utf-8")
    assert "set ADOPTSIGNAL_MAX_UPLOAD_MB=10000" in bat
    assert "--server.maxUploadSize=%ADOPTSIGNAL_MAX_UPLOAD_MB%" in bat
    command = (ROOT / "run_app.command").read_text(encoding="utf-8")
    assert 'MAX_UPLOAD_MB="${ADOPTSIGNAL_MAX_UPLOAD_MB:-10000}"' in command
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000" in docker
    assert "--server.maxUploadSize" not in docker
    assert "maxUploadSize = 10000" in (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
