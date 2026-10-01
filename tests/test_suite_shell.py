from pathlib import Path

from streamlit.testing.v1 import AppTest

from adoptsignal import __version__


ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
UI = ROOT / "src" / "adoptsignal" / "ui"


def test_shared_signal_shell_renders() -> None:
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()

    assert not app.exception, [error.value for error in app.exception]
    body = "\n".join(str(item.value) for item in app.markdown)
    sidebar = "\n".join(str(item.value) for item in app.sidebar.markdown)
    assert "OPEN ADOPTION FORECASTING" in body
    assert "NEW-PRODUCT GROWTH, WITHOUT THE BLACK BOX" in body
    assert "structured guess, not a prediction" in body
    assert f"Adopt Signal v{__version__}" in body
    assert "Structured forecast, not prediction" in body
    assert "Part of the Signal suite" in body
    assert "AGPL-3.0-or-later" in body
    assert "sg-mast" in body  # the shared Signal masthead
    assert "sg-foot" in body  # the shared Signal footer
    assert "Know when the market will follow" in sidebar
    assert "sg-side" in sidebar  # the shared Signal sidebar lockup


def test_app_uses_shared_signal_theme_instead_of_pasted_styles() -> None:
    standalone = (ROOT / "app.py").read_text(encoding="utf-8")
    ui_source = (UI / "app.py").read_text(encoding="utf-8")
    theme = (UI / "signal_theme.py").read_text(encoding="utf-8")
    assert 'st.set_page_config(**sig.page_config("adopt"))' in standalone
    assert "sig.apply(NS)" in ui_source
    assert "st.plotly_chart(" not in ui_source  # charts go through sig.chart (template + theme=None)
    assert ui_source.count("sig.chart(NS,") == 4
    assert "<style>" not in standalone + ui_source
    for old_colour in ("#173c3a", "#d95b40", "#83d2b4", "#f2c66d", "#17322e", "#102c2a", "#73837f"):
        assert old_colour not in (standalone + ui_source).lower()
    assert (UI / "assets" / "marks" / "adoptsignal-mark-64.png").exists()
    assert ":focus-visible" in theme
    assert "@media (prefers-reduced-motion:reduce)" in theme
    assert "friendly_message" in ui_source


def test_readme_matches_suite_information_architecture() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # Signal README template order: readers find the same section in the same place in every repo.
    sections = [
        "## Read this first",
        "## Scope",
        "## Try the demo in three minutes",
        "## Data contract",
        "## Analysis contract",
        "## Methods",
        "## Decision statuses",
        "## Exports",
        "## Run locally",
        "## Privacy",
        "## No install? Give this file to an AI",
        "## Development",
        "## Where this fits in Signal",
        "## References",
        "## Originality and license",
    ]
    positions = [readme.find(f"\n{heading}\n") for heading in sections]
    assert all(position >= 0 for position in positions), dict(zip(sections, positions, strict=True))
    assert positions == sorted(positions)
    assert readme.startswith('<p align="center">\n  <img src="assets/adoptsignal-banner.png"')
    assert "assets/adoptsignal-banner.svg" not in readme
    assert "Signal-Market-728157" in readme  # family badge in the Market 600 colour
    assert "github.com/UlrikErlingsen/adoption-forecasting/actions" in readme  # tests badge
    assert "**Adopt Signal**" in readme
    assert "> When will a new product be adopted?" in readme
    assert '<img src="assets/adoptsignal-mark-64.png"' in readme  # suite footer
    assert "AdoptSignal" not in readme
    assert "Creator Signal" not in readme
    assert "structured guess, not a prediction" in readme
    assert "pre-peak" in readme
    for path in ("assets/adoptsignal-banner.png", "assets/adoptsignal-mark-64.png", "assets/adoptsignal-social.png"):
        assert (ROOT / path).exists()
    assert not (ROOT / "assets" / "adoptsignal-banner.svg").exists()


def test_runtime_scaffolding_is_private_and_health_checked() -> None:
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    launcher = (ROOT / "run_app.command").read_text(encoding="utf-8")

    assert "gatherUsageStats = false" in config
    assert 'base = "light"' in config
    assert 'primaryColor = "#728157"' in config  # Signal Market family, 600 step
    assert "USER adoptsignal" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "--browser.gatherUsageStats=false" in launcher
    assert "ADOPTSIGNAL_PORT" in launcher
    assert "Adopt Signal is ready" in launcher
