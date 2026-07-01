# Early-Session Sentiment Factor / 早盘情绪因子

A market-timing factor for Chinese A-shares built on one idea: the cross-sectional
*breadth* of the first minutes of trading is a clean read on systematic risk. When
most stocks fall together at the open, cut exposure for the day.

一个 A 股择时因子。核心思想:开盘后前十几分钟**下跌个股的广度**,是当日系统性风险的干净读数;当全市场早盘同步下跌,当日降仓避险。

---

## 中文

### 逻辑
- 个股早盘涨幅 `r_i = 09:55价 / 开盘价 - 1`。
- 下跌广度 `D_t = mean(1[r_i < 0])`,在清洗后的全市场上统计。
- 信号 `S_t = 1 if D_t <= 0.40 else 0`(1 满仓、0 空仓)。
- 直觉:隔夜信息无法交易,开盘时被集中重定价;**广度**能把"全市场同步的系统性事件"与"个股噪声"分开——普跌当日大概率延续弱势。

### 适用范围
- A 股、**日频**的多头组合(选股/指数增强)。信号是全市场早盘广度,只对日级择时有意义。
- 投资域:主板+创业板+科创板(剔北交所),逐期剔 ST/次新/一字/停牌,含退市股。
- 不适用:分钟级高频、非 A 股、已自带强择时的策略。

### 表现(2015–2025,诚实成交口径,毛于成本)
叠加到小市值组合:夏普 **1.06 → 2.22**,最大回撤 **−55% → −32%**,在市约 34%。早盘广度对成交后市场收益的信息系数 IC≈0.18(Newey–West t=8.1)。机理上它是一个**广义的早盘情绪 beta 择时器**,对沪深300 等大盘同样减风险,收益随标的下行风险放大。**价值集中在熊市与踩踏期**;牛市/震荡因踏空而让利,2025 单边上行年甚至为负。它是一个**风险削减器**,不是收益增强器。

### 优化方向与警示
可尝试:迟滞带/部分降仓(降换手)、观测时点、与**低相关的异质信号**组合(不同数据源)、只在极端广度动作的尾部版本。

**两条警示:**
1. **过拟合风险高**。这是一个简单、机理清楚的信号,参数空间小;继续调阈值/堆变体在样本外基本是噪声。多重检验下,边际改动的显著性经不起检验。
2. **在我已做的多方向尝试里,目前没有能显著超过原因子的。** 迟滞带、同族集成、指数动态阈值、早盘离散度、尾盘广度、期货对冲——要么是噪声级增量,要么改变了收益来源/不可执行。把劲用在"正交的新信息"上,别在这一个因子上抠参数。

### 用法
```python
from factor import load_signal, apply_timing
sig = load_signal()                              # 预计算 0/1 信号(派生指标)
timed = apply_timing(my_daily_nav, sig, lag=0)   # 叠到你自己的日频净值上
```
`python example.py` 用合成数据跑一遍(零依赖)。诚实口径回测见 `回测/backtest.py`;自定义参数重算信号见 `factor.generate_signal`(需自备数据源)。

---

## English

### Logic
- Per-stock early return `r_i = P(09:55) / Open - 1`.
- Down-breadth `D_t = mean(1[r_i < 0])` over the cleaned universe.
- Signal `S_t = 1 if D_t <= 0.40 else 0` (1 = hold, 0 = cash).
- Information accumulated overnight cannot be traded and is repriced at the open;
  breadth separates a market-wide systematic event from idiosyncratic noise, and
  broad early weakness tends to persist through the day.

### Scope
- Daily long books in A-shares (stock selection, index enhancement). The signal is
  whole-market breadth and only makes sense at daily timing granularity.
- Universe: Main Board + ChiNext + STAR (Beijing excluded), point-in-time cleaned of
  ST/IPO/limit-lock/halt, survivorship-free.
- Not for: minute-level HFT, non-A-share books, or strategies that already time hard.

### Performance (2015–2025, execution-honest, gross of cost)
On a small-cap book: Sharpe **1.06 → 2.22**, max drawdown **−55% → −32%**, ~34% time
in market. Breadth predicts the post-signal market return with IC ≈ 0.18 (Newey–West
t = 8.1). Mechanistically it is a **broad early-session sentiment beta timer**: it
de-risks even large-cap indices, and its payoff scales with the downside risk of the
timed asset. The value concentrates in bear markets and crashes; it costs return in
bull and sideways regimes through opportunity cost, and was negative in the one-sided
up-market of 2025. It is a risk reducer, not a return enhancer.

### Where to take it next, and two warnings
Worth trying: hysteresis / partial de-risking (lower turnover), the observation time,
combining with a genuinely **low-correlation** signal from a different data source, or
a tail-only version that acts only on extreme breadth.

1. **High overfitting risk.** The signal is simple and its parameter space is small;
   tuning the threshold or stacking variants is essentially noise out-of-sample and
   does not survive a multiple-testing correction.
2. **None of the directions I tried significantly beats the base factor.** Hysteresis,
   same-family ensembles, index-driven dynamic thresholds, early-session dispersion,
   a closing-session breadth factor, and a futures hedge all came back as noise-level
   gains, changed the return source, or were not executable. Spend effort on orthogonal
   new information, not on tuning this one factor.

### Usage
```python
from factor import load_signal, apply_timing
sig = load_signal()
timed = apply_timing(my_daily_nav, sig, lag=0)
```
Run `python example.py` on synthetic data (no dependencies). The execution-honest
backtest is in `回测/backtest.py`; recompute the signal from your own feed via
`factor.generate_signal`.

---

## Disclaimer / 免责声明
For research and education only. Not investment advice. Past backtested performance
does not guarantee future results. 仅供研究与学习,非投资建议;回测表现不代表未来收益。

## 详见 / Reports
- **中文报告请见** [`reports/早盘情绪因子.pdf`](reports/早盘情绪因子.pdf)
- **For the English version, see** [`reports/Early-Session-Sentiment-Factor.pdf`](reports/Early-Session-Sentiment-Factor.pdf)
