"""
Historical scenario matching via per-layer cosine similarity.

Layers used: macro, rates, sentiment, technical (news has no historical data).
For each layer, build a time-series matrix of normalized indicators,
then compute cosine similarity between current state and every historical date.
"""

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity
from src.config import CACHE_TTL_DAILY


# ── helpers ─────────────────────────────────────────────────────────────────

def _strip_tz(series: pd.Series) -> pd.Series:
    """Remove timezone info from DatetimeIndex so mixed-tz joins don't fail."""
    if isinstance(series.index, pd.DatetimeIndex) and series.index.tz is not None:
        series = series.copy()
        series.index = series.index.tz_localize(None)
    return series


def _norm(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)


def _last(series: pd.Series):
    return float(series.iloc[-1]) if len(series) else np.nan


# ── build historical matrices ────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL_DAILY)
def _build_macro_matrix() -> pd.DataFrame:
    from src.data.macro import fetch_all_macro, fetch_cape_history, compute_buffett_indicator

    macro = fetch_all_macro()

    # Stable FRED series — always available
    cpi      = _strip_tz(macro["cpi"])
    cpi_yoy  = ((cpi / cpi.shift(12)) - 1) * 100
    series   = {
        "unemployment": _strip_tz(macro["unemployment"]),
        "cpi_yoy":      cpi_yoy.dropna(),
    }

    # Optional: CAPE and Buffett (scraping may fail on cloud)
    try:
        cape = _strip_tz(fetch_cape_history())
        if len(cape) > 50:
            series["cape"] = cape.resample("D").ffill()
    except Exception:
        pass

    try:
        _, buffett = compute_buffett_indicator()
        b = _strip_tz(buffett)
        if len(b) > 50:
            series["buffett"] = b.resample("D").ffill()
    except Exception:
        pass

    df = pd.DataFrame(series)
    df = df.ffill().dropna()
    if df.empty:
        return df
    for col in df.columns:
        df[col] = _norm(df[col])
    return df


@st.cache_data(ttl=CACHE_TTL_DAILY)
def _build_rates_matrix() -> pd.DataFrame:
    from src.data.macro import fetch_all_macro
    macro = fetch_all_macro()

    df = pd.DataFrame({
        "yield_10y2y": _strip_tz(macro["yield_curve_10y2y"]),
        "yield_10y3m": _strip_tz(macro["yield_curve_10y3m"]),
        "fed_funds":   _strip_tz(macro["fed_funds"]),
        "real_yield":  _strip_tz(macro["real_yield_10y"]),
    })
    df = df.ffill().dropna()
    for col in df.columns:
        df[col] = _norm(df[col])
    return df


@st.cache_data(ttl=CACHE_TTL_DAILY)
def _build_sentiment_matrix() -> pd.DataFrame:
    from src.data.macro import fetch_all_macro
    macro = fetch_all_macro()
    vix_hist = _strip_tz(macro["vix_history"])

    df = pd.DataFrame({"vix": vix_hist})
    df = df.dropna()
    for col in df.columns:
        df[col] = _norm(df[col])
    return df


@st.cache_data(ttl=CACHE_TTL_DAILY)
def _build_technical_matrix(ticker: str = "SPY") -> pd.DataFrame:
    from src.data.market import get_technical_history
    df = get_technical_history(ticker)
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    for col in df.columns:
        df[col] = _norm(df[col])
    return df


# ── current-state vectors ────────────────────────────────────────────────────

def _current_macro_vec(macro_matrix: pd.DataFrame) -> np.ndarray:
    from src.data.macro import get_macro_snapshot, fetch_cape_history, compute_buffett_indicator, fetch_all_macro
    snap  = get_macro_snapshot()
    macro = fetch_all_macro()

    def nv(val, series):
        s = _strip_tz(series).dropna()
        mn, mx = s.min(), s.max()
        if mx == mn or np.isnan(float(val) if val is not None else np.nan):
            return 0.5
        return float(np.clip((val - mn) / (mx - mn), 0, 1))

    cpi     = macro["cpi"]
    cpi_yoy = ((cpi / cpi.shift(12)) - 1) * 100

    lookup = {
        "unemployment": lambda: nv(snap["unemployment"], macro["unemployment"]),
        "cpi_yoy":      lambda: nv(snap["cpi_yoy"],     cpi_yoy),
        "cape":         lambda: nv(snap["cape"],         fetch_cape_history()),
        "buffett":      lambda: nv(snap["buffett"],      compute_buffett_indicator()[1]),
    }

    return np.array([lookup.get(col, lambda: 0.5)() for col in macro_matrix.columns])


