# Changelog

All notable changes to Adopt Signal (published as AdoptSignal before 1.2.0) are documented here.

## 1.3.0 - 2026-10-03

### Larger datasets

- **Larger datasets: no built-in data limits when run locally** (was 200 MB per file, 50 MB for JSON, 1,000,000 rows, 10,000,000 cells, 400 MB of expanded workbook, 400 periods of history and 400 forecast periods). File size, rows, cells and periods are limited only by memory; running out of memory (including Arrow allocation failures) is reported as a plain message. A public demo (`SIGNAL_PUBLIC=1`) applies caps — 50 MB, 1,000,000 rows, 10,000,000 cells, 400 MB expanded workbook, 400 periods of history — all in the new `adoptsignal.limits` module, and its messages say the downloaded app has none. The in-code `ADOPTSIGNAL_MAX_UPLOAD_MB` file limit and the `MAX_*` constants in `adoptsignal.io` and `adoptsignal.bass` are gone.
- CSV files are read by pandas' C parser with a sniffed delimiter instead of the Python engine, and tables are no longer copied after reading. Measured on this machine: 5,000,000 rows (115 MB) load in 1–2 s at 0.55 GB peak memory; a 343 MB JSON file with 5,000,000 records in about 5 s at 2.5 GB.
- Detailed files can now be fitted: `prepare_adoption_series` gains keyword options `sum_rows_per_period`, `group_dates_by` ("week", "month", "quarter", "year"; empty calendar periods count as zero) and `adopters_column=COUNT_ROWS` (one row per adopter). Aggregation is vectorized (5,000,000 daily store rows to 120 months in about 1 s), shown as a warning, kept in `series.attrs["aggregation"]` and exported as `input_aggregation` in the fit JSON. Without the options, repeated period labels are still refused, now with a hint to the new option. The fit page has the matching controls.
- The fit chart draws at most 5,000 periods (every n-th, with a note); the fit, the figures and the export use every period.
- Launchers accept `ADOPTSIGNAL_MAX_UPLOAD_MB` (default 10000; the Windows launcher now honours it too) for `--server.maxUploadSize`; the Dockerfile sets `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000`. Hub mode (`SIGNAL_HUB=1`) is unchanged.
- New `tests/test_large_data.py`: local mode accepts input above the demo row, cell and period caps; `SIGNAL_PUBLIC=1` enforces each cap with its demo message; date grouping, row counting and the duplicate-period hint; out-of-memory as a plain message; launcher, Docker and config caps.

### Suite

- Suite: Rival, Reach, Learn and Blueprint Signal added to the suite table; the synced Signal config raises `maxUploadSize` to 10000.

## 1.2.0 - 2026-10-02

Signal brand refresh and Signal Hub entry point. The model, estimation, warnings, data contract and export contents are unchanged.

### Brand

- Display name written **Adopt Signal** (with a space) in the app, README, docs, launchers and metadata. Package, dist, file and environment-variable names stay `adoptsignal` / `adoption-forecasting` / `ADOPTSIGNAL_*`.
- The app uses the shared `signal_theme` module (Organic Signal design, Market family colour `#728157`, Figtree): sidebar lockup, masthead, hero, step cards, notes, footer, Plotly template (shown with `theme=None`) and the mark as favicon replace the pasted styles. Chart colours follow the Market colorway and the suite's semantic roles.
- New banner, social preview and marks in `assets/`; the old banner SVG is removed. `.streamlit/config.toml` uses the family colours.
- Export metadata names the product "Adopt Signal".
- README follows the Signal template; bug-report and feature-request issue templates added.

### Signal Hub contract

- `adoptsignal.ui` exposes `APP_INFO` and `render()`, so Signal Hub can embed the app; `app.py` is now a thin standalone entry point.
- All session-state and widget keys are namespaced `adopt:` (including the page selector).
- The demo histories come from a new core module, `adoptsignal.examples`, byte-identical to the files in `examples/`, so the demos also work from an installed wheel.
- `streamlit` and `plotly` moved to a `ui` extra (also in `test`); the analysis core installs without them. `requirements.txt` still lists everything.
- Opens with the fictional demo preloaded: a starting launch plan (page-1 defaults) and the fitted smart-lock history, so every page shows results without an upload. The demo buttons restore or switch the demo, an upload replaces it, and "Clear session data" leaves the app empty.
- Embedded Figtree font, no Google Fonts request: the synced `signal_theme` loads Figtree from the new `signal_font` module (base64), and the colorway uses the per-family contrast order.
- New tests: no Streamlit/Plotly import outside `adoptsignal.ui`, `render()` runs from a script without a page config, every widget key is namespaced, the demos match the committed examples, and the shell, README and theme follow the Signal brand.

## 1.1.1 - 2026-07-16

### Security

- Excel exports now neutralize formula-like column headers (not only cell values) and scrub and de-duplicate sheet names.
- The Docker image keeps application code root-owned and read-only, and defusedxml hardens workbook XML parsing.

## 1.1.0 - 2026-07-14

Statistical corrections following an external methods audit:

- The discrete adoption curve is capped so cumulative adoption can never exceed the market potential.
- All peak numbers in the UI are now read off the same discrete curve that is plotted; the continuous formulas are kept for theory only.
- Forecasts beyond a fitted history now extend the same continuous curve the NLS fitted, instead of a separate discrete recursion.
- NLS parameter covariance is kept: approximate standard errors and correlations for p, q, m are reported and exported.
- "Clearly past the peak" now requires at least two post-peak periods well below the peak — a single small decline no longer counts.
- Duplicate period labels are rejected; dropped rows and unequal period spacing produce visible warnings.
- Published analog suggestions are clamped to usable ranges (hybrid corn's p = 0.000 no longer crashes the sliders).
- Removed the suggestion that a conjoint preference share × population directly estimates the market potential.

## 1.0.0 - 2026-07-14

- First stable release. No functional changes since 0.1.0; the version now
  signals that the workflow, methods, exports, and file formats are stable.

## 0.1.0 - 2026-07-14

- First release.
- Bass diffusion forecasting from market potential plus published category analogs.
- Word-of-mouth stress-test scenarios and peak-timing metrics.
- Fitting to real adoption history: nonlinear least squares (Srinivasan–Mason) with Bass-regression start and fallback, honest pre-peak warnings, and forward forecasting.
- Excel, CSV, and JSON exports with a reproducibility manifest.
- Local-first Streamlit UI, fictional demo histories, methods documentation, and automated tests.
