<p align="center">
  <img src="assets/adoptsignal-banner.png" alt="Adopt Signal: When will a new product be adopted?" width="100%">
</p>

<p align="center">
  <a href="https://github.com/UlrikErlingsen/adoption-forecasting/actions"><img alt="Tests" src="https://github.com/UlrikErlingsen/adoption-forecasting/actions/workflows/tests.yml/badge.svg"></a>
  <a href="https://github.com/UlrikErlingsen/signal-hub"><img alt="Signal · Market" src="https://img.shields.io/badge/Signal-Market-728157?labelColor=2e2b25"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-2e2b25?logo=python&logoColor=f9f4ed">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-app-728157?logo=streamlit&logoColor=f9f4ed">
  <a href="LICENSE"><img alt="License: AGPL-3.0-or-later" src="https://img.shields.io/badge/License-AGPL--3.0--or--later-645c50"></a>
</p>

<p align="center"><strong>Open new-product adoption forecasting for marketers — the Bass diffusion model with published analogies, honest warnings, and local-first data.</strong></p>

**Adopt Signal** forecasts how a new product spreads: when adoption takes off, when sales peak, and where they saturate. Before launch, borrow the innovation (p) and imitation (q) parameters from published category analogies and stress-test the word-of-mouth assumption. After launch, fit the model to your real adoption history and let the data update the story. It is made for marketers: plain-language pages, a published analog library with citations, fictional demos, and portable exports. No account or statistics software is required.

> When will a new product be adopted?

Everything runs locally with open-source Python packages. There is no account, telemetry, external AI call, remote database, or built-in data storage — and this tool needs no person-level data at all.

## Read this first

> **Treat every diffusion forecast as a structured guess, not a prediction.** The market potential is a judgment, the parameters come from analogies or noisy history, and the model ignores price, competition, and marketing. Its value is disciplining the growth conversation — quantifying the assumptions so they can be argued about.

- **Two honest modes:** plan-by-analogy before launch; estimate-from-history after. The app is explicit about which is which.
- **Pre-peak warnings:** fitting a diffusion curve before the sales peak identifies the market potential poorly — Adopt Signal says so instead of printing confident nonsense.
- **Explainable and reproducible:** one classic model (Bass 1969) you can verify in a spreadsheet, with formulas and citations in the docs and a manifest in every export.

## Scope

**Version 1.2 supports:**

- adoption and penetration curves from any p, q, m, with peak timing (ln(q/p)/(p+q)) and peak magnitude;
- a published analog library (per-year parameters) with a cross-category average of roughly p ≈ 0.03, q ≈ 0.42;
- word-of-mouth stress-test scenarios (q × 0.7 and q × 1.3);
- estimation from history by nonlinear least squares on the cumulative curve (Srinivasan & Mason 1986), started and backstopped by Bass's original regression, with fit R², approximate standard errors and explicit pre-peak warnings;
- forecasts beyond a fitted history that extend the same fitted curve;
- Excel, CSV, and JSON exports with a reproducibility manifest.

