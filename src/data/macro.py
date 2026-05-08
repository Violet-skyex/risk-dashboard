"""FRED macro data fetcher — daily-cached."""

import pandas as pd
import numpy as np
import streamlit as st
from fredapi import Fred
from datetime import datetime, timedelta
from src.config import FRED_API_KEY, FRED_SERIES, CACHE_TTL_DAILY


@st.cache_data(ttl=CACHE_TTL_DAILY)
def fetch_fred_series(series_id: str, years: int = 22) -> pd.Series:
    fred = Fred(api_key=FRED_API_KEY)
    start = datetime.today() - timedelta(days=365 * years)
    try:
        data = fred.get_series(series_id, observation_start=start)
        return data.dropna()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=CACHE_TTL_DAILY)
def fetch_all_macro() -> dict:
    """Return dict of {name: pd.Series} for all FRED series."""
    result = {}
    for name, sid in FRED_SERIES.items():
        result[name] = fetch_fred_series(sid)
    return result


@st.cache_data(ttl=CACHE_TTL_DAILY)
def fetch_cape() -> float:
    """Scrape current Shiller CAPE from multpl.com."""
    import requests
    from bs4 import BeautifulSoup
    try:
        r = requests.get("https://www.multpl.com/shiller-pe", timeout=8,
                         headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        val = soup.find("div", {"id": "current-value"})
        return float(val.text.strip().replace(",", ""))
    except Exception:
        return float("nan")


@st.cache_data(ttl=CACHE_TTL_DAILY)
def fetch_cape_history(years: int = 22) -> pd.Series:
    """Scrape CAPE table from multpl.com for historical data."""
    import requests
    try:
        tables = pd.read_html("https://www.multpl.com/shiller-pe/table/by-month")
        df = tables[0]
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"].astype(str).str.replace(",", ""), errors="coerce")
        df = df.dropna().set_index("date").sort_index()
        cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
        return df["value"][df.index >= cutoff]
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=CACHE_TTL_DAILY)
def compute_buffett_indicator() -> tuple[float, pd.Series]:
    """Returns (current_value_pct, historical_series)."""
    wilshire = fetch_fred_series("WILL5000PR")
    gdp = fetch_fred_series("GDP")

    # GDP is quarterly — forward fill to daily
    gdp_daily = gdp.resample("D").interpolate(method="linear")

    # Align
    combined = pd.concat([wilshire, gdp_daily], axis=1, join="inner")
    combined.columns = ["wilshire", "gdp"]
    combined = combined.dropna()

    buffett = (combined["wilshire"] / combined["gdp"]) * 100
    current = float(buffett.iloc[-1]) if len(buffett) else float("nan")
    return current, buffett


@st.cache_data(ttl=CACHE_TTL_DAILY)
def get_macro_snapshot() -> dict:
    """Assembled current-value snapshot for all macro indicators."""
    macro_data = fetch_all_macro()

    def last(series: pd.Series):
        return float(series.iloc[-1]) if len(series) else float("nan")

    cape_current = fetch_cape()
    buffett_current, _ = compute_buffett_indicator()

    return {
        "cape":          cape_current,
        "buffett":       buffett_current,
        "yield_10y2y":   last(macro_data["yield_curve_10y2y"]),
        "yield_10y3m":   last(macro_data["yield_curve_10y3m"]),
        "hy_spread":     last(macro_data["hy_spread"]),
        "ig_spread":     last(macro_data["ig_spread"]),
        "fed_funds":     last(macro_data["fed_funds"]),
        "real_yield":    last(macro_data["real_yield_10y"]),
        "vix_history":   last(macro_data["vix_history"]),
        "dollar_index":  last(macro_data["dollar_index"]),
        "unemployment":  last(macro_data["unemployment"]),
        "cpi_yoy":       _cpi_yoy(macro_data["cpi"]),
    }


def _cpi_yoy(cpi: pd.Series) -> float:
    if len(cpi) < 13:
        return float("nan")
    return float((cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100)
