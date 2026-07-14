<p align="center">
  <img src="assets/adoptsignal-banner.svg" alt="AdoptSignal — Know when the market will follow" width="100%">
</p>

<p align="center">
  <a href="https://github.com/UlrikErlingsen/adoption-forecasting/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/UlrikErlingsen/adoption-forecasting/actions/workflows/tests.yml/badge.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-173C3A?logo=python&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-app-D95B40?logo=streamlit&logoColor=white">
  <a href="LICENSE"><img alt="License: AGPL-3.0-or-later" src="https://img.shields.io/badge/License-AGPL--3.0--or--later-36534E"></a>
</p>

<p align="center"><strong>Open new-product adoption forecasting for marketers — the Bass diffusion model with published analogies, honest warnings, and local-first data.</strong></p>

**AdoptSignal** forecasts how a new product spreads: when adoption takes off, when sales peak, and where they saturate. Before launch, borrow the innovation (p) and imitation (q) parameters from published category analogies and stress-test the word-of-mouth assumption. After launch, fit the model to your real adoption history and let the data update the story. No account or statistics software is required.

## Read this first

> **Treat every diffusion forecast as a structured guess, not a prediction.** The market potential is a judgment, the parameters come from analogies or noisy history, and the model ignores price, competition, and marketing. Its value is disciplining the growth conversation — quantifying the assumptions so they can be argued about.

## Why AdoptSignal

- **Made for marketers:** plain-language pages, a published analog library with citations, fictional demos, and portable exports.
- **Two honest modes:** plan-by-analogy before launch; estimate-from-history after. The app is explicit about which is which.
- **Pre-peak warnings:** fitting a diffusion curve before the sales peak identifies the market potential poorly — AdoptSignal says so instead of printing confident nonsense.
- **Local-first:** no account, telemetry, external AI calls, or built-in data storage — and this tool needs no person-level data at all.
- **Explainable and reproducible:** one classic model (Bass 1969) you can verify in a spreadsheet, with formulas and citations in the docs and a manifest in every export.

## Get the app

You need Python 3.10 or newer. Download this project from GitHub and unzip it, or clone it:

```bash
git clone https://github.com/UlrikErlingsen/adoption-forecasting.git
cd adoption-forecasting
```

**Mac:** double-click `run_app.command`. The browser opens automatically after the local server is ready.

**Windows:** double-click `run_app.bat`.

The first start creates a private `.venv` folder and installs the required packages, which can take a few minutes. Later starts reuse it without requiring a network connection.

Or use a terminal:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

With Docker:

```bash
docker build -t adoptsignal .
docker run --rm -p 8501:8501 adoptsignal
```

Then open `http://localhost:8501`.

## Try it in two minutes

1. On **1 · Market & analogs**, set a market potential, pick one or two analog categories, and save the plan — no file needed.
2. On **2 · Forecast & scenarios**, read the adoption curve, the peak timing, and how the story bends when word of mouth is slower or faster.
3. Click **Demo · smart-lock sales** in the sidebar, and on **3 · Fit your own history** estimate p, q, and m from 16 quarters of fictional sales.
4. Try **Demo · early meal-kit data** to see the honest pre-peak warning.

## Which data works?

Pages 1–2 need no data. For fitting on page 3, AdoptSignal reads `.csv`, `.xlsx`, `.xls`, `.xlsm`, and `.json` with **one row per period**:

| quarter  | units_sold |
| -------- | ---------- |
| Q1 2020  | 2285       |
| Q2 2020  | 3139       |
| Q3 2020  | 4701       |

A period label column and a numeric column of **first-time adopters** (unit sales work for durables bought once). At least 5 periods; the fit becomes trustworthy only after the sales peak. See [the data guide](docs/data_guide.md).

## Methods and accuracy

AdoptSignal implements the **Bass diffusion model**: new adopters per period are n(t) = (p + q·N/m)(m − N). It reports:

- adoption and penetration curves from any p, q, m, with peak timing (ln(q/p)/(p+q)) and peak magnitude;
- a published analog library (per-year parameters) with a cross-category average of roughly p ≈ 0.03, q ≈ 0.42;
- word-of-mouth stress-test scenarios (q × 0.7 and q × 1.3);
- estimation from history by nonlinear least squares on the cumulative curve (Srinivasan & Mason 1986), started and backstopped by Bass's original regression, with fit R² and explicit pre-peak warnings;
- repeat purchases, marketing-mix effects, competition, and successive technology generations are documented as outside the basic model.

See [methods and references](docs/methods.md). Run the automated tests with:

```bash
python -m pytest
```

## Related tools

AdoptSignal is part of a small family of open, local-first marketing-analytics apps that share one design language but do different statistical jobs:

- **[WorthSignal](https://github.com/UlrikErlingsen/customer-value-analytics)** — customer value: RFM targeting, CLV, retention, and marketing ROI.
- **[SegmentSignal](https://github.com/UlrikErlingsen/customer-segmentation)** — multi-variable B2C customer segmentation with stability checks.
- **[ChoiceSignal](https://github.com/UlrikErlingsen/conjoint-analysis)** — conjoint analysis: which product features customers value, and preference shares.
- **[PositionSignal](https://github.com/UlrikErlingsen/brand-positioning)** — perceptual mapping for brand positioning: where brands sit relative to competitors, from brand-attribute ratings.

Together they cover the launch questions in order: *what* to build (ChoiceSignal), *who* it is for (SegmentSignal), *how the market perceives you* (PositionSignal), *when* the market adopts (AdoptSignal), and *what a customer is worth* once acquired (WorthSignal). A ChoiceSignal preference share times a defensible target population is one disciplined way to set the market potential used here.

## Privacy and responsible use

AdoptSignal works entirely on aggregate period counts — it never needs names, IDs, or person-level records. Local mode keeps files in the running process on your computer; hosted mode makes the operator responsible for access control and retention. Read [PRIVACY.md](PRIVACY.md).

## About this project

The product name is **AdoptSignal**; the repository keeps the clear `adoption-forecasting` name. This app was built with AI assistance and reviewed against the published diffusion literature cited in [docs/methods.md](docs/methods.md). All example histories are synthetic; no licensed third-party materials are included.

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## License

AGPL-3.0-or-later. Commercial use is allowed, while distribution and modified network services carry source-sharing obligations described in the full [LICENSE](LICENSE). This summary is not legal advice; the license text controls.
