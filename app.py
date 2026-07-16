# ruff: noqa: E402

from __future__ import annotations

import os

# pyarrow's bundled mimalloc allocator can segfault on macOS when Streamlit
# serializes tables from a worker thread; the system allocator is stable.
# Must be set before Arrow creates its default memory pool.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

import base64
import hashlib
import inspect
import json
import platform
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from adoptsignal import __version__
from adoptsignal.bass import (
    ANALOG_PARAMETERS,
    analog_suggestion,
    bass_curve,
    fit_bass,
    forecast_beyond,
    prepare_adoption_series,
)
from adoptsignal.errors import DataProblem, friendly_message
from adoptsignal.io import LoadedData, load_data, results_to_excel, results_to_json, safe_for_spreadsheet


MARK_URI = "data:image/svg+xml;base64," + base64.b64encode(
    (ROOT / "assets" / "adoptsignal-mark.svg").read_bytes()
).decode("ascii")

PAGES = [
    "Welcome",
    "1 · Market & analogs",
    "2 · Forecast & scenarios",
    "3 · Fit your own history",
    "Methods & limits",
]

CAUTION = (
    "**Treat every diffusion forecast as a structured guess, not a prediction.** The market potential is a "
    "judgment, the parameters come from analogies or noisy history, and the model ignores price, competition, "
    "and marketing. Its value is disciplining the growth conversation — not ending it."
)

COLORS = {"ink": "#17322e", "coral": "#d95b40", "mint": "#83d2b4", "gold": "#f2c66d", "muted": "#73837f"}

_USES_STRETCH_WIDTH = "width" in inspect.signature(st.button).parameters


def full_width(widget, *args, **kwargs):
    """Use Streamlit's full-width API across both older and newer releases."""
    if _USES_STRETCH_WIDTH:
        kwargs["width"] = "stretch"
    else:
        kwargs["use_container_width"] = True
    return widget(*args, **kwargs)