**It does not:** model repeat purchases, replacements, upgrades or churn, marketing-mix effects (price, advertising, distribution), competition, or successive technology generations; it does not validate a forecast beyond the history it was fitted to, and it does not turn a preference share into a market potential. Where a sibling app covers it, use **[Worth Signal](https://github.com/UlrikErlingsen/customer-value-analytics)** for retention and customer value after adoption, **[Choice Signal](https://github.com/UlrikErlingsen/conjoint-analysis)** for what customers value in a design, **[Alloc Signal](https://github.com/UlrikErlingsen/marketing-mix-allocation)** for marketing response and budget allocation, and **[Gate Signal](https://github.com/UlrikErlingsen/launch-decision-gate)** for the go/hold/rework/kill launch decision.

## Try the demo in three minutes

The app opens with a fictional demo already loaded, so every page shows results before you upload anything: a starting launch plan (m = 100,000 with the published cross-category average analogs) and 16 quarters of fictional smart-lock sales, already fitted.

1. Start the app. On **1 · Market & analogs**, change the market potential or pick one or two analog categories, and save the plan — no file needed.
2. On **2 · Forecast & scenarios**, read the adoption curve, the peak timing, and how the story bends when word of mouth is slower or faster.
3. On **3 · Fit your own history**, read the p, q, and m estimated from the preloaded fictional smart-lock sales. **Demo · smart-lock sales** in the sidebar restores this demo at any time.
4. Click **Demo · early meal-kit data** to see the honest pre-peak warning.
5. Export the forecast as Excel, CSV, or JSON, or the fit as JSON with its audit trail. Upload your own history in the sidebar to replace the demo.

The demo histories are deterministic synthetic data generated by code ([`scripts/generate_examples.py`](scripts/generate_examples.py)). They represent no real product, organisation, course case or empirical finding.

## Data contract

Pages 1–2 need no data. For fitting on page 3, Adopt Signal reads `.csv`, `.xlsx`, `.xls`, `.xlsm`, and `.json` with **one row per period**:

| quarter  | units_sold |
| -------- | ---------- |
| Q1 2020  | 2285       |
| Q2 2020  | 3139       |
| Q3 2020  | 4701       |

A period label column and a numeric column of **first-time adopters** (unit sales work for durables bought once). At least 5 periods; the fit becomes trustworthy only after the sales peak. Duplicate period labels are rejected; rows without a numeric count are dropped with a warning, and unequally spaced numeric periods are flagged. Up to 400 periods per history; files up to 200 MB (JSON 50 MB). See [the data guide](docs/data_guide.md).

## Analysis contract

Before forecasting, page 1 records a **launch plan**: the market potential m, the parameters p and q, and the analog categories they were borrowed from. The plan is the single source for the forecast page, and every export repeats it, so the judgment behind m and the choice of analogs stay visible and arguable. Published analog parameters are per **year**; the app says so wherever the period unit matters.

## Methods

Adopt Signal implements the **Bass diffusion model**: new adopters per period are n(t) = (p + q·N/m)(m − N).

1. **Plan by analogy:** p and q are averaged from the chosen published categories (clamped to usable ranges); m is your judgment.
2. **Forecast:** the discrete recursion draws the curve, capped so cumulative adoption never exceeds m; peak numbers are read off the same plotted curve.
3. **Stress-test:** the same plan with q × 0.7 and q × 1.3.
4. **Fit history:** nonlinear least squares on the continuous cumulative curve, started by Bass's regression and falling back to it with a warning; R², approximate standard errors and parameter correlations are reported.
5. **Forecast beyond the history:** the same fitted continuous curve is extended.

Repeat purchases, marketing-mix effects, competition, and successive technology generations are documented as outside the basic model. See [methods and references](docs/methods.md).

## Decision statuses

Adopt Signal gives no go/no-go verdict. A fitted history carries these flags and warnings, on screen and in the JSON export:

- **Peaked history** (`history_has_peaked: true`): at least two post-peak periods average well below the peak observation.
- **Provisional, pre-peak** (`history_has_peaked: false`): the market potential is poorly identified and the forecast can change dramatically with one more period; refit as periods arrive.
- **Regression fallback** (`estimation: Bass regression (OLS)`): nonlinear fitting failed and Bass's original regression is reported instead.
- **Weak fit**: the model explains less than half of the period-to-period variation.
- **No parameter uncertainty**: the fit sits at a bound, so the estimates are point values only.

## Exports

The forecast exports (Excel pack, CSV, JSON) include:

- a manifest with product, software version, model, m, p, q, the analog categories and the horizon;
- library versions (Python, NumPy, pandas, Streamlit) and the caution that this is a structured scenario, not a prediction;
- the base forecast and the slower and faster word-of-mouth scenarios.

The fit export (JSON) includes the source filename, the estimation method, p, q, m, R², whether the history has peaked, the number of periods, a SHA-256 fingerprint of the fitted periods, and the fitted history. Excel and CSV exports neutralise formula-like cell text and column headers against spreadsheet-formula interpretation, and Excel sheet names are scrubbed and de-duplicated.

## Run locally

You need Python 3.10 or newer and a local copy of this folder. Download this project from GitHub and unzip it, or clone it:

```bash
git clone https://github.com/UlrikErlingsen/adoption-forecasting.git
cd adoption-forecasting
```

**macOS:** double-click `run_app.command`. The browser opens automatically after the local server is ready. **Windows:** double-click `run_app.bat`.

The first launch creates a private `.venv` and installs the open-source dependencies, which can take a few minutes. Later launches reuse it without requiring a network connection. Or use a terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Adopt Signal prefers local port 8501; on macOS the launcher falls back to the next free port. The macOS launcher accepts `ADOPTSIGNAL_PORT`, `ADOPTSIGNAL_MAX_UPLOAD_MB` and `ADOPTSIGNAL_NO_BROWSER`; `ADOPTSIGNAL_MAX_UPLOAD_MB` also sets the app's own file limit, and `ADOPTSIGNAL_DEBUG=1` reveals unexpected technical error details.

### Docker

```bash
docker build -t adoptsignal .
docker run --rm -p 8501:8501 adoptsignal
```

Then open http://127.0.0.1:8501. The container runs as a non-root user and includes a health check.

## Privacy

Adopt Signal works entirely on aggregate period counts — it never needs names, IDs, or person-level records. Local mode keeps files in the running process on your computer; hosted mode makes the operator responsible for access control and retention. See [PRIVACY.md](PRIVACY.md).

## No install? Give this file to an AI

[AI_ANALYST.md](AI_ANALYST.md) is a single copy-paste file that turns a capable AI assistant (Claude, ChatGPT, Gemini, …) into this analysis. Copy the file into a chat, add your data, and the AI follows the same published methods and honesty rules as the app. The app is still the more private option: local mode keeps your data on your computer, while a cloud AI sees whatever you paste.

## Development

```bash
python -m pip install -e ".[test]"
python -m pytest
python -m ruff check .
python -m build
```

The analysis core (`adoptsignal`) installs without Streamlit or Plotly; the app needs the `ui` extra (`python -m pip install -e ".[ui]"`), and `requirements.txt` lists everything for the launchers and Docker. [Signal Hub](https://github.com/UlrikErlingsen/signal-hub) embeds the app through `adoptsignal.ui.render()`.

The suite checks the Bass curve and peak formulas, parameter recovery from the demo, pre-peak and validation warnings, analog suggestions, the deterministic demos, every Streamlit page and flow, the shared Signal shell, and the Signal Hub contract (no Streamlit import outside `ui/`, `render()` without a page config, namespaced keys).

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Where this fits in Signal

Adopt Signal answers *when* the market adopts. Together the apps cover the launch questions in order: *what* to build (Choice Signal), *who* it is for (Segment Signal), *how the market perceives you* (Position Signal), *when* the market adopts (Adopt Signal), *what a customer is worth* once acquired (Worth Signal), *what drives their satisfaction* (Driver Signal), *what their words say* (Text Signal), *whether the scores you rely on measure anything* (Measure Signal), *whether a tested change actually worked* (Experiment Signal), *where the next budget should go* (Alloc Signal), and *whether the launch investment should proceed at all* (Gate Signal).

<!-- signal-suite:start (generated from signal-hub/apps.yaml by scripts/sync_readme_suite.py) -->
| Family | App | Asks |
|---|---|---|
| Brand | [Track Signal](https://github.com/UlrikErlingsen/brand-tracking) | Is the brand moving, or is the tracker just noisy? |
| Brand | [Position Signal](https://github.com/UlrikErlingsen/brand-positioning) | Where do brands sit relative to competitors? |
| Market | [Prospect Signal](https://github.com/UlrikErlingsen/b2b-prospecting) | Which Norwegian companies fit your ideal customer, and which first? |
| Market | [Listen Signal](https://github.com/UlrikErlingsen/media-listening) | Who is talking about the brand in Norwegian media, and in what tone? |
| Market | [Influence Signal](https://github.com/UlrikErlingsen/influencer-campaigns) | Which creators delivered, and was every post labelled properly? |
| Market | [Season Signal](https://github.com/UlrikErlingsen/marketing-calendar) | What does the Norwegian marketing year look like, worked backwards? |
| Market | **Adopt Signal** (this app) | When will a new product be adopted? |
| Market | [Rival Signal](https://github.com/UlrikErlingsen/competitor-analysis) | Which rivals matter, and how could they respond? |
| Market | [Reach Signal](https://github.com/UlrikErlingsen/location-catchment-analysis) | Where could a new location reach, and how would it share demand with existing sites? |
| Customer | [Worth Signal](https://github.com/UlrikErlingsen/customer-value-analytics) | What are customers and relationships worth? |
| Customer | [Segment Signal](https://github.com/UlrikErlingsen/customer-segmentation) | Do customers form stable, useful groups? |
| Customer | [Trace Signal](https://github.com/UlrikErlingsen/journey-path-analysis) | How do logged customer journeys actually unfold? |
| Customer | [Blueprint Signal](https://github.com/UlrikErlingsen/service-blueprinting) | How is the customer experience actually delivered, and where do the handoffs fail? |
| Customer | [Recommend Signal](https://github.com/UlrikErlingsen/recommender-evaluation) | Which recommendation policy should be tested live? |
| Research | [Choice Signal](https://github.com/UlrikErlingsen/conjoint-analysis) | How do product attributes drive choice? |
| Research | [Driver Signal](https://github.com/UlrikErlingsen/survey-driver-analysis) | Which measured experiences move with satisfaction? |
| Research | [Measure Signal](https://github.com/UlrikErlingsen/measurement-validation) | Does a multi-item score have a defensible structure? |
| Research | [Text Signal](https://github.com/UlrikErlingsen/open-text-analysis) | What recurring patterns appear in open-ended responses? |
| Research | [Tag Signal](https://github.com/UlrikErlingsen/pricing-analysis) | What price range is supported, and how does profit move? |
| Research | [Learn Signal](https://github.com/UlrikErlingsen/research-prioritization) | Which uncertainty is worth paying to research before you decide? |
| Decide | [Experiment Signal](https://github.com/UlrikErlingsen/experiment-analysis) | Did the treatment cause a practically meaningful change? |
| Decide | [Gate Signal](https://github.com/UlrikErlingsen/launch-decision-gate) | Does a concept deserve the next investment? |
| Decide | [Shift Signal](https://github.com/UlrikErlingsen/cannibalization-analysis) | Does a launch grow the portfolio, or move existing demand around? |
| Decide | [Alloc Signal](https://github.com/UlrikErlingsen/marketing-mix-allocation) | Where should the next marketing budget go? |

All 24 apps run side by side in [Signal Hub](https://github.com/UlrikErlingsen/signal-hub), each opening with fictional demo data. Every repo carries the [`signal-suite`](https://github.com/topics/signal-suite) topic, and the suite is listed at [ulrikerlingsen.com](https://ulrikerlingsen.com). Freddo CRM is a separate product.
<!-- signal-suite:end -->

## References

- Bass, F. M. (1969). A new product growth for model consumer durables. *Management Science*, 15(5), 215–227.
- Lilien, G. L., Rangaswamy, A., & De Bruyn, A. (2017). *Principles of Marketing Engineering and Analytics* (3rd ed.). DecisionPro.
- Mahajan, V., Muller, E., & Bass, F. M. (1990). New product diffusion models in marketing: A review and directions for research. *Journal of Marketing*, 54(1), 1–26.
- Srinivasan, V., & Mason, C. H. (1986). Nonlinear least squares estimation of new product diffusion models. *Marketing Science*, 5(2), 169–178.
- Sultan, F., Farley, J. U., & Lehmann, D. R. (1990). A meta-analysis of applications of diffusion models. *Journal of Marketing Research*, 27(1), 70–77.
- Van den Bulte, C., & Stremersch, S. (2004). Social contagion and income heterogeneity in new product diffusion: A meta-analytic test. *Marketing Science*, 23(4), 530–544.

Formulas and implementation notes are in [docs/methods.md](docs/methods.md).

## Originality and license

The product name is **Adopt Signal**; the repository keeps the clear `adoption-forecasting` name. This app was built with AI assistance and reviewed against the published diffusion literature cited in [docs/methods.md](docs/methods.md). All example histories are synthetic; no licensed third-party materials are included.

The software and documentation are free under **AGPL-3.0-or-later**. Commercial use is allowed, while distribution and modified network services carry source-sharing obligations described in the full [LICENSE](LICENSE). This summary is not legal advice; the license text controls. The license covers this project's expression, not ownership of the published statistical methods it implements.

Verify material decisions independently; no warranty is provided.

---

<p>
  <img src="assets/adoptsignal-mark-64.png" width="20" height="20" alt="" align="absmiddle">
  <strong>Adopt Signal</strong> is part of <a href="https://github.com/UlrikErlingsen/signal-hub"><strong>Signal</strong></a>, open marketing-evidence tools by <a href="https://ulrikerlingsen.com">Ulrik Erlingsen</a>.
</p>
