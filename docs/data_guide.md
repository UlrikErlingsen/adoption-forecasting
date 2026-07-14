# Data guide

## Forecasting needs no file

Pages 1–2 work from three numbers: market potential, and the p/q parameters (borrowed from the built-in
published analog table or set manually). Bring data only when you want to **fit** the model on page 3.

## The shape AdoptSignal expects for fitting

One row per period, in time order:

| quarter  | units_sold |
| -------- | ---------- |
| Q1 2020  | 2285       |
| Q2 2020  | 3139       |
| Q3 2020  | 4701       |

- **Period column** — any label (quarter, month, year). If the values are numeric they are sorted; otherwise the file's row order is used.
- **Adopters column** — the number of **first-time adopters** in that period. Unit sales are a fair proxy for durables bought once per customer. Do not use revenue (price changes distort the shape) or cumulative totals (the app cumulates for you).

At least 5 periods are required; a trustworthy fit usually needs the history to have passed its sales peak. Fits on pre-peak data are flagged as provisional.

## Tips

- Use consistent period lengths (all quarters or all months); mixed spacing bends the curve.
- Strip out promotions-driven spikes mentally when reading the fit — the basic model does not know about them.
- Refit as each new period arrives; watching the parameters stabilize is itself information.

## Limits

Up to 400 periods per history; files up to 200 MB (JSON 50 MB). These are responsiveness bounds — real adoption histories are dozens of rows, not thousands.
