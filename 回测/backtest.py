# -*- coding: utf-8 -*-
"""
Execution-honest backtest for the early-session sentiment factor.
早盘情绪因子的诚实口径回测。

The signal is known at 09:55 but fills happen around 10:00, so a switching day
is split into a morning leg (open -> 10:00) and an intraday leg (10:00 -> close):

    R_timed_t = p_{t-1} * m_t + p_t * r_t          # m: morning leg, r: intraday leg

On a day you cut exposure, the morning-leg loss is borne in full (empirically
about 78% of a cash-day's fall has already happened by 09:55). Filling at the
open would overstate the Sharpe by roughly a factor of two.

Metrics: annualized Sharpe (mean-based), max drawdown, CAGR, time-in-market.
"""
import numpy as np
import pandas as pd

ANN = 252


def perf(nav: pd.Series) -> dict:
    nav = nav.dropna()
    if len(nav) < 5:
        return dict(sharpe=np.nan, max_drawdown=np.nan, cagr=np.nan, cum=np.nan)
    nav = nav / nav.iloc[0]
    r = nav.pct_change().dropna()
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    return dict(
        sharpe=(r.mean() * ANN) / (r.std() * np.sqrt(ANN)) if r.std() > 0 else np.nan,
        max_drawdown=(nav / nav.cummax() - 1).min(),
        cagr=nav.iloc[-1] ** (1 / yrs) - 1,
        cum=nav.iloc[-1],
    )


def timed_nav(segments: pd.DataFrame, signal: pd.Series,
              cost: float = 0.0, stamp: float = 0.001) -> pd.Series:
    """Execution-honest timed NAV.

    segments: daily DataFrame with columns m (prev_close->10:00), r (10:00->close),
              d (full day); all as portfolio-weighted returns.
    signal:   daily 0/1 series (1 = hold, 0 = cash), aligned same-day (lag = 0).
    """
    p = signal.reindex(segments.index).ffill().fillna(1.0).clip(0, 1)
    pp = p.shift(1).fillna(p.iloc[0])
    gross = pp * segments["m"] + p * segments["r"]
    dp = p - pp
    trade_cost = np.where(dp < 0, -dp * (cost + stamp), dp * cost)
    return (1 + (gross - trade_cost)).cumprod()


def untimed_nav(segments: pd.DataFrame) -> pd.Series:
    """Buy-and-hold NAV from the full-day leg."""
    return (1 + segments["d"]).cumprod()


def report(segments: pd.DataFrame, signal: pd.Series, cost: float = 0.0) -> pd.DataFrame:
    """Side-by-side metrics: no timing vs timed."""
    u, t = perf(untimed_nav(segments)), perf(timed_nav(segments, signal, cost))
    inmkt = signal.reindex(segments.index).ffill().mean()
    out = pd.DataFrame({"no_timing": u, "timed": t}).T
    out["time_in_market"] = [1.0, inmkt]
    return out