def _current_rates_vec() -> np.ndarray:
    from src.data.macro import get_macro_snapshot
    snap = get_macro_snapshot()
    return np.array([
        norm_from_raw(snap["yield_10y2y"], "yield_curve_10y2y"),
        norm_from_raw(snap["yield_10y3m"], "yield_curve_10y3m"),
        norm_from_raw(snap["fed_funds"],   "fed_funds"),
        norm_from_raw(snap["real_yield"],  "real_yield_10y"),
    ])


def _current_sentiment_vec() -> np.ndarray:
    from src.data.market import fetch_vix
    from src.data.macro import fetch_all_macro
    vix = fetch_vix()
    vix_hist = fetch_all_macro()["vix_history"]
    mn, mx = vix_hist.min(), vix_hist.max()
    return np.array([float(np.clip((vix - mn) / (mx - mn), 0, 1))])


def _current_technical_vec(ticker: str = "SPY") -> np.ndarray:
    from src.data.market import get_technical_snapshot
    from src.data.market import compute_rsi, compute_historical_volatility, fetch_price_history
    snap = get_technical_snapshot(ticker)
    hist_df = get_technical_history_cached(ticker)
    if not snap or hist_df.empty:
        return np.full(5, 0.5)

    def nv(val, col):
        s = hist_df[col].dropna()
        mn, mx = s.min(), s.max()
        if mx == mn: return 0.5
        return float(np.clip((val - mn) / (mx - mn), 0, 1))

    return np.array([
        nv(snap["rsi"],              "rsi"),
        nv(snap["hvol"],             "hvol"),
        nv(snap["pct_above_ma200"],  "pct_ma200"),
        nv(snap["momentum_12m"],     "momentum_12m"),
        nv(snap["distance_from_52w_high"], "distance_52w"),
    ])


@st.cache_data(ttl=CACHE_TTL_DAILY)
def get_technical_history_cached(ticker: str):
    from src.data.market import get_technical_history
    return get_technical_history(ticker)


def _raw_series(name: str) -> pd.Series:
    from src.data.macro import fetch_all_macro
    return fetch_all_macro()[name]


def norm_from_raw(val: float, fred_name: str) -> float:
    s = _raw_series(fred_name)
    mn, mx = s.min(), s.max()
    if mx == mn: return 0.5
    return float(np.clip((val - mn) / (mx - mn), 0, 1))


# ── similarity search ────────────────────────────────────────────────────────

def _layer_similarity(current_vec: np.ndarray, matrix: pd.DataFrame) -> pd.Series:
    """Cosine similarity between current_vec and every row of matrix."""
    if len(current_vec) != matrix.shape[1]:
        # Truncate/pad to match
        n = min(len(current_vec), matrix.shape[1])
        current_vec = current_vec[:n]
        matrix = matrix.iloc[:, :n]

    mat = matrix.values
    cv  = current_vec.reshape(1, -1)
    sims = cosine_similarity(cv, mat)[0]
    return pd.Series(sims, index=matrix.index)


