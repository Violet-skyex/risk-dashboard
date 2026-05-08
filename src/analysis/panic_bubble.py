"""
Panic vs Bubble classifier.
Returns bubble_score and panic_score (0-100 each).
"""

import numpy as np
import streamlit as st
from src.config import CACHE_TTL_FAST


@st.cache_data(ttl=CACHE_TTL_FAST)
def classify_panic_bubble(ticker: str = "SPY") -> dict:
    from src.data.macro import get_macro_snapshot
    from src.data.market import fetch_vix, get_technical_snapshot
    from src.data.fear_greed import fetch_fear_greed

    snap  = get_macro_snapshot()
    tech  = get_technical_snapshot(ticker)
    fg    = fetch_fear_greed()
    vix   = fetch_vix()

    bubble_signals = []
    panic_signals  = []

    # --- BUBBLE SIGNALS ---

    # CAPE: >25 moderate bubble, >35 extreme bubble
    if not np.isnan(snap["cape"]):
        cape_b = np.clip((snap["cape"] - 15) / (40 - 15) * 100, 0, 100)
        bubble_signals.append(cape_b)

    # Buffett Indicator: >130% moderate, >200% extreme
    if not np.isnan(snap["buffett"]):
        buff_b = np.clip((snap["buffett"] - 80) / (200 - 80) * 100, 0, 100)
        bubble_signals.append(buff_b)

    # VIX very low + market near high = complacency (bubble)
    if not np.isnan(vix) and tech:
        if vix < 15 and tech.get("distance_from_52w_high", -100) > -5:
            bubble_signals.append(80)
        elif vix < 20:
            bubble_signals.append(40)
        else:
            bubble_signals.append(0)

    # HY spreads very tight = bubble/complacency
    if not np.isnan(snap["hy_spread"]):
        # Tight spreads (low) = bubble; 200bps=very tight, 800bps=crisis
        hy_b = np.clip((400 - snap["hy_spread"]) / (400 - 200) * 100, 0, 100)
        bubble_signals.append(hy_b)

    # Fear & Greed extreme greed
    if not np.isnan(fg["value"]):
        fg_b = np.clip((fg["value"] - 50) / 50 * 100, 0, 100)
        bubble_signals.append(fg_b)

    # 12M momentum very strong = overbought/bubble-like
    if tech and not np.isnan(tech.get("momentum_12m", float("nan"))):
        mom = tech["momentum_12m"]
        mom_b = np.clip((mom - 10) / 50 * 100, 0, 100)
        bubble_signals.append(mom_b)

    # --- PANIC SIGNALS ---

    # VIX spike
    if not np.isnan(vix):
        vix_p = np.clip((vix - 15) / (80 - 15) * 100, 0, 100)
        panic_signals.append(vix_p)

    # HY spread very wide = credit stress = panic
    if not np.isnan(snap["hy_spread"]):
        hy_p = np.clip((snap["hy_spread"] - 300) / (1200 - 300) * 100, 0, 100)
        panic_signals.append(hy_p)

    # Yield curve extremely inverted
    if not np.isnan(snap["yield_10y2y"]):
        yc_p = np.clip((-snap["yield_10y2y"] - 0) / 3.0 * 100, 0, 100)
        panic_signals.append(yc_p)

    # RSI deeply oversold
    if tech and not np.isnan(tech.get("rsi", float("nan"))):
        rsi = tech["rsi"]
        rsi_p = np.clip((40 - rsi) / 40 * 100, 0, 100)
        panic_signals.append(rsi_p)

    # Price far below 200 MA = panic
    if tech and not np.isnan(tech.get("pct_above_ma200", float("nan"))):
        below_ma = -tech["pct_above_ma200"]
        ma_p = np.clip((below_ma - 0) / 30 * 100, 0, 100)
        panic_signals.append(ma_p)

    # Fear & Greed extreme fear
    if not np.isnan(fg["value"]):
        fg_p = np.clip((50 - fg["value"]) / 50 * 100, 0, 100)
        panic_signals.append(fg_p)

    bubble_score = float(np.mean(bubble_signals)) if bubble_signals else 50.0
    panic_score  = float(np.mean(panic_signals))  if panic_signals  else 50.0

    # Normalize so they sum to meaningful comparison
    bubble_score = round(min(100, max(0, bubble_score)), 1)
    panic_score  = round(min(100, max(0, panic_score)),  1)

    if bubble_score > 60 and panic_score < 40:
        character = "bubble"
    elif panic_score > 60 and bubble_score < 40:
        character = "panic"
    elif bubble_score > 50 and panic_score > 50:
        character = "volatile"
    else:
        character = "neutral"

    return {
        "bubble_score": bubble_score,
        "panic_score":  panic_score,
        "character":    character,
    }
