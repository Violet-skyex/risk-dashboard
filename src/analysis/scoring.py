"""
Risk scoring engine.
Each layer produces a score 0-100 (100 = most risky).
Composite = equal-weight average across layers.
"""

import numpy as np
import pandas as pd
import streamlit as st
from src.analysis.percentile import dual_percentile, percentile_of
from src.data.macro import fetch_all_macro, fetch_cape_history, compute_buffett_indicator, get_macro_snapshot
from src.data.market import fetch_vix_history, get_technical_snapshot
from src.data.fear_greed import fetch_fear_greed
from src.config import CACHE_TTL_FAST


def _safe_avg(values: list) -> float:
    valid = [v for v in values if not np.isnan(v)]
    return float(np.mean(valid)) if valid else float("nan")


@st.cache_data(ttl=CACHE_TTL_FAST)
def score_macro_layer(ticker: str = "SPY") -> dict:
    """Valuation + macro cycle risk."""
    snap = get_macro_snapshot()
    macro = fetch_all_macro()

    # Always-available FRED indicators
    unemp_pct = dual_percentile(snap["unemployment"], macro["unemployment"], True)

    cpi_series = macro["cpi"]
    cpi_yoy_s  = ((cpi_series / cpi_series.shift(12)) - 1) * 100
    cpi_pct    = dual_percentile(snap["cpi_yoy"], cpi_yoy_s.dropna(), True)

    # Optional scraped/computed indicators (may fail on Streamlit Cloud)
    cape_hist    = fetch_cape_history()
    _, buffett_hist = compute_buffett_indicator()
    cape_pct     = dual_percentile(snap["cape"],    cape_hist,    True)
    buffett_pct  = dual_percentile(snap["buffett"], buffett_hist, True)

    indicators = {
        "cape": {
            "label": "indicator_cape", "current": snap["cape"], "unit": "x",
            **cape_pct, "risk_score": cape_pct["pct_20yr"],
        },
        "buffett": {
            "label": "indicator_buffett", "current": snap["buffett"], "unit": "%",
            **buffett_pct, "risk_score": buffett_pct["pct_20yr"],
        },
        "unemployment": {
            "label": "Unemployment Rate", "current": snap["unemployment"], "unit": "%",
            **unemp_pct, "risk_score": unemp_pct["pct_20yr"],
        },
        "cpi_yoy": {
            "label": "CPI YoY", "current": snap["cpi_yoy"], "unit": "%",
            **cpi_pct, "risk_score": cpi_pct["pct_20yr"],
        },
    }

    layer_score = _safe_avg([v["risk_score"] for v in indicators.values()])
    return {"score": layer_score, "indicators": indicators}


@st.cache_data(ttl=CACHE_TTL_FAST)
def score_rates_layer() -> dict:
    """Yield curve, credit spreads, real rates."""
    snap  = get_macro_snapshot()
    macro = fetch_all_macro()

    def dp(val, hist, higher_risky):
        return dual_percentile(val, hist, higher_risky)

    # Yield curve: more inverted (lower) = more risky
    yc_10y2y = dp(snap["yield_10y2y"], macro["yield_curve_10y2y"], False)
    yc_10y3m = dp(snap["yield_10y3m"], macro["yield_curve_10y3m"], False)
    hy        = dp(snap["hy_spread"],  macro["hy_spread"],          True)
    ig        = dp(snap["ig_spread"],  macro["ig_spread"],          True)
    ry        = dp(snap["real_yield"], macro["real_yield_10y"],     True)

    indicators = {
        "yield_10y2y": {
            "label": "indicator_10y2y", "current": snap["yield_10y2y"], "unit": "%",
            **yc_10y2y, "risk_score": yc_10y2y["pct_20yr"],
        },
        "yield_10y3m": {
            "label": "indicator_10y3m", "current": snap["yield_10y3m"], "unit": "%",
            **yc_10y3m, "risk_score": yc_10y3m["pct_20yr"],
        },
        "hy_spread": {
            "label": "indicator_hy", "current": snap["hy_spread"], "unit": "bps",
            **hy, "risk_score": hy["pct_20yr"],
        },
        "ig_spread": {
            "label": "indicator_ig", "current": snap["ig_spread"], "unit": "bps",
            **ig, "risk_score": ig["pct_20yr"],
        },
        "real_yield": {
            "label": "indicator_realyield", "current": snap["real_yield"], "unit": "%",
            **ry, "risk_score": ry["pct_20yr"],
        },
    }
    layer_score = _safe_avg([v["risk_score"] for v in indicators.values()])
    return {"score": layer_score, "indicators": indicators}


