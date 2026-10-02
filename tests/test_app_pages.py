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
def test_every_page_renders_with_the_preloaded_demo(page):
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, [error.value for error in app.exception]
    assert not [info.value for info in app.info]  # no "save a plan first" / "bring a file" dead ends


def test_fresh_run_opens_with_the_fictional_demo_preloaded():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.sidebar.radio[0].value == "Welcome"
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "opens with a fictional demo preloaded" in body
    assert app.session_state["adopt:source_name"] == "demo_smartlock_sales.csv"
    assert app.session_state["adopt:history_fit"].method == "nls"
    assert app.session_state["adopt:history_fit"].r_squared > 0.9
    assert app.session_state["adopt:plan"]["analogs"] == ["Cross-category average"]

    app.sidebar.radio[0].set_value("2 · Forecast & scenarios").run()
    assert not app.exception, [error.value for error in app.exception]
    assert "Market potential" in [metric.label for metric in app.metric]
    app.sidebar.radio[0].set_value("3 · Fit your own history").run()
    assert not app.exception, [error.value for error in app.exception]
    assert "Fit R²" in [metric.label for metric in app.metric]


def test_an_upload_replaces_the_preloaded_demo():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    values = [120, 260, 480, 790, 1100, 1350, 1420, 1310, 1080, 820, 590, 400]
    history = "month,units\n" + "".join(f"M{index},{value}\n" for index, value in enumerate(values, start=1))
    app.sidebar.file_uploader[0].set_value(("my_history.csv", history.encode("utf-8"), "text/csv")).run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.session_state["adopt:source_name"] == "my_history.csv"
    assert "adopt:history_fit" not in app.session_state  # the demo fit does not survive the new data
    assert app.sidebar.radio[0].value == "3 · Fit your own history"
    next(button for button in app.button if button.label == "Fit the Bass model").click().run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.session_state["adopt:history_fit"].fitted["new_adopters"].iloc[0] == 120


def test_clearing_the_session_does_not_preload_the_demo_again():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    next(button for button in app.sidebar.button if button.label == "Clear session data").click().run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.session_state["adopt:tables"] is None
    app.sidebar.radio[0].set_value("3 · Fit your own history").run()
    assert any("fictional demo history" in info.value for info in app.info)
    next(button for button in app.sidebar.button if button.label == "Demo · smart-lock sales").click().run()
    assert app.session_state["adopt:source_name"] == "demo_smartlock_sales.csv"


def test_loading_a_demo_navigates_to_fit_page_and_keeps_the_radio_in_sync():
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    next(button for button in app.sidebar.button if button.label == "Demo · smart-lock sales").click().run()
    assert app.sidebar.radio[0].value == "3 · Fit your own history"
    assert app.session_state["adopt:nav_target"] == "3 · Fit your own history"
    assert not app.exception, [error.value for error in app.exception]


def test_full_fit_flow_reaches_estimates():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    next(button for button in app.sidebar.button if button.label == "Demo · smart-lock sales").click().run()
    next(button for button in app.button if button.label == "Fit the Bass model").click().run()
    assert not app.exception, [error.value for error in app.exception]
    fit = app.session_state["adopt:history_fit"]
    assert fit.method == "nls"
    assert fit.r_squared > 0.9


def test_plan_and_forecast_flow_without_uploading():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    app.sidebar.radio[0].set_value("1 · Market & analogs").run()
    next(button for button in app.button if button.label == "Save this launch plan").click().run()
    assert app.session_state["adopt:plan"]["m"] > 0
    app.sidebar.radio[0].set_value("2 · Forecast & scenarios").run()
    assert not app.exception, [error.value for error in app.exception]


def test_choosing_analogs_moves_the_sliders_and_continue_opens_the_forecast():
    from adoptsignal.bass import ANALOG_PARAMETERS, analog_suggestion

    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    app.sidebar.radio[0].set_value("1 · Market & analogs").run()
    category = next(name for name in ANALOG_PARAMETERS["category"] if name != "Cross-category average")
    expected_p, expected_q = analog_suggestion([category])
    app.multiselect[0].set_value([category]).run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.slider[0].value == pytest.approx(round(expected_p, 3))
    assert app.slider[1].value == pytest.approx(round(expected_q, 2))
    next(button for button in app.button if button.label == "Save this launch plan").click().run()
    next(button for button in app.button if button.label.startswith("Continue to 2")).click().run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.sidebar.radio[0].value == "2 · Forecast & scenarios"
