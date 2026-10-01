"""Signal Hub contract: importable UI entry point, Streamlit only under ui/, slug-namespaced state."""

import ast
from pathlib import Path
import re
import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

from adoptsignal import __version__


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "adoptsignal"
UI = PACKAGE / "ui"
UI_ONLY_LIBRARIES = {"streamlit", "plotly"}
PAGES = [
    "Welcome",
    "1 · Market & analogs",
    "2 · Forecast & scenarios",
    "3 · Fit your own history",
    "Methods & limits",
]
RENDER_SCRIPT = """
from adoptsignal.ui import render

render()
"""


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_ui_entry_point_matches_the_hub_contract() -> None:
    from adoptsignal.ui import APP_INFO, render

    assert callable(render)
    assert APP_INFO == {"product": "Adopt Signal", "version": __version__, "repo": "adoption-forecasting", "slug": "adopt"}


def test_only_the_ui_package_imports_streamlit_or_plotly() -> None:
    offenders = {
        str(path.relative_to(PACKAGE)): sorted(_imported_roots(path) & UI_ONLY_LIBRARIES)
        for path in PACKAGE.rglob("*.py")
        if UI not in path.parents and _imported_roots(path) & UI_ONLY_LIBRARIES
    }
    assert not offenders, offenders


def test_core_package_imports_without_streamlit_or_plotly() -> None:
    # A fresh interpreter, so modules already imported by other tests cannot hide a stray import.
    code = (
        f"import sys\nsys.path.insert(0, {str(ROOT / 'src')!r})\n"
        "import adoptsignal, adoptsignal.bass, adoptsignal.errors, adoptsignal.examples, adoptsignal.io\n"
        "loaded = sorted(name for name in ('streamlit', 'plotly') if name in sys.modules)\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_render_never_sets_page_config_or_navigation() -> None:
    for path in UI.glob("*.py"):
        if path.name == "signal_theme.py":
            continue
        source = path.read_text(encoding="utf-8")
        for call in ("st.set_page_config(", "st.navigation(", "st.Page("):
            assert call not in source, (path.name, call)


def test_render_runs_from_a_script_without_set_page_config() -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()

    assert not app.exception, [error.value for error in app.exception]
    assert app.sidebar.radio[0].key == "adopt:page"
    assert "adopt:nav_target" in app.session_state
    assert "nav_target" not in app.session_state
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "NEW-PRODUCT GROWTH, WITHOUT THE BLACK BOX" in body
    assert f"Adopt Signal v{__version__}" in body


def test_rendered_demo_flow_keeps_state_in_the_namespace() -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    next(button for button in app.sidebar.button if button.label == "Demo · smart-lock sales").click().run()
    next(button for button in app.button if button.label == "Fit the Bass model").click().run()

    assert not app.exception, [error.value for error in app.exception]
    assert app.sidebar.radio[0].value == "3 · Fit your own history"
    assert app.session_state["adopt:history_fit"].method == "nls"
    assert "history_fit" not in app.session_state
    assert "tables" not in app.session_state


@pytest.mark.parametrize("page", PAGES)
def test_every_widget_key_is_namespaced(page: str) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    # Load a demo first, so the data-dependent widgets (table picker, column pickers) are drawn too.
    next(button for button in app.sidebar.button if button.label == "Demo · smart-lock sales").click().run()
    if page == "2 · Forecast & scenarios":
        app.sidebar.radio[0].set_value("1 · Market & analogs").run()
        next(button for button in app.button if button.label == "Save this launch plan").click().run()
    app.sidebar.radio[0].set_value(page).run()

    assert not app.exception, [error.value for error in app.exception]
    widgets = [
        *app.radio, *app.selectbox, *app.multiselect, *app.checkbox, *app.button, *app.slider, *app.number_input,
    ]
    assert widgets
    unkeyed = [(type(widget).__name__, widget.label) for widget in widgets if widget.key is None]
    assert not unkeyed, unkeyed
    assert all(widget.key.startswith("adopt:") for widget in widgets)


def test_session_state_and_widget_keys_go_through_the_namespace_helper() -> None:
    source = (UI / "app.py").read_text(encoding="utf-8")
    state_keys = re.findall(r"session_state(?:\[|\.get\(|\.pop\(|\.setdefault\()\s*([^,\])]+)", source)
    widget_keys = re.findall(r"\bkey=([^,)\n]+)", source)
    assert state_keys and widget_keys
    assert all(key.startswith("k(") for key in state_keys), state_keys
    assert all(key.startswith("k(") for key in widget_keys), widget_keys
    assert 'NS = "adopt"' in source
