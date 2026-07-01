# -*- coding: utf-8 -*-
"""
Runnable example — no market data or license needed.
可运行示例——无需任何行情数据或 license。

It loads the precomputed 0/1 signal and overlays it on a *synthetic* strategy
NAV to show the API. Replace `my_nav` with your own daily strategy NAV.

    python example.py
"""
import numpy as np
import pandas as pd
from factor import load_signal, apply_timing

signal = load_signal()
dates = signal.index
n = len(dates)
rng = np.random.default_rng(0)

# A synthetic small-cap-like NAV whose worst days cluster on signal-off days,
# which is the condition under which a de-risking overlay is supposed to help.
inmkt = signal.values == 1
daily = np.where(inmkt, rng.normal(0.0018, 0.015, n), rng.normal(0.0003, 0.020, n))
crash = (~inmkt) & (rng.random(n) < 0.02)
daily = daily.copy()
daily[crash] -= 0.040
my_nav = pd.Series((1 + pd.Series(daily, index=dates)).cumprod(), index=dates)


def stats(nav):
    nav = nav.dropna() / nav.dropna().iloc[0]
    r = nav.pct_change().dropna()
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    sharpe = (r.mean() * 252) / (r.std() * np.sqrt(252))
    mdd = (nav / nav.cummax() - 1).min()
    return sharpe, mdd, nav.iloc[-1] ** (1 / yrs) - 1


timed = apply_timing(my_nav, signal, lag=0)
for name, nav in [("no timing", my_nav), ("timed", timed)]:
    s, m, c = stats(nav)
    print(f"{name:<10} Sharpe {s:5.2f} | MaxDD {m*100:6.1f}% | CAGR {c*100:5.1f}%")
print(f"time in market: {signal.reindex(my_nav.pct_change().index).ffill().mean():.0%}")
print("\nSynthetic data for API illustration only; see the reports for real results.")
