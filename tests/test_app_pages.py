from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


APP = str(Path(__file__).parents[1] / "app.py")
PAGES = [
    "Welcome",
    "1 · Market & analogs",
    "2 · Forecast & scenarios",
    "3 · Fit your own history",
    "Methods & limits",
]


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_data(page):
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [error.value for error in app.exception]


def test_loading_a_demo_navigates_to_fit_page_and_keeps_the_radio_in_sync():
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    next(button for button in app.sidebar.button if button.label == "Demo · smart-lock sales").click().run()
    assert app.sidebar.radio[0].value == "3 · Fit your own history"
    assert app.session_state["nav_target"] == "3 · Fit your own history"
    assert not app.exception, [error.value for error in app.exception]


def test_full_fit_flow_reaches_estimates():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    next(button for button in app.sidebar.button if button.label == "Demo · smart-lock sales").click().run()
    next(button for button in app.button if button.label == "Fit the Bass model").click().run()
    assert not app.exception, [error.value for error in app.exception]
    fit = app.session_state["history_fit"]
    assert fit.method == "nls"
    assert fit.r_squared > 0.9


def test_plan_and_forecast_flow_without_any_data():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    app.sidebar.radio[0].set_value("1 · Market & analogs").run()
    next(button for button in app.button if button.label == "Save this launch plan").click().run()
    assert app.session_state["plan"]["m"] > 0
    app.sidebar.radio[0].set_value("2 · Forecast & scenarios").run()
    assert not app.exception, [error.value for error in app.exception]
