"""Adopt Signal Streamlit UI.

Everything that draws the app runs inside ``render()`` (or the functions it calls), so it runs on every rerun,
both in the standalone ``app.py`` and inside Signal Hub. Module-level code here only defines constants and
functions. ``render()`` never calls ``st.set_page_config`` or ``st.navigation``.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import platform
import traceback

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
from adoptsignal.examples import demo_csv_bytes
from adoptsignal.io import LoadedData, load_data, results_to_excel, results_to_json, safe_for_spreadsheet
from adoptsignal.ui import signal_theme as sig


NS = "adopt"


def k(name: str) -> str:
    """Namespace a session-state or widget key with the app slug, so apps can share one Hub session."""
    return f"{NS}:{name}"


SIDEBAR_TAGLINE = "Know when the market will follow."
MASTHEAD_KICKER = "OPEN ADOPTION FORECASTING"
MASTHEAD_PROMISES = ["Local-first", "Explainable", "Open source"]
FOOTER_LINE = "Structured forecast, not prediction"

CAUTION = (
    "**Treat every diffusion forecast as a structured guess, not a prediction.** The market potential is a "
    "judgment, the parameters come from analogies or noisy history, and the model ignores price, competition, "
    "and marketing. Its value is disciplining the growth conversation — not ending it."
)

FIT_PAGE = "3 · Fit your own history"

_USES_STRETCH_WIDTH = "width" in inspect.signature(st.button).parameters


def full_width(widget, *args, **kwargs):
    """Use Streamlit's full-width API across both older and newer releases."""
    if _USES_STRETCH_WIDTH:
        kwargs["width"] = "stretch"
    else:
        kwargs["use_container_width"] = True
    return widget(*args, **kwargs)