def find_historical_scenarios(ticker: str = "SPY", top_n: int = 5) -> list[dict]:
    """
    Returns top_n historical scenarios ranked by composite similarity
    across macro, rates, sentiment, and technical layers.
    """
    macro_m    = _build_macro_matrix()
    rates_m    = _build_rates_matrix()
    sentiment_m= _build_sentiment_matrix()
    technical_m= _build_technical_matrix(ticker)

    macro_vec  = _current_macro_vec(macro_m)
    rates_vec  = _current_rates_vec()
    sent_vec   = _current_sentiment_vec()
    tech_vec   = _current_technical_vec(ticker)

    # Align all matrices to common dates
    common = macro_m.index \
        .intersection(rates_m.index) \
        .intersection(sentiment_m.index) \
        .intersection(technical_m.index)

    # Need at least 1 year of history after each date for outcome computation
    from src.data.market import fetch_price_history
    spy_close = fetch_price_history("SPY", "22y")["Close"]
    # Strip tz from spy_close so it matches tz-naive common index
    if isinstance(spy_close.index, pd.DatetimeIndex) and spy_close.index.tz is not None:
        spy_close.index = spy_close.index.tz_localize(None)
    last_valid = spy_close.index[-252] if len(spy_close) > 252 else spy_close.index[-1]
    common = common[common <= last_valid]

    if len(common) < 50:
        return []

    sim_macro = _layer_similarity(macro_vec,   macro_m.loc[common])
    sim_rates = _layer_similarity(rates_vec,   rates_m.loc[common])
    sim_sent  = _layer_similarity(sent_vec,    sentiment_m.loc[common])
    sim_tech  = _layer_similarity(tech_vec,    technical_m.loc[common])

    composite_sim = (sim_macro + sim_rates + sim_sent + sim_tech) / 4

    # Cluster: remove dates within 90 days of a higher-scoring date
    composite_sim_sorted = composite_sim.sort_values(ascending=False)
    selected = []
    excluded = set()

    for date, score in composite_sim_sorted.items():
        if date in excluded:
            continue
        selected.append(date)
        # Exclude nearby dates
        window = pd.date_range(date - pd.Timedelta(days=90), date + pd.Timedelta(days=90), freq="D")
        excluded.update(window)
        if len(selected) >= top_n:
            break

    scenarios = []
    for date in selected:
        outcome = _compute_outcome(date, spy_close)
        scenarios.append({
            "date":           date.strftime("%Y-%m-%d"),
            "composite_sim":  round(float(composite_sim[date]) * 100, 1),
            "macro_sim":      round(float(sim_macro[date]) * 100, 1),
            "rates_sim":      round(float(sim_rates[date]) * 100, 1),
            "sentiment_sim":  round(float(sim_sent[date]) * 100, 1),
            "technical_sim":  round(float(sim_tech[date]) * 100, 1),
            **outcome,
        })

    return sorted(scenarios, key=lambda x: x["composite_sim"], reverse=True)


def _compute_outcome(date: pd.Timestamp, spy_close: pd.Series) -> dict:
    """Compute forward returns and max drawdown from a given date."""
    future = spy_close[spy_close.index > date]
    p0 = float(spy_close.asof(date)) if date in spy_close.index or len(spy_close[spy_close.index <= date]) else None
    if p0 is None or p0 == 0 or len(future) < 20:
        return {
            "fwd_3m": np.nan, "fwd_6m": np.nan, "fwd_12m": np.nan,
            "max_dd": np.nan, "dd_days": np.nan, "recovery_days": np.nan,
        }

    def fwd(days):
        idx = min(days, len(future) - 1)
        return round((float(future.iloc[idx]) / p0 - 1) * 100, 2)

    # Max drawdown over next 252 days
    horizon = future.iloc[:252]
    peak = float(horizon.cummax().iloc[0])
    trough = float(horizon.min())
    max_dd = round((trough / p0 - 1) * 100, 2)

    # Drawdown duration: days from date to trough
    trough_idx = horizon.idxmin()
    dd_days = int((trough_idx - date).days)

    # Recovery: days from trough back to p0
    after_trough = future[future.index > trough_idx]
    recovered = after_trough[after_trough >= p0]
    recovery_days = int((recovered.index[0] - trough_idx).days) if len(recovered) else None

    return {
        "fwd_3m":        fwd(63),
        "fwd_6m":        fwd(126),
        "fwd_12m":       fwd(252),
        "max_dd":        max_dd,
        "dd_days":       dd_days,
        "recovery_days": recovery_days,
    }
