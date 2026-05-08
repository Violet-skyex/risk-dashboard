"""yfinance market data — fast-cached (5 min)."""

import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from src.config import CACHE_TTL_FAST, CACHE_TTL_DAILY


@st.cache_data(ttl=CACHE_TTL_FAST)
def fetch_price_history(ticker: str, period: str = "20y") -> pd.DataFrame:
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period, auto_adjust=True)
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])


@st.cache_data(ttl=CACHE_TTL_FAST)
def fetch_current_price(ticker: str) -> float:
    tk = yf.Ticker(ticker)
    try:
        info = tk.fast_info
        return float(info.last_price)
    except Exception:
        hist = fetch_price_history(ticker, "5d")
        return float(hist["Close"].iloc[-1]) if len(hist) else float("nan")


@st.cache_data(ttl=CACHE_TTL_FAST)
def fetch_vix() -> float:
    return fetch_current_price("^VIX")


@st.cache_data(ttl=CACHE_TTL_FAST)
def fetch_vix_history(period: str = "20y") -> pd.Series:
    df = fetch_price_history("^VIX", period)
    return df["Close"]


def compute_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def compute_historical_volatility(prices: pd.Series, window: int = 30) -> pd.Series:
    log_ret = np.log(prices / prices.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(252) * 100


@st.cache_data(ttl=CACHE_TTL_FAST)
def get_technical_snapshot(ticker: str) -> dict:
    hist = fetch_price_history(ticker, "20y")
    close = hist["Close"]
    volume = hist["Volume"]

    if len(close) < 200:
        return {}

    ma50   = close.rolling(50).mean().iloc[-1]
    ma200  = close.rolling(200).mean().iloc[-1]
    price  = close.iloc[-1]
    rsi    = compute_rsi(close).iloc[-1]
    hvol   = compute_historical_volatility(close).iloc[-1]
    momentum_12m = (price / close.iloc[-252] - 1) * 100 if len(close) >= 252 else float("nan")
    vol_ratio = volume.iloc[-20:].mean() / volume.iloc[-252:].mean() if len(volume) >= 252 else float("nan")
    distance_from_high = (price / close.rolling(252).max().iloc[-1] - 1) * 100

    return {
        "price":               price,
        "ma50":                ma50,
        "ma200":               ma200,
        "pct_above_ma200":     (price / ma200 - 1) * 100,
        "rsi":                 rsi,
        "hvol":                hvol,
        "momentum_12m":        momentum_12m,
        "vol_ratio_20_252":    vol_ratio,
        "distance_from_52w_high": distance_from_high,
    }


@st.cache_data(ttl=CACHE_TTL_FAST)
def get_technical_history(ticker: str) -> pd.DataFrame:
    """Returns daily DataFrame of technical indicators for similarity engine."""
    hist = fetch_price_history(ticker, "20y")
    close = hist["Close"]

    df = pd.DataFrame(index=close.index)
    df["rsi"]         = compute_rsi(close)
    df["hvol"]        = compute_historical_volatility(close)
    df["pct_ma200"]   = (close / close.rolling(200).mean() - 1) * 100
    df["momentum_12m"]= (close / close.shift(252) - 1) * 100
    df["distance_52w"]= (close / close.rolling(252).max() - 1) * 100
    return df.dropna()


@st.cache_data(ttl=CACHE_TTL_FAST)
def get_put_call_ratio() -> float:
    """Estimate P/C ratio from SPY options chain (30-60d expiry)."""
    try:
        spy = yf.Ticker("SPY")
        exps = spy.options
        if not exps:
            return float("nan")
        # Pick expiry ~45 days out
        today = pd.Timestamp.today()
        target = today + pd.Timedelta(days=45)
        exp = min(exps, key=lambda e: abs((pd.Timestamp(e) - target).days))
        chain = spy.option_chain(exp)
        put_vol  = chain.puts["volume"].sum()
        call_vol = chain.calls["volume"].sum()
        if call_vol == 0:
            return float("nan")
        return round(put_vol / call_vol, 3)
    except Exception:
        return float("nan")


@st.cache_data(ttl=CACHE_TTL_DAILY)
def get_fundamentals(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info
        return {
            "pe_trailing":    info.get("trailingPE"),
            "pe_forward":     info.get("forwardPE"),
            "pb":             info.get("priceToBook"),
            "ps":             info.get("priceToSalesTrailing12Months"),
            "market_cap":     info.get("marketCap"),
            "short_ratio":    info.get("shortRatio"),
            "short_pct_float":info.get("shortPercentOfFloat"),
            "beta":           info.get("beta"),
            "sector":         info.get("sector"),
            "industry":       info.get("industry"),
        }
    except Exception:
        return {}


@st.cache_data(ttl=CACHE_TTL_DAILY)
def get_insider_activity(ticker: str) -> dict:
    try:
        tk = yf.Ticker(ticker)
        transactions = tk.insider_transactions
        if transactions is None or transactions.empty:
            return {"net_shares_30d": float("nan"), "summary": "N/A"}
        recent = transactions[transactions.index <= pd.Timestamp.today()]
        recent = recent.head(20)
        buys  = recent[recent["Text"].str.contains("Purchase|Buy", case=False, na=False)]["Shares"].sum()
        sells = recent[recent["Text"].str.contains("Sale|Sell", case=False, na=False)]["Shares"].sum()
        return {"net_shares_30d": int(buys - sells), "buy_count": int(buys > 0), "sell_count": int(sells > 0)}
    except Exception:
        return {"net_shares_30d": float("nan")}