st.set_page_config(page_title="AdoptSignal | Open adoption forecasting", page_icon="◮", layout="wide")
st.markdown(
    """
    <style>
    :root {
        --as-ink: #17322e; --as-deep: #102c2a; --as-teal: #173c3a;
        --as-coral: #d95b40; --as-mint: #83d2b4; --as-gold: #f2c66d;
        --as-paper: #f8f5ed; --as-line: rgba(23, 50, 46, 0.14);
    }
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 93% 2%, rgba(217,91,64,.14), transparent 27rem),
                    linear-gradient(180deg,#fbf9f3 0%,var(--as-paper) 100%);
    }
    [data-testid="stHeader"] { background: rgba(248,245,237,.78); }
    [data-testid="stSidebar"] { background: linear-gradient(165deg,#173c3a 0%,#102c2a 65%,#0c2422 100%); }
    [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] span { color:#f8f5ed; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color:#b9cbc5; }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { background:rgba(255,255,255,.06); border-color:rgba(217,91,64,.32); }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small span { color:#b9cbc5 !important; }
    [data-testid="stSidebar"] button { border-color:rgba(255,255,255,.23); }
    [data-testid="stSidebar"] [data-testid="stButton"] button { background:rgba(255,255,255,.08); color:#f8f5ed !important; }
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover { background:rgba(217,91,64,.16); border-color:rgba(217,91,64,.48); }
    [data-testid="stSidebar"] [data-testid="stButton"] button p,
    [data-testid="stSidebar"] [data-testid="stButton"] button span { color:#f8f5ed !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button { background:#f8f5ed; color:#17322e !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button * { color:#17322e !important; }
    .block-container { max-width:1240px; padding-top:4.4rem; padding-bottom:4rem; }
    h1,h2,h3 { color:var(--as-ink); letter-spacing:-.025em; }
    a { color:#9b3e2b; }
    [data-testid="stMetric"] { background:rgba(255,255,255,.75); border:1px solid var(--as-line); border-radius:16px; padding:1rem 1.05rem; box-shadow:0 8px 28px rgba(23,50,46,.045); }
    [data-testid="stMetricValue"] { color:var(--as-ink); }
    .stButton > button[kind="primary"] { background:linear-gradient(135deg,#e26748,#c94c34); color:white; border:0; box-shadow:0 8px 20px rgba(217,91,64,.22); font-weight:750; }
    .stButton > button[kind="primary"]:hover { background:linear-gradient(135deg,#c94c34,#b63f2b); color:white; }
    [data-testid="stExpander"],[data-testid="stAlert"],[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
    .as-brand { padding:.25rem 0 1.1rem; }
    .as-lockup { display:flex; align-items:center; gap:.65rem; }
    .as-mark { width:38px; height:38px; }
    .as-name { color:white; font-size:1.28rem; line-height:1; font-weight:850; letter-spacing:-.04em; }
    .as-name span { color:#f2c66d !important; }
    .as-tag { margin:.55rem 0 0 !important; color:#b9cbc5 !important; font-size:.77rem; line-height:1.4; }
    .as-masthead { display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:.72rem 1rem .72rem .78rem; margin-bottom:1.35rem; background:rgba(255,255,255,.65); border:1px solid var(--as-line); border-radius:18px; box-shadow:0 10px 36px rgba(23,50,46,.05); }
    .as-masthead .as-mark { width:48px; height:48px; }
    .as-wordmark { color:var(--as-ink); font-weight:850; letter-spacing:-.045em; font-size:1.55rem; line-height:1; }
    .as-wordmark span { color:var(--as-coral); }
    .as-kicker { margin-top:.32rem; color:#59716c; font-size:.67rem; font-weight:800; letter-spacing:.13em; }
    .as-promise { color:#47645e; font-size:.78rem; font-weight:700; white-space:nowrap; }
    .as-promise span { color:var(--as-coral); padding:0 .3rem; }
    .as-hero { position:relative; overflow:hidden; padding:clamp(1.7rem,4vw,3.4rem); margin-bottom:1.3rem; background:linear-gradient(135deg,#173c3a 0%,#102c2a 75%); border-radius:26px; box-shadow:0 18px 50px rgba(23,50,46,.17); }
    .as-hero:after { content:""; position:absolute; width:310px; height:310px; right:-100px; top:-135px; border-radius:50%; border:58px solid rgba(217,91,64,.16); }
    .as-eyebrow { color:#d95b40; font-size:.72rem; font-weight:850; letter-spacing:.16em; }
    .as-hero h1 { color:white; font-size:clamp(2.25rem,5vw,4.7rem); line-height:.97; margin:.75rem 0 1rem; max-width:900px; }
    .as-hero h1 em { color:#f2c66d; font-style:normal; }
    .as-hero p { color:#d7e3df; font-size:1.06rem; line-height:1.6; max-width:780px; }
    .as-pills { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.15rem; }
    .as-pill { padding:.4rem .72rem; border:1px solid rgba(255,255,255,.16); border-radius:999px; color:#f8f5ed; font-size:.78rem; font-weight:700; background:rgba(255,255,255,.055); }
    .as-step { height:100%; padding:1.2rem 1.2rem 1rem; background:rgba(255,255,255,.66); border:1px solid var(--as-line); border-radius:18px; }
    .as-step b { color:var(--as-coral); font-size:.72rem; letter-spacing:.12em; }
    .as-step h3 { margin:.4rem 0 .5rem; }
    .as-step p { color:#59716c; font-size:.9rem; line-height:1.55; }
    .as-quote { margin:1.4rem auto 0; max-width:760px; padding:1.1rem 1.4rem; background:rgba(255,255,255,.6); border:1px solid var(--as-line); border-radius:16px; color:#47645e; font-size:.95rem; line-height:1.65; font-style:italic; }
    .as-quote b { color:var(--as-ink); font-style:normal; font-size:.8rem; letter-spacing:.06em; }
    .as-footer { margin-top:3.2rem; padding-top:1rem; border-top:1px solid var(--as-line); color:#617670; font-size:.76rem; text-align:center; }
    .as-footer span { color:var(--as-coral); padding:0 .38rem; }
    @media (max-width:760px) { .as-promise{display:none}.as-hero{border-radius:20px} }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_error(exc: Exception) -> None:
    st.error(friendly_message(exc))
    if not isinstance(exc, DataProblem) and os.getenv("ADOPTSIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def set_loaded(loaded: LoadedData) -> None:
    st.session_state["tables"] = loaded.tables
    st.session_state["source_name"] = loaded.source_name
    st.session_state["active_table"] = next(iter(loaded.tables))
    st.session_state.pop("history_fit", None)
    st.session_state.pop("history_warnings", None)


def load_demo(filename: str) -> None:
    set_loaded(load_data(ROOT / "examples" / filename))


def current_frame() -> pd.DataFrame | None:
    tables = st.session_state.get("tables")
    if not tables:
        return None
    name = st.session_state.get("active_table", next(iter(tables)))
    return tables[name]


def masthead() -> None:
    st.markdown(
        f"""
        <div class="as-masthead"><div class="as-lockup"><img class="as-mark" src="{MARK_URI}"/>
        <div><div class="as-wordmark">Adopt<span>Signal</span></div><div class="as-kicker">OPEN ADOPTION FORECASTING</div></div></div>
        <div class="as-promise">Local-first <span>•</span> Explainable <span>•</span> Open source</div></div>
        """,
        unsafe_allow_html=True,
    )


for key, default in (
    ("tables", None), ("source_name", None), ("active_table", None),
    ("upload_epoch", 0), ("_uploader_had_file", False),
    ("nav_target", PAGES[0]), ("nav_epoch", 0),
):
    st.session_state.setdefault(key, default)


def go_to(page_name: str) -> None:
    """Navigate programmatically.

    The sidebar radio is re-created with a fresh key so it adopts ``nav_target``
    even when a rerun interrupted the script before the radio was drawn.
    """
    st.session_state["nav_target"] = page_name
    st.session_state["nav_epoch"] = int(st.session_state["nav_epoch"]) + 1


with st.sidebar:
    st.markdown(
        f"<div class='as-brand'><div class='as-lockup'><img class='as-mark' src='{MARK_URI}'/><div class='as-name'>Adopt<span>Signal</span></div></div><p class='as-tag'>Know when the market will follow.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown("### Forecast without data")
    st.caption("Pages 1–2 need no file: set the market and borrow parameters from published analogies.")
    st.markdown("### Or fit your history")
    uploaded = st.file_uploader(
        "CSV, Excel, or JSON with one row per period",
        type=["csv", "xlsx", "xls", "xlsm", "json"],
        key=f"history_upload_{st.session_state['upload_epoch']}",
    )
    if uploaded is not None:
        upload_identity = (
            str(getattr(uploaded, "file_id", "") or f"widget-{st.session_state['upload_epoch']}"),
            uploaded.name,
            int(getattr(uploaded, "size", 0)),
        )
        st.session_state["_uploader_had_file"] = True
        if st.session_state.get("upload_identity") != upload_identity:
            try:
                raw = uploaded.getvalue()
                set_loaded(load_data(raw, name=uploaded.name))
                st.session_state["upload_identity"] = upload_identity
                st.session_state["_uploader_had_file"] = False
                st.session_state["upload_epoch"] = int(st.session_state.get("upload_epoch", 0)) + 1
                go_to("3 · Fit your own history")
                st.rerun()
            except Exception as exc:
                show_error(exc)
    elif st.session_state.get("_uploader_had_file"):
        st.session_state["_uploader_had_file"] = False
    if full_width(st.button, "Demo · smart-lock sales"):
        load_demo("demo_smartlock_sales.csv")
        go_to("3 · Fit your own history")
        st.rerun()
    if full_width(st.button, "Demo · early meal-kit data"):
        load_demo("demo_mealkit_early.csv")
        go_to("3 · Fit your own history")
        st.rerun()
    with st.expander("What are the demos?"):
        st.caption(
            "**Smart-lock sales:** 16 fictional quarters of unit sales, clearly past the sales peak — a "
            "comfortable fit.\n\n"
            "**Early meal-kit data:** only 6 fictional quarters, before the peak — shows how honest the app is "
            "about pre-peak uncertainty.\n\nEvery record is synthetic."
        )
    if st.session_state.get("tables") and full_width(st.button, "Clear session data"):
        for key in (
            "tables", "source_name", "active_table", "upload_identity", "_uploader_had_file",
            "plan", "history_fit", "history_warnings",
        ):
            st.session_state.pop(key, None)
        st.session_state["upload_epoch"] = int(st.session_state.get("upload_epoch", 0)) + 1
        go_to("Welcome")
        st.rerun()
    if st.session_state.get("tables"):
        table_names = list(st.session_state["tables"])
        selected_table = st.selectbox(
            "Table / sheet",
            table_names,
            index=table_names.index(st.session_state.get("active_table"))
            if st.session_state.get("active_table") in table_names
            else 0,
        )
        if selected_table != st.session_state.get("active_table"):
            st.session_state["active_table"] = selected_table
            st.session_state.pop("history_fit", None)
            st.session_state.pop("history_warnings", None)
        active = st.session_state["tables"][selected_table]
        st.caption(f"{st.session_state.get('source_name')} · {len(active):,} rows × {len(active.columns)} columns")
    st.markdown("### Follow the workflow")
    page = st.radio(
        "Page",
        PAGES,
        index=PAGES.index(st.session_state["nav_target"]),
        key=f"nav_radio_{st.session_state['nav_epoch']}",
        label_visibility="collapsed",
    )
    st.session_state["nav_target"] = page

masthead()


def welcome_page() -> None:
    st.markdown(
        """
        <section class="as-hero"><div class="as-eyebrow">NEW-PRODUCT GROWTH, WITHOUT THE BLACK BOX</div>
        <h1>Forecast when the market <em>will follow.</em></h1>
        <p>The Bass diffusion model turns two forces — independent adoption and word of mouth — into an S-shaped
        forecast of new-product growth. Borrow parameters from published analogies before launch, or fit your own
        sales history, and see when adoption should take off, peak, and saturate.</p>
        <div class="as-pills"><span class="as-pill">No account</span><span class="as-pill">No telemetry</span><span class="as-pill">Published analogies</span><span class="as-pill">Honest pre-peak warnings</span></div></section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(CAUTION)
    st.write("")
    columns = st.columns(3)
    steps = [
        ("STEP 01", "Frame the market", "Set a defensible market potential and borrow innovation and imitation parameters from categories that behaved like yours."),
        ("STEP 02", "Forecast & stress-test", "See the adoption curve, the time to peak, and how the story changes when word of mouth is slower or faster than hoped."),
        ("STEP 03", "Fit your own history", "Once real periods arrive, estimate the parameters from your data and let the model tell you how far the ride has left."),
    ]
    for column, (number, title, body) in zip(columns, steps):
        column.markdown(f"<div class='as-step'><b>{number}</b><h3>{title}</h3><p>{body}</p></div>", unsafe_allow_html=True)
    st.write("")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Model", "Bass", "1969, still standard")
    metric_columns[1].metric("Published analogs", f"{len(ANALOG_PARAMETERS)}", "with citations")
    metric_columns[2].metric("Estimation", "NLS", "with OLS fallback")
    metric_columns[3].metric("Data stored", "None", "by the app")
    st.markdown(
        """
        <div class="as-quote">“Would you tell me, please, which way I ought to go from here?”<br>
        “That depends a good deal on where you want to get to.”<br>
        “I don't much care where—”<br>
        “Then it doesn't much matter which way you go.”<br>
        <b>— ALICE IN WONDERLAND, LEWIS CARROLL</b></div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Where this tool fits"):
        st.write(
            "AdoptSignal answers *when* customers will adopt. Its siblings answer the other launch questions: "
            "ChoiceSignal measures *what* customers value in a design, SegmentSignal finds *who* the distinct "
            "groups are, PositionSignal maps *how the market perceives* competing brands, and WorthSignal "
            "estimates *what a customer is worth* once acquired."
        )


def market_page() -> None:
    st.title("Frame the market and borrow parameters")
    st.write(
        "A Bass forecast needs three numbers: the market potential *m* (eventual adopters), the innovation "
        "parameter *p* (adoption pressure from advertising and independent discovery), and the imitation "
        "parameter *q* (adoption pressure from word of mouth and social influence)."
    )
    m = st.number_input(
        "Market potential m — customers who will EVENTUALLY adopt",
        min_value=100.0, max_value=1e9, value=float(st.session_state.get("plan", {}).get("m", 100_000)),
        step=1000.0, format="%.0f",
        help="Not the population: the share of it that would realistically ever adopt — a judgment combining the "
        "target population with a defensible eventual penetration. Document how you arrived at it.",
    )
    st.subheader("Borrow p and q from published analogies")
    st.caption(
        "These estimates come from the published diffusion literature (per **year**). Choose categories whose "
        "adoption story resembles yours; the suggestion is their average. Analogy is judgment — document your choice."
    )
    full_width(st.dataframe, ANALOG_PARAMETERS, hide_index=True)
    chosen = st.multiselect(
        "Analog categories", ANALOG_PARAMETERS["category"].tolist(),
        default=st.session_state.get("plan", {}).get("analogs", ["Cross-category average"]),
    )
    try:
        suggested_p, suggested_q = analog_suggestion(chosen) if chosen else (0.03, 0.42)
    except Exception as exc:
        show_error(exc)
        suggested_p, suggested_q = 0.03, 0.42
    tune = st.columns(2)
    p = tune[0].slider("Innovation parameter p", 0.001, 0.100, float(round(suggested_p, 3)), 0.001, format="%.3f")
    q = tune[1].slider("Imitation parameter q", 0.05, 0.90, float(round(suggested_q, 2)), 0.01)
    if q <= p:
        st.warning("With q ≤ p there is almost no word-of-mouth engine: adoption starts at its maximum and only declines.")

    preview_curve = bass_curve(p, q, m, 60)
    preview_peak = preview_curve.loc[preview_curve["new_adopters"].idxmax()]
    preview = st.columns(3)
    preview[0].metric("Sales peak in period", f"{int(preview_peak['period'])}")
    preview[1].metric("Peak-period adoptions", f"{preview_peak['new_adopters']:,.0f}")
    preview[2].metric("Adopting in period 1", f"{preview_curve['new_adopters'].iloc[0]:,.0f}")
    st.caption(
        "Periods follow the analogs' unit — years for the published table. If you plan in quarters, published "
        "yearly parameters do not transfer directly; prefer fitting your own quarterly history on page 3."
    )
    if st.button("Save this launch plan", type="primary"):
        st.session_state["plan"] = {"m": float(m), "p": float(p), "q": float(q), "analogs": chosen}
        st.success("Plan saved. Continue to the forecast.")
    if st.session_state.get("plan"):
        st.write("")
        if full_width(st.button, "Continue to 2 · Forecast & scenarios →"):
            go_to("2 · Forecast & scenarios")
            st.rerun()


def _curve_chart(curves: dict[str, pd.DataFrame], value_column: str, y_title: str) -> go.Figure:
    figure = go.Figure()
    palette = [COLORS["ink"], COLORS["coral"], COLORS["mint"], COLORS["gold"]]
    for index, (label, curve) in enumerate(curves.items()):
        figure.add_trace(
            go.Scatter(
                x=curve["period"], y=curve[value_column], mode="lines+markers", name=label,
                line=dict(color=palette[index % len(palette)], width=2.4),
                marker=dict(size=5),
            )
        )
    figure.update_layout(
        height=420, margin=dict(l=10, r=10, t=20, b=10), legend_title_text="",
        xaxis_title="Period", yaxis_title=y_title, hovermode="x unified",
    )
    return figure


def forecast_page() -> None:
    st.title("The adoption curve, and how fragile it is")
    plan = st.session_state.get("plan")
    if not plan:
        st.info("Save a launch plan on page 1 first.")
        return
    context = st.columns(4)
    context[0].metric("Market potential", f"{plan['m']:,.0f}")
    context[1].metric("p (innovation)", f"{plan['p']:.3f}")
    context[2].metric("q (imitation)", f"{plan['q']:.2f}")
    context_curve = bass_curve(plan["p"], plan["q"], plan["m"], 60)
    context[3].metric(
        "Sales peak in period", f"{int(context_curve.loc[context_curve['new_adopters'].idxmax(), 'period'])}"
    )
    horizon = st.slider("Forecast horizon (periods)", 5, 60, 15)

    try:
        base = bass_curve(plan["p"], plan["q"], plan["m"], horizon)
    except Exception as exc:
        show_error(exc)
        return
    st.subheader("New adopters per period")
    full_width(st.plotly_chart, _curve_chart({"Base plan": base}, "new_adopters", "New adopters"))
    st.subheader("Cumulative adoption")
    cumulative_chart = _curve_chart({"Base plan": base}, "cumulative_adopters", "Cumulative adopters")
    cumulative_chart.add_hline(y=plan["m"], line_dash="dot", line_color=COLORS["muted"],
                               annotation_text="market potential m")
    full_width(st.plotly_chart, cumulative_chart)

    with st.expander("Stress-test the word of mouth", expanded=True):
        st.caption(
            "The imitation parameter q is the least certain and the most powerful. The same plan with slower or "
            "faster word of mouth:"
        )
        scenarios = {
            "Slower word of mouth (q × 0.7)": bass_curve(plan["p"], plan["q"] * 0.7, plan["m"], horizon),
            "Base plan": base,
            "Faster word of mouth (q × 1.3)": bass_curve(plan["p"], min(plan["q"] * 1.3, 1.99), plan["m"], horizon),
        }
        full_width(st.plotly_chart, _curve_chart(scenarios, "new_adopters", "New adopters"))
        summary = pd.DataFrame(
            [
                {
                    "scenario": label,
                    "peak_period": int(curve.loc[curve["new_adopters"].idxmax(), "period"]),
                    "peak_adoptions": round(float(curve["new_adopters"].max())),
                    "penetration_at_horizon_%": round(float(curve["penetration_%"].iloc[-1]), 1),
                }
                for label, curve in scenarios.items()
            ]
        )
        full_width(st.dataframe, summary, hide_index=True)

    st.subheader("Export the forecast")
    metadata = {
        "product": "AdoptSignal", "version": __version__,
        "model": "Bass diffusion (discrete recursion for curves; continuous forms for peak metrics)",
        "market_potential_m": plan["m"], "p": plan["p"], "q": plan["q"],
        "analog_categories": plan.get("analogs", []), "horizon_periods": horizon,
        "library_versions": {
            "python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "streamlit": st.__version__,
        },
        "caution": "Structured scenario, not a prediction; m and q are judgments.",
    }
    manifest = pd.DataFrame(
        {"field": list(metadata),
         "value": [json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value) for value in metadata.values()]}
    )
    tables = {"Forecast manifest": manifest, "Base forecast": base}
    for label, curve in list(scenarios.items()):
        if label != "Base plan":
            tables[label[:31]] = curve
    downloads = st.columns(3)
    full_width(
        downloads[0].download_button, "Download Excel pack", results_to_excel(tables),
        "adoptsignal_forecast.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    full_width(
        downloads[1].download_button, "Download forecast CSV",
        safe_for_spreadsheet(base).to_csv(index=False).encode("utf-8"), "adoptsignal_forecast.csv", "text/csv",
    )
    full_width(
        downloads[2].download_button, "Download JSON + audit trail",
        results_to_json({"base_forecast": base}, metadata), "adoptsignal_forecast.json", "application/json",
    )


def fit_page() -> None:
    st.title("Fit the model to your own adoption history")
    st.write(
        "One row per period with the number of **first-time adopters** (or unit sales for a durable). "
        "The app estimates p, q, and m from the shape of the curve."
    )
    frame = current_frame()
    if frame is None:
        st.info("Bring a CSV, Excel, or JSON file in the sidebar—or use a fictional demo history.")
        return
    full_width(st.dataframe, frame.head(10), hide_index=True)
    columns = [str(column) for column in frame.columns]
    period_guess = next(
        (index for index, column in enumerate(columns) if any(
            token in column.lower() for token in ("period", "quarter", "month", "year", "week", "date")
        )), 0,
    )
    numeric_hints = [index for index, column in enumerate(columns) if any(
        token in column.lower() for token in ("adopt", "sales", "sold", "units", "subscribers", "customers", "count")
    )]
    period_column = st.selectbox("Period column", columns, index=period_guess)
    adopters_column = st.selectbox(
        "New adopters per period", columns, index=numeric_hints[0] if numeric_hints else len(columns) - 1
    )
    if st.button("Fit the Bass model", type="primary"):
        try:
            series, series_warnings = prepare_adoption_series(frame, period_column, adopters_column)
            st.session_state["history_fit"] = fit_bass(series)
            st.session_state["history_warnings"] = series_warnings
        except Exception as exc:
            show_error(exc)

    fit = st.session_state.get("history_fit")
    if fit is None:
        return
    for warning in st.session_state.get("history_warnings", []):
        st.warning(warning)
    for warning in fit.warnings:
        st.warning(warning)
    metrics = st.columns(4)
    metrics[0].metric("p (innovation)", f"{fit.p:.4f}")
    metrics[1].metric("q (imitation)", f"{fit.q:.3f}")
    metrics[2].metric("Market potential m", f"{fit.m:,.0f}")
    metrics[3].metric("Fit R²", f"{fit.r_squared:.2f}")
    st.caption(
        f"Estimated by {'nonlinear least squares' if fit.method == 'nls' else 'Bass’s original regression'} on "
        f"{len(fit.fitted)} periods. p is always the least precisely identified parameter; q and m carry the story."
    )
    if fit.standard_errors:
        se = fit.standard_errors
        st.caption(
            f"Approximate standard errors (model-conditional): p ± {se['p']:.4f}, q ± {se['q']:.3f}, "
            f"m ± {se['m']:,.0f}. The uncertainty in m is usually the widest — especially before the peak — "
            "and p, q, and m are strongly correlated, so read them jointly, not one at a time."
        )

    extra = st.slider("Forecast further periods beyond the history", 0, 40, 8)
    observed = fit.fitted
    figure = go.Figure()
    figure.add_trace(go.Bar(x=observed["period"], y=observed["new_adopters"], name="Actual",
                            marker_color=COLORS["mint"]))
    figure.add_trace(go.Scatter(x=observed["period"], y=observed["fitted_new_adopters"], name="Fitted",
                                mode="lines", line=dict(color=COLORS["ink"], width=2.4)))
    if extra:
        forward = forecast_beyond(fit, extra)
        remaining = max(float(fit.m) - float(observed["fitted_cumulative"].iloc[-1]), 0.0)
        figure.add_trace(go.Scatter(
            x=[f"+{index}" for index in range(1, extra + 1)], y=forward["forecast_new_adopters"],
            name="Forecast", mode="lines+markers", line=dict(color=COLORS["coral"], width=2.4, dash="dash"),
        ))
        st.caption(
            f"About {remaining:,.0f} adopters remain before the fitted market potential is exhausted "
            "(measured on the fitted curve, the same curve the forecast extends)."
        )
    figure.update_layout(height=440, margin=dict(l=10, r=10, t=20, b=10), legend_title_text="",
                         xaxis_title="Period", yaxis_title="New adopters", hovermode="x unified")
    full_width(st.plotly_chart, figure)

    export_tables = {"Fitted history": fit.fitted}
    fingerprint = hashlib.sha256(
        pd.util.hash_pandas_object(fit.fitted[["period", "new_adopters"]].astype(str), index=True).values.tobytes()
    ).hexdigest()
    metadata = {
        "product": "AdoptSignal", "version": __version__, "source": st.session_state.get("source_name"),
        "estimation": "Srinivasan–Mason NLS with Bass-regression start" if fit.method == "nls" else "Bass regression (OLS)",
        "p": round(fit.p, 6), "q": round(fit.q, 6), "m": round(fit.m, 2), "r_squared": round(fit.r_squared, 4),
        "history_has_peaked": fit.peaked, "periods": len(fit.fitted),
        "dataset_fingerprint_sha256": fingerprint,
        "caution": "Pre-peak histories identify m poorly; refit as new periods arrive.",
    }
    full_width(
        st.download_button, "Download fit + forecast (JSON + audit trail)",
        results_to_json(export_tables, metadata), "adoptsignal_fit.json", "application/json",
    )


def methods_page() -> None:
    st.title("Methods, assumptions, and honest limits")
    st.markdown(CAUTION)
    st.subheader("The model")
    st.write(
        "Bass (1969): adopters arrive from two forces — an innovation force p acting on everyone who has not yet "
        "adopted, and an imitation force q scaled by how many have already adopted. New adopters in a period are "
        "n(t) = (p + q·N/m)(m − N), where N is cumulative adoption. Small p with larger q produces the familiar "
        "S-curve with a take-off, a peak at ln(q/p)/(p+q), and saturation at m."
    )
    method_columns = st.columns(2)
    with method_columns[0]:
        with st.container(border=True):
            st.markdown("#### Analogies before launch")
            st.write(
                "With no sales history, p and q are borrowed from published estimates for categories that spread "
                "the way yours might. Across hundreds of studied categories the averages are roughly p ≈ 0.03 and "
                "q ≈ 0.42 per year. The analogy is a judgment; the app records which analogs you chose."
            )
    with method_columns[1]:
        with st.container(border=True):
            st.markdown("#### Estimation from history")
            st.write(
                "With real periods, the app fits the continuous cumulative Bass curve by nonlinear least squares, "
                "started (and backstopped) by Bass's original regression. Histories that have not passed their "
                "sales peak identify the market potential poorly — the app says so instead of hiding it."
            )
    st.subheader("Important boundaries")
    st.markdown(
        """
        - The model covers **first-time adoption** of one innovation: no repeat purchases, replacements, upgrades, or churn.
        - Market potential m is an input judgment before launch; even fitted, it is fragile until the peak has passed.
        - Price, advertising, distribution, competition, and successive technology generations are outside the basic model.
        - Published p and q are per **year**; they do not transfer directly to quarterly or monthly planning.
        - Analogies inherit the chooser's optimism. Choosing only fast-diffusing analogs bakes the answer in.
        - A good fit to history does not validate the forecast beyond it — diffusion curves fit many shapes in-sample.
        """
    )
    with st.expander("References and implementation notes"):
        st.write(
            "See `docs/methods.md` for formulas, estimation details, and citations (Bass 1969; Srinivasan & Mason "
            "1986; Sultan, Farley & Lehmann 1990; Van den Bulte & Stremersch 2004; Lilien, Rangaswamy & De Bruyn "
            "2017). Every computational module is separate from Streamlit and covered by automated tests."
        )


if page == "Welcome":
    welcome_page()
elif page == "1 · Market & analogs":
    market_page()
elif page == "2 · Forecast & scenarios":
    forecast_page()
elif page == "3 · Fit your own history":
    fit_page()
else:
    methods_page()

st.markdown(
    f"<div class='as-footer'>AdoptSignal v{__version__} <span>◆</span> Structured forecast, not prediction "
    "<span>◆</span> Part of the Signal suite <span>◆</span> AGPL-3.0-or-later</div>",
    unsafe_allow_html=True,
)