def show_error(exc: Exception) -> None:
    """Render a useful error while keeping tracebacks opt-in."""
    st.error(friendly_message(exc))
    if not isinstance(exc, DataProblem) and os.getenv("ADOPTSIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def _ensure_state() -> None:
    st.session_state.setdefault(k("tables"), None)
    st.session_state.setdefault(k("source_name"), None)
    st.session_state.setdefault(k("active_table"), None)
    st.session_state.setdefault(k("upload_epoch"), 0)
    st.session_state.setdefault(k("data_epoch"), 0)
    st.session_state.setdefault(k("uploader_had_file"), False)
    st.session_state.setdefault(k("nav_target"), next(iter(PAGES)))


def _clear_fit() -> None:
    st.session_state.pop(k("history_fit"), None)
    st.session_state.pop(k("history_warnings"), None)


def set_loaded(loaded: LoadedData) -> None:
    st.session_state[k("tables")] = loaded.tables
    st.session_state[k("source_name")] = loaded.source_name
    st.session_state[k("active_table")] = next(iter(loaded.tables))
    # New data: the table picker and the column pickers start again from their defaults.
    st.session_state.pop(k("table_select"), None)
    st.session_state[k("data_epoch")] = int(st.session_state.get(k("data_epoch"), 0)) + 1
    _clear_fit()


def load_demo(filename: str) -> None:
    # Generated in memory (identical to the committed examples/ files), so the demos also work from a wheel.
    set_loaded(load_data(demo_csv_bytes(filename), name=filename))


def current_frame() -> pd.DataFrame | None:
    tables = st.session_state.get(k("tables"))
    if not tables:
        return None
    name = st.session_state.get(k("active_table")) or next(iter(tables))
    return tables[name]


def go_to(page_name: str) -> None:
    """Navigate programmatically.

    The page radio is keyed, and a widget's value cannot change after it is drawn, so the target is applied at
    the start of the next run, before the radio is drawn (also when a rerun interrupted this run first).
    """
    st.session_state[k("nav_target")] = page_name
    st.session_state[k("nav_pending")] = page_name


def welcome_page() -> None:
    sig.hero(
        NS,
        eyebrow="NEW-PRODUCT GROWTH, WITHOUT THE BLACK BOX",
        title="Forecast when the market",
        em="will follow.",
        body=(
            "The Bass diffusion model turns two forces — independent adoption and word of mouth — into an S-shaped "
            "forecast of new-product growth. Borrow parameters from published analogies before launch, or fit your "
            "own sales history, and see when adoption should take off, peak, and saturate."
        ),
        pills=["No account", "No telemetry", "Published analogies", "Honest pre-peak warnings"],
    )
    sig.note("warn", CAUTION)
    sig.cards(
        [
            ("STEP 01", "Frame the market", "Set a defensible market potential and borrow innovation and imitation parameters from categories that behaved like yours."),
            ("STEP 02", "Forecast & stress-test", "See the adoption curve, the time to peak, and how the story changes when word of mouth is slower or faster than hoped."),
            ("STEP 03", "Fit your own history", "Once real periods arrive, estimate the parameters from your data and let the model tell you how far the ride has left."),
        ]
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("Model", "Bass", "1969, still standard")
    metric_columns[1].metric("Published analogs", f"{len(ANALOG_PARAMETERS)}", "with citations")
    metric_columns[2].metric("Estimation", "NLS", "with OLS fallback")
    metric_columns[3].metric("Data stored", "None", "by the app")
    quote = [
        "“Would you tell me, please, which way I ought to go from here?”",
        "“That depends a good deal on where you want to get to.”",
        "“I don't much care where—”",
        "“Then it doesn't much matter which way you go.”",
    ]
    st.markdown("\n".join(f"> *{line}*  " for line in quote) + "\n>\n> **— Alice in Wonderland, Lewis Carroll**")
    with st.expander("Where this tool fits"):
        st.write(
            "Adopt Signal answers *when* customers will adopt. Its siblings answer the other launch questions: "
            "Choice Signal measures *what* customers value in a design, Segment Signal finds *who* the distinct "
            "groups are, Position Signal maps *how the market perceives* competing brands, and Worth Signal "
            "estimates *what a customer is worth* once acquired."
        )


def market_page() -> None:
    sig.header("Step 1", "Frame the market and borrow parameters")
    st.write(
        "A Bass forecast needs three numbers: the market potential *m* (eventual adopters), the innovation "
        "parameter *p* (adoption pressure from advertising and independent discovery), and the imitation "
        "parameter *q* (adoption pressure from word of mouth and social influence)."
    )
    plan = st.session_state.get(k("plan")) or {}
    m = st.number_input(
        "Market potential m — customers who will EVENTUALLY adopt",
        min_value=100.0, max_value=1e9, value=float(plan.get("m", 100_000)),
        step=1000.0, format="%.0f",
        help="Not the population: the share of it that would realistically ever adopt — a judgment combining the "
        "target population with a defensible eventual penetration. Document how you arrived at it.",
        key=k("market_potential"),
    )
    st.subheader("Borrow p and q from published analogies")
    st.caption(
        "These estimates come from the published diffusion literature (per **year**). Choose categories whose "
        "adoption story resembles yours; the suggestion is their average. Analogy is judgment — document your choice."
    )
    full_width(st.dataframe, ANALOG_PARAMETERS, hide_index=True)
    chosen = st.multiselect(
        "Analog categories", ANALOG_PARAMETERS["category"].tolist(),
        default=plan.get("analogs", ["Cross-category average"]),
        key=k("analogs"),
    )
    try:
        suggested_p, suggested_q = analog_suggestion(chosen) if chosen else (0.03, 0.42)
    except Exception as exc:
        show_error(exc)
        suggested_p, suggested_q = 0.03, 0.42
    start_p, start_q = float(round(suggested_p, 3)), float(round(suggested_q, 2))
    tune = st.columns(2)
    # The slider keys carry the suggestion, so choosing other analogs moves the sliders to the new suggestion.
    p = tune[0].slider(
        "Innovation parameter p", 0.001, 0.100, start_p, 0.001, format="%.3f", key=k(f"innovation_p_{start_p:.3f}")
    )
    q = tune[1].slider("Imitation parameter q", 0.05, 0.90, start_q, 0.01, key=k(f"imitation_q_{start_q:.2f}"))
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
    if st.button("Save this launch plan", type="primary", key=k("save_plan")):
        st.session_state[k("plan")] = {"m": float(m), "p": float(p), "q": float(q), "analogs": chosen}
        st.success("Plan saved. Continue to the forecast.")
    if st.session_state.get(k("plan")):
        st.write("")
        if full_width(st.button, "Continue to 2 · Forecast & scenarios →", key=k("continue_forecast")):
            go_to("2 · Forecast & scenarios")
            st.rerun()


def _curve_chart(curves: dict[str, pd.DataFrame], value_column: str, y_title: str) -> go.Figure:
    figure = go.Figure()
    palette = sig.colorway(NS)
    for index, (label, curve) in enumerate(curves.items()):
        figure.add_trace(
            go.Scatter(
                x=curve["period"], y=curve[value_column], mode="lines+markers", name=label,
                line={"color": palette[index % len(palette)], "width": 2.4},
                marker={"size": 5},
            )
        )
    figure.update_layout(
        template=sig.template(NS),
        height=420, margin={"l": 10, "r": 10, "t": 20, "b": 10}, legend_title_text="",
        xaxis_title="Period", yaxis_title=y_title, hovermode="x unified",
    )
    return figure


def forecast_page() -> None:
    sig.header("Step 2", "The adoption curve, and how fragile it is")
    plan = st.session_state.get(k("plan"))
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
    horizon = st.slider("Forecast horizon (periods)", 5, 60, 15, key=k("horizon"))

    try:
        base = bass_curve(plan["p"], plan["q"], plan["m"], horizon)
    except Exception as exc:
        show_error(exc)
        return
    st.subheader("New adopters per period")
    sig.chart(NS, _curve_chart({"Base plan": base}, "new_adopters", "New adopters"), key=k("new_adopters_chart"))
    st.subheader("Cumulative adoption")
    cumulative_chart = _curve_chart({"Base plan": base}, "cumulative_adopters", "Cumulative adopters")
    cumulative_chart.add_hline(y=plan["m"], line_dash="dot", line_color=sig.CORE["muted"],
                               annotation_text="market potential m")
    sig.chart(NS, cumulative_chart, key=k("cumulative_chart"))

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
        sig.chart(NS, _curve_chart(scenarios, "new_adopters", "New adopters"), key=k("scenario_chart"))
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
        "product": "Adopt Signal", "version": __version__,
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
        key=k("download_forecast_excel"),
    )
    full_width(
        downloads[1].download_button, "Download forecast CSV",
        safe_for_spreadsheet(base).to_csv(index=False).encode("utf-8"), "adoptsignal_forecast.csv", "text/csv",
        key=k("download_forecast_csv"),
    )
    full_width(
        downloads[2].download_button, "Download JSON + audit trail",
        results_to_json({"base_forecast": base}, metadata), "adoptsignal_forecast.json", "application/json",
        key=k("download_forecast_json"),
    )


def fit_page() -> None:
    sig.header("Step 3", "Fit the model to your own adoption history")
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
    # The column-picker keys carry the data epoch, so a new file or sheet starts again from the guesses.
    epoch = int(st.session_state.get(k("data_epoch"), 0))
    period_column = st.selectbox("Period column", columns, index=period_guess, key=k(f"period_column_{epoch}"))
    adopters_column = st.selectbox(
        "New adopters per period", columns, index=numeric_hints[0] if numeric_hints else len(columns) - 1,
        key=k(f"adopters_column_{epoch}"),
    )
    if st.button("Fit the Bass model", type="primary", key=k("fit_model")):
        try:
            series, series_warnings = prepare_adoption_series(frame, period_column, adopters_column)
            st.session_state[k("history_fit")] = fit_bass(series)
            st.session_state[k("history_warnings")] = series_warnings
        except Exception as exc:
            show_error(exc)

    fit = st.session_state.get(k("history_fit"))
    if fit is None:
        return
    for warning in st.session_state.get(k("history_warnings"), []):
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

    extra = st.slider("Forecast further periods beyond the history", 0, 40, 8, key=k("extra_periods"))
    observed = fit.fitted
    roles = sig.roles(NS)
    figure = go.Figure()
    figure.add_trace(go.Bar(x=observed["period"], y=observed["new_adopters"], name="Actual",
                            marker_color=roles["highlight"]))
    figure.add_trace(go.Scatter(x=observed["period"], y=observed["fitted_new_adopters"], name="Fitted",
                                mode="lines", line={"color": roles["estimate"], "width": 2.4}))
    if extra:
        forward = forecast_beyond(fit, extra)
        remaining = max(float(fit.m) - float(observed["fitted_cumulative"].iloc[-1]), 0.0)
        figure.add_trace(go.Scatter(
            x=[f"+{index}" for index in range(1, extra + 1)], y=forward["forecast_new_adopters"],
            name="Forecast", mode="lines+markers",
            line={"color": sig.colorway(NS)[1], "width": 2.4, "dash": "dash"},
        ))
        st.caption(
            f"About {remaining:,.0f} adopters remain before the fitted market potential is exhausted "
            "(measured on the fitted curve, the same curve the forecast extends)."
        )
    figure.update_layout(template=sig.template(NS),
                         height=440, margin={"l": 10, "r": 10, "t": 20, "b": 10}, legend_title_text="",
                         xaxis_title="Period", yaxis_title="New adopters", hovermode="x unified")
    sig.chart(NS, figure, key=k("fit_chart"))

    export_tables = {"Fitted history": fit.fitted}
    fingerprint = hashlib.sha256(
        pd.util.hash_pandas_object(fit.fitted[["period", "new_adopters"]].astype(str), index=True).values.tobytes()
    ).hexdigest()
    metadata = {
        "product": "Adopt Signal", "version": __version__, "source": st.session_state.get(k("source_name")),
        "estimation": "Srinivasan–Mason NLS with Bass-regression start" if fit.method == "nls" else "Bass regression (OLS)",
        "p": round(fit.p, 6), "q": round(fit.q, 6), "m": round(fit.m, 2), "r_squared": round(fit.r_squared, 4),
        "history_has_peaked": fit.peaked, "periods": len(fit.fitted),
        "dataset_fingerprint_sha256": fingerprint,
        "caution": "Pre-peak histories identify m poorly; refit as new periods arrive.",
    }
    full_width(
        st.download_button, "Download fit + forecast (JSON + audit trail)",
        results_to_json(export_tables, metadata), "adoptsignal_fit.json", "application/json",
        key=k("download_fit"),
    )


def methods_page() -> None:
    sig.header("Methods & limits", "Methods, assumptions, and honest limits")
    sig.note("warn", CAUTION)
    st.subheader("The model")
    st.write(
        "Bass (1969): adopters arrive from two forces — an innovation force p acting on everyone who has not yet "
        "adopted, and an imitation force q scaled by how many have already adopted. New adopters in a period are "
        "n(t) = (p + q·N/m)(m − N), where N is cumulative adoption. Small p with larger q produces the familiar "
        "S-curve with a take-off, a peak at ln(q/p)/(p+q), and saturation at m."
    )
    method_columns = st.columns(2)
    with method_columns[0], st.container(border=True):
        st.markdown("#### Analogies before launch")
        st.write(
            "With no sales history, p and q are borrowed from published estimates for categories that spread "
            "the way yours might. Across hundreds of studied categories the averages are roughly p ≈ 0.03 and "
            "q ≈ 0.42 per year. The analogy is a judgment; the app records which analogs you chose."
        )
    with method_columns[1], st.container(border=True):
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


PAGES = {
    "Welcome": welcome_page,
    "1 · Market & analogs": market_page,
    "2 · Forecast & scenarios": forecast_page,
    FIT_PAGE: fit_page,
    "Methods & limits": methods_page,
}


def _sidebar_data() -> None:
    """Upload, demo and table controls. Loading data jumps to the fit page."""
    st.markdown("### Forecast without data")
    st.caption("Pages 1–2 need no file: set the market and borrow parameters from published analogies.")
    st.markdown("### Or fit your history")
    uploaded = st.file_uploader(
        "CSV, Excel, or JSON with one row per period",
        type=["csv", "xlsx", "xls", "xlsm", "json"],
        key=k(f"history_upload_{st.session_state[k('upload_epoch')]}"),
    )
    if uploaded is not None:
        upload_identity = (
            str(getattr(uploaded, "file_id", "") or f"widget-{st.session_state[k('upload_epoch')]}"),
            uploaded.name,
            int(getattr(uploaded, "size", 0)),
        )
        st.session_state[k("uploader_had_file")] = True
        if st.session_state.get(k("upload_identity")) != upload_identity:
            try:
                raw = uploaded.getvalue()
                set_loaded(load_data(raw, name=uploaded.name))
                st.session_state[k("upload_identity")] = upload_identity
                st.session_state[k("uploader_had_file")] = False
                st.session_state[k("upload_epoch")] = int(st.session_state.get(k("upload_epoch"), 0)) + 1
                go_to(FIT_PAGE)
                st.rerun()
            except Exception as exc:
                show_error(exc)
    elif st.session_state.get(k("uploader_had_file")):
        st.session_state[k("uploader_had_file")] = False
    if full_width(st.button, "Demo · smart-lock sales", key=k("demo_smartlock")):
        load_demo("demo_smartlock_sales.csv")
        go_to(FIT_PAGE)
        st.rerun()
    if full_width(st.button, "Demo · early meal-kit data", key=k("demo_mealkit")):
        load_demo("demo_mealkit_early.csv")
        go_to(FIT_PAGE)
        st.rerun()
    with st.expander("What are the demos?"):
        st.caption(
            "**Smart-lock sales:** 16 fictional quarters of unit sales, clearly past the sales peak — a "
            "comfortable fit.\n\n"
            "**Early meal-kit data:** only 6 fictional quarters, before the peak — shows how honest the app is "
            "about pre-peak uncertainty.\n\nEvery record is synthetic."
        )
    if st.session_state.get(k("tables")) and full_width(st.button, "Clear session data", key=k("clear_data")):
        for name in (
            "tables", "source_name", "active_table", "upload_identity", "uploader_had_file",
            "plan", "history_fit", "history_warnings", "table_select",
        ):
            st.session_state.pop(k(name), None)
        st.session_state[k("upload_epoch")] = int(st.session_state.get(k("upload_epoch"), 0)) + 1
        go_to("Welcome")
        st.rerun()
    if st.session_state.get(k("tables")):
        table_names = list(st.session_state[k("tables")])
        active_name = st.session_state.get(k("active_table"))
        selected_table = st.selectbox(
            "Table / sheet",
            table_names,
            index=table_names.index(active_name) if active_name in table_names else 0,
            key=k("table_select"),
        )
        if selected_table != st.session_state.get(k("active_table")):
            st.session_state[k("active_table")] = selected_table
            st.session_state[k("data_epoch")] = int(st.session_state.get(k("data_epoch"), 0)) + 1
            _clear_fit()
        active = st.session_state[k("tables")][selected_table]
        st.caption(f"{st.session_state.get(k('source_name'))} · {len(active):,} rows × {len(active.columns)} columns")


def _sidebar() -> str:
    """Draw the sidebar lockup, data controls and page selector; return the selected page."""
    sig.sidebar_brand(NS, SIDEBAR_TAGLINE)
    with st.sidebar:
        _sidebar_data()
        st.markdown("### Follow the workflow")
        pending = st.session_state.pop(k("nav_pending"), None)
        if pending in PAGES:
            st.session_state[k("page")] = pending
        elif k("page") not in st.session_state:
            st.session_state[k("page")] = st.session_state[k("nav_target")]
        page = st.radio("Page", list(PAGES), key=k("page"), label_visibility="collapsed")
        st.session_state[k("nav_target")] = page
    return page


def render() -> None:
    """Draw the whole Adopt Signal app on the current page. Never calls st.set_page_config or st.navigation."""
    sig.apply(NS)
    _ensure_state()
    page = _sidebar()
    sig.masthead(NS, MASTHEAD_PROMISES, MASTHEAD_KICKER)
    try:
        PAGES[page]()
    except Exception as exc:
        show_error(exc)
    sig.footer(NS, __version__, FOOTER_LINE)
