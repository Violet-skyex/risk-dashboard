"""Earnings risk module for individual tickers."""

import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from src.config import CACHE_TTL_DAILY


@st.cache_data(ttl=CACHE_TTL_DAILY)
def get_earnings_risk(ticker: str) -> dict:
    if ticker in ("SPY", "QQQ", "^SPX", "^GSPC"):
        return {"is_index": True}

    try:
        tk = yf.Ticker(ticker)
        cal = tk.calendar

        # Next earnings date
        next_date = None
        if cal is not None and not cal.empty:
            if hasattr(cal, "T"):
                cal = cal.T
            for col in ["Earnings Date", "Earnings High", "Earnings Low"]:
                if col in cal.columns:
                    val = cal[col].iloc[0]
                    if pd.notna(val):
                        next_date = pd.Timestamp(val)
                        break

        days_to_earnings = int((next_date - pd.Timestamp.today()).days) if next_date else None

        # Historical earnings reactions from price history
        hist = tk.history(period="5y", auto_adjust=True)
        earnings_history = tk.earnings_history if hasattr(tk, "earnings_history") else None
        avg_reaction, reactions = _compute_reactions(ticker, hist)

        # Implied move from options (nearest ATM straddle ~45d out)
        implied_move = _get_implied_move(ticker)

        # Analyst revision trend (last 30 days)
        revision_trend = _get_revision_trend(tk)

        return {
            "is_index":       False,
            "next_date":      next_date.strftime("%Y-%m-%d") if next_date else "N/A",
            "days_to":        days_to_earnings,
            "implied_move":   implied_move,
            "avg_reaction":   avg_reaction,
            "reactions":      reactions,
            "revision_trend": revision_trend,
        }
    except Exception as e:
        return {"is_index": False, "error": str(e)}


def _compute_reactions(ticker: str, hist: pd.DataFrame) -> tuple:
    """Estimate earnings reaction from large single-day moves (proxy)."""
    if hist.empty or len(hist) < 20:
        return float("nan"), []

    daily_ret = hist["Close"].pct_change().dropna() * 100
    # Large moves (abs > 3%) as proxy for earnings days
    big_moves = daily_ret[daily_ret.abs() > 3].tail(8)
    reactions = [round(v, 2) for v in big_moves.values]
    avg = round(float(big_moves.abs().mean()), 2) if len(big_moves) else float("nan")
    return avg, reactions


def _get_implied_move(ticker: str) -> float:
    """ATM straddle price as % of underlying ~ implied earnings move."""
    try:
        tk = yf.Ticker(ticker)
        price = tk.fast_info.last_price
        exps = tk.options
        if not exps:
            return float("nan")

        today = pd.Timestamp.today()
        target = today + pd.Timedelta(days=45)
        exp = min(exps, key=lambda e: abs((pd.Timestamp(e) - target).days))
        chain = tk.option_chain(exp)

        # Find ATM strike
        strikes = chain.calls["strike"].values
        atm_strike = strikes[np.argmin(np.abs(strikes - price))]

        call_row = chain.calls[chain.calls["strike"] == atm_strike]
        put_row  = chain.puts[chain.puts["strike"] == atm_strike]

        if call_row.empty or put_row.empty:
            return float("nan")

        call_mid = (call_row["bid"].values[0] + call_row["ask"].values[0]) / 2
        put_mid  = (put_row["bid"].values[0]  + put_row["ask"].values[0])  / 2
        straddle = call_mid + put_mid

        return round(straddle / price * 100, 2)
    except Exception:
        return float("nan")


def _get_revision_trend(tk) -> str:
    """Check if analyst consensus has trended up or down."""
    try:
        rec = tk.recommendations
        if rec is None or rec.empty:
            return "N/A"
        recent = rec.tail(10)
        buy_count  = recent["To Grade"].str.contains("Buy|Outperform|Overweight", case=False, na=False).sum()
        sell_count = recent["To Grade"].str.contains("Sell|Underperform|Underweight", case=False, na=False).sum()
        if buy_count > sell_count * 2:
            return "Positive ↑"
        elif sell_count > buy_count * 2:
            return "Negative ↓"
        else:
            return "Neutral →"
    except Exception:
        return "N/A"
