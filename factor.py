# -*- coding: utf-8 -*-
"""
Early-Session Sentiment Factor / 早盘情绪因子
================================================

A market-timing signal for Chinese A-shares. Each trading day, measure the
cross-sectional *breadth* of stock returns in the short window after the open;
when the market is broadly down, cut exposure for the day.

    early return   r_{i,t} = P_i(09:55) / Open_i - 1
    down-breadth   D_t     = mean( 1[ r_{i,t} < 0 ] )      # over the cleaned universe
    signal         S_t     = 1 if D_t <= 0.40 else 0       # 1 = hold, 0 = cash

Universe: Main Board + ChiNext + STAR (Beijing exchange excluded), point-in-time
cleaned of ST/*ST, suspensions, one-way limit locks and recent IPOs; delisted
names retained (survivorship-free).

Author: Chenyang Sun. Independent reproduction and study; the core idea (opening
breadth as a sentiment timer) is not original to the author. Research/education
only, not investment advice.
"""
import os
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SIGNAL = os.path.join(_HERE, "signal_early_session_2015_2025.csv")


# ----------------------------------------------------------------------
# Core factor
# ----------------------------------------------------------------------
def down_breadth(panel: pd.DataFrame, price_col: str = "price_0955",
                 open_col: str = "open", date_col: str = "date") -> pd.Series:
    """Daily down-breadth D_t from a long panel of one cleaned trading day per row.

    panel needs columns [date_col, open_col, price_col]. Returns a daily Series.
    早盘下跌广度:当日 (09:55价/开盘价-1 < 0) 的个股占比。
    """
    df = panel[[date_col, open_col, price_col]].copy()
    df = df[df[open_col] > 0]
    r = df[price_col] / df[open_col] - 1.0
    D = r.groupby(df[date_col]).apply(lambda x: (x < 0).mean())
    D.index = pd.to_datetime(D.index)
    return D.sort_index()


def signal_from_breadth(D: pd.Series, threshold: float = 0.40) -> pd.Series:
    """Binary timing signal S_t = 1[D_t <= threshold]. 1 = hold, 0 = cash."""
    s = (D <= threshold).astype(int)
    s.name = "signal"
    return s.sort_index()


def load_signal(path: str = None) -> pd.Series:
    """Load the precomputed daily 0/1 signal (2015-2025). Zero external deps.

    加载预计算的日频 0/1 信号(派生指标,非原始行情)。
    """
    path = path or _DEFAULT_SIGNAL
    s = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
    s.name = "signal"
    return s.sort_index()


# ----------------------------------------------------------------------
# Applying the signal to your own strategy NAV
# ----------------------------------------------------------------------
def apply_timing(nav: pd.Series, signal: pd.Series = None, lag: int = 0,
                 cost: float = 0.0, stamp: float = 0.0) -> pd.Series:
    """Overlay the signal on a daily strategy NAV. Returns the timed NAV.

    lag = 0 by design: the signal is known intraday (09:55) and acts the same
    day; do not set lag = 1. Gross by default; pass `cost` (one-way commission
    on turnover) and `stamp` (sell-side tax) to net out. Note this applies the
    signal to whole-day returns; for the execution-honest morning/intraday split
    use 回测/backtest.py.
    """
    if signal is None:
        signal = load_signal()
    nav = nav.dropna()
    r = nav.pct_change()
    pos = signal.reindex(r.index).ffill().shift(lag).fillna(1.0).clip(0, 1)
    timed = r * pos
    if cost > 0 or stamp > 0:
        dp = pos.diff().abs().fillna(0.0)
        timed = timed - dp * (cost + stamp * (pos.diff().fillna(0) < 0))
    return (1 + timed.fillna(0)).cumprod()


# ----------------------------------------------------------------------
# Optional: recompute the signal from raw data (needs your own data feed)
# ----------------------------------------------------------------------
def generate_signal(start_date, end_date, threshold: float = 0.40,
                    obs: str = "09:55", min_listed_days: int = 250,
                    chunk: int = 800) -> pd.Series:
    """Recompute the signal from rqdatac (RiceQuant) minute + daily data.

    Requires a configured rqdatac license (not distributed with this repo).
    You can swap in any data source that yields, per stock and day, the open
    price and the `obs` snapshot price over the cleaned universe.
    """
    import rqdatac
    rqdatac.init()
    inst = rqdatac.all_instruments(type="CS", market="cn")
    inst = inst[inst["exchange"].isin(["XSHG", "XSHE"])]
    if "board_type" in inst.columns:
        inst = inst[inst["board_type"].isin(["MainBoard", "GEM", "KSH"])]
    codes = inst["order_book_id"].tolist()
    listed = pd.to_datetime(inst.set_index("order_book_id")["listed_date"])
    tt = pd.Timestamp(obs).time()

    rows = []
    for i in range(0, len(codes), chunk):
        cs = codes[i:i + chunk]
        dy = rqdatac.get_price(cs, start_date, end_date, frequency="1d",
                               fields=["open", "limit_up", "limit_down"],
                               adjust_type="none", expect_df=True)
        mn = rqdatac.get_price(cs, start_date, end_date, frequency="1m",
                               fields=["close"], adjust_type="none", expect_df=True)
        if dy is None or mn is None or dy.empty or mn.empty:
            continue
        mn = mn.reset_index()
        mn = mn[mn["datetime"].dt.time == tt]
        mn["date"] = mn["datetime"].dt.normalize()
        mn = mn.rename(columns={"order_book_id": "code", "close": "p"})[["code", "date", "p"]]
        dy = dy.reset_index().rename(columns={"order_book_id": "code", "date": "date",
                                              "open": "O", "limit_up": "lu", "limit_down": "ld"})
        dy["date"] = pd.to_datetime(dy["date"]).dt.normalize()
        m = dy.merge(mn, on=["code", "date"], how="inner")
        st = _flag(rqdatac.is_st_stock, cs, start_date, end_date)
        su = _flag(rqdatac.is_suspended, cs, start_date, end_date)
        m = m.merge(st, on=["code", "date"], how="left").merge(su, on=["code", "date"], how="left")
        m = m[(m["O"] > 0) & (m.get("st", 0).fillna(0) == 0) & (m.get("su", 0).fillna(0) == 0)]
        m = m[~((m["lu"].notna()) & (m["O"] >= m["lu"] - 1e-3))]
        m = m[~((m["ld"].notna()) & (m["O"] <= m["ld"] + 1e-3))]
        m["age"] = (m["date"] - m["code"].map(listed)).dt.days
        m = m[m["age"] >= min_listed_days]
        m["r"] = m["p"] / m["O"] - 1
        rows.append(m[["date", "r"]])
    panel = pd.concat(rows, ignore_index=True).dropna(subset=["r"])
    D = panel.groupby("date")["r"].apply(lambda x: (x < 0).mean())
    D.index = pd.to_datetime(D.index)
    return signal_from_breadth(D.sort_index(), threshold)


def _flag(func, codes, s, e):
    try:
        w = func(codes, s, e)
    except Exception:
        w = None
    name = "st" if func.__name__ == "is_st_stock" else "su"
    if w is None or getattr(w, "empty", True):
        return pd.DataFrame(columns=["date", "code", name])
    lg = w.stack().rename(name).reset_index()
    lg.columns = ["date", "code", name]
    lg["date"] = pd.to_datetime(lg["date"]).dt.normalize()
    return lg
