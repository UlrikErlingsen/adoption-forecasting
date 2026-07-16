# Changelog

All notable changes to AdoptSignal are documented here.

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
