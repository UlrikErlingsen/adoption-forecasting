"""Adopt Signal user interface: the Signal Hub entry point.

The only package under ``adoptsignal`` that imports Streamlit (and Plotly). ``render()`` draws the whole app on the
current page and never calls ``st.set_page_config``; the standalone ``app.py`` or Signal Hub owns the page config.
"""

from adoptsignal import __version__
from adoptsignal.ui import signal_theme
from adoptsignal.ui.app import render

APP_INFO = {"product": "Adopt Signal", "version": __version__, "repo": "adoption-forecasting", "slug": "adopt"}

__all__ = ["APP_INFO", "render", "signal_theme"]
