# Methods and validation

AdoptSignal implements the Bass (1969) diffusion model for first-time adoption of an innovation.

## The model

Cumulative adoption \(N(t)\) approaches a market potential \(m\). New adopters in a period combine an
**innovation** force \(p\) (advertising, independent discovery — constant pressure on everyone who has not yet
adopted) and an **imitation** force \(q\) (word of mouth, social influence — pressure proportional to how many
have already adopted):

\[
n(t) = \left(p + q\,\frac{N(t-1)}{m}\right)\bigl(m - N(t-1)\bigr).
\]

The app uses this discrete recursion for curves and tables. Peak metrics use the continuous solution: adoption
peaks at \(t^* = \ln(q/p)/(p+q)\) with peak rate \(m(p+q)^2/(4q)\), provided \(q > p\); with \(q \le p\)
adoption starts at its maximum and declines. The continuous cumulative form is

\[
N(t) = m\,\frac{1 - e^{-(p+q)t}}{1 + (q/p)\,e^{-(p+q)t}}.
\]

## Analogies before launch

Without history, \(p\) and \(q\) are borrowed from published estimates for categories whose diffusion resembled
the new product's. The app ships the classic category table reproduced across the diffusion literature and the
cross-category averages of roughly \(p \approx 0.03\) and \(q \approx 0.42\) per year (Sultan, Farley & Lehmann
1990; Van den Bulte & Stremersch 2004). Choosing analogs is a judgment; the export records the choice. Published
parameters are per **year** and do not transfer directly to quarterly or monthly planning.

## Estimation from history

Given one row per period of first-time adopters, the app estimates \((p, q, m)\) by nonlinear least squares on
the continuous cumulative curve (Srinivasan & Mason 1986), with starting values from Bass's original regression
\(n(t) = a + bN(t-1) + cN(t-1)^2\), where \(m\) solves the quadratic and \(p = a/m\), \(q = b + p\). If NLS
fails, the regression estimates are reported with a warning. Reported fit is \(R^2\) on period adoptions.

Two published cautions are surfaced in the UI rather than buried:

- **Pre-peak instability.** Until the sales peak has clearly passed, \(m\) is weakly identified and estimates
  can change dramatically with one more period of data. The app flags any history whose maximum is its last
  observation.
- **\(p\) is imprecise.** The innovation parameter is small and estimated from the earliest, noisiest periods;
  \(q\) and \(m\) carry most of the managerial story.

## Boundaries

- First-time adoption only: no repeat purchase, replacement, upgrades, multi-unit ownership, or churn.
- No marketing-mix effects: price, advertising, and distribution are outside the basic model (extensions exist
  — e.g., the Generalized Bass Model — and are out of scope for this release).
- One innovation at a time: competition and successive technology generations are not modeled.
- In-sample fit does not validate out-of-sample forecasts; S-shaped curves fit many histories.
- The market potential is a judgment even when fitted; sensitivity analysis is a feature, not an afterthought.

## References

- Bass, F. M. (1969). A new product growth for model consumer durables. *Management Science*, 15(5), 215–227.
- Lilien, G. L., Rangaswamy, A., & De Bruyn, A. (2017). *Principles of Marketing Engineering and Analytics* (3rd ed.). DecisionPro.
- Mahajan, V., Muller, E., & Bass, F. M. (1990). New product diffusion models in marketing: A review and directions for research. *Journal of Marketing*, 54(1), 1–26.
- Srinivasan, V., & Mason, C. H. (1986). Nonlinear least squares estimation of new product diffusion models. *Marketing Science*, 5(2), 169–178.
- Sultan, F., Farley, J. U., & Lehmann, D. R. (1990). A meta-analysis of applications of diffusion models. *Journal of Marketing Research*, 27(1), 70–77.
- Van den Bulte, C., & Stremersch, S. (2004). Social contagion and income heterogeneity in new product diffusion: A meta-analytic test. *Marketing Science*, 23(4), 530–544.