@st.cache_data(ttl=CACHE_TTL_FAST)
def score_sentiment_layer() -> dict:
    """VIX, Fear & Greed, Put/Call ratio."""
    from src.data.market import get_put_call_ratio, fetch_vix

    vix_now   = fetch_vix()
    vix_hist  = fetch_vix_history()
    fg        = fetch_fear_greed()
    pc_ratio  = get_put_call_ratio()

    vix_pct = dual_percentile(vix_now, vix_hist, True)

    # Fear & Greed: LOW value = high fear = high risk
    fg_hist = pd.Series(dtype=float)  # no long history; use raw inversion
    fg_risk_score = max(0, 100 - fg["value"]) if not np.isnan(fg["value"]) else float("nan")

    indicators = {
        "vix": {
            "label": "indicator_vix", "current": vix_now, "unit": "",
            **vix_pct, "risk_score": vix_pct["pct_20yr"],
        },
        "fear_greed": {
            "label": "indicator_fg", "current": fg["value"], "unit": "/100",
            "pct_5yr": float("nan"), "pct_20yr": float("nan"),
            "risk_score": fg_risk_score,
            "extra": fg,
        },
        "put_call": {
            "label": "Put/Call Ratio", "current": pc_ratio, "unit": "",
            "pct_5yr": float("nan"), "pct_20yr": float("nan"),
            # high P/C = high fear (risk)
            "risk_score": min(100, max(0, (pc_ratio - 0.5) / 1.0 * 100)) if not np.isnan(pc_ratio) else float("nan"),
        },
    }
    layer_score = _safe_avg([v["risk_score"] for v in indicators.values()])
    return {"score": layer_score, "indicators": indicators}


@st.cache_data(ttl=CACHE_TTL_FAST)
def score_technical_layer(ticker: str = "SPY") -> dict:
    """RSI, distance from MA200, momentum, historical vol."""
    snap = get_technical_snapshot(ticker)
    if not snap:
        return {"score": float("nan"), "indicators": {}}

    hist = fetch_price_history_cached(ticker)

    from src.data.market import compute_rsi, compute_historical_volatility
    close  = hist["Close"]
    rsi_s  = compute_rsi(close)
    hvol_s = compute_historical_volatility(close)
    ma200_s = (close / close.rolling(200).mean() - 1) * 100
    mom_s   = (close / close.shift(252) - 1) * 100

    rsi_pct  = dual_percentile(snap["rsi"],          rsi_s.dropna(),  True)
    hvol_pct = dual_percentile(snap["hvol"],         hvol_s.dropna(), True)
    # Distance below MA200: riskier when price is far above (bubble) or far below (panic)
    # Use absolute distance from MA200 as risk
    ma200_abs = abs(snap["pct_above_ma200"])
    ma200_abs_s = ma200_s.abs().dropna()
    ma200_pct = dual_percentile(ma200_abs, ma200_abs_s, True)
    mom_pct  = dual_percentile(snap["momentum_12m"], mom_s.dropna(),  True)

    indicators = {
        "rsi": {
            "label": "indicator_rsi", "current": snap["rsi"], "unit": "",
            **rsi_pct, "risk_score": rsi_pct["pct_20yr"],
        },
        "ma200": {
            "label": "indicator_ma200",
            "current": snap["pct_above_ma200"], "unit": "%",
            **ma200_pct, "risk_score": ma200_pct["pct_20yr"],
        },
        "momentum": {
            "label": "indicator_momentum", "current": snap["momentum_12m"], "unit": "%",
            **mom_pct, "risk_score": mom_pct["pct_20yr"],
        },
        "hvol": {
            "label": "indicator_hvol", "current": snap["hvol"], "unit": "%",
            **hvol_pct, "risk_score": hvol_pct["pct_20yr"],
        },
    }
    layer_score = _safe_avg([v["risk_score"] for v in indicators.values()])
    return {"score": layer_score, "indicators": indicators}


@st.cache_data(ttl=CACHE_TTL_FAST)
def fetch_price_history_cached(ticker: str):
    from src.data.market import fetch_price_history
    return fetch_price_history(ticker, "20y")


def score_news_layer(ticker: str = "SPY") -> dict:
    """FinBERT news sentiment — not cached (runs on page load)."""
    from src.data.news import analyze_news_sentiment
    result = analyze_news_sentiment(ticker)
    # Convert: low sentiment score = high news risk
    news_risk = max(0, 100 - result["score"]) if not np.isnan(result.get("score", float("nan"))) else float("nan")
    return {
        "score": news_risk,
        "raw_sentiment": result,
        "indicators": {
            "news_sentiment": {
                "label": "news_sentiment",
                "current": result.get("score", float("nan")),
                "unit": "/100",
                "pct_5yr": float("nan"),
                "pct_20yr": float("nan"),
                "risk_score": news_risk,
            }
        }
    }


def compute_composite_score(ticker: str = "SPY") -> dict:
    """
    Run all layers and return composite risk score + per-layer breakdown.
    News layer excluded from equal-weight average (no historical percentile).
    """
    layers = {
        "macro":     score_macro_layer(ticker),
        "rates":     score_rates_layer(),
        "sentiment": score_sentiment_layer(),
        "technical": score_technical_layer(ticker),
    }
    news = score_news_layer(ticker)

    layer_scores = [v["score"] for v in layers.values() if not np.isnan(v["score"])]
    composite = _safe_avg(layer_scores)

    return {
        "composite":  round(composite, 1),
        "layers":     layers,
        "news":       news,
    }
