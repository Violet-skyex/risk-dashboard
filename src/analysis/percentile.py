"""Historical percentile computation utilities."""

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore


def percentile_of(current: float, history: pd.Series, higher_is_riskier: bool = True) -> float:
    """
    Returns 0-100 risk percentile.
    higher_is_riskier=True  → high current value = high risk percentile (e.g. VIX, CAPE, spreads)
    higher_is_riskier=False → low current value = high risk percentile (e.g. yield curve slope, which is riskier inverted)
    """
    if np.isnan(current) or len(history) < 10:
        return float("nan")
    clean = history.dropna().values
    raw = percentileofscore(clean, current, kind="rank")
    return round(raw if higher_is_riskier else 100 - raw, 1)


def dual_percentile(current: float, history: pd.Series, higher_is_riskier: bool = True) -> dict:
    """Returns both 5yr and 20yr percentiles."""
    nan_result = {"pct_5yr": float("nan"), "pct_20yr": float("nan")}
    if not isinstance(history.index, pd.DatetimeIndex) or len(history) < 10:
        return nan_result
    # Strip timezone so comparison with Timestamp.today() always works
    hist = history.copy()
    if hist.index.tz is not None:
        hist.index = hist.index.tz_localize(None)
    now = pd.Timestamp.today()
    h5  = hist[hist.index >= now - pd.DateOffset(years=5)]
    h20 = hist[hist.index >= now - pd.DateOffset(years=20)]
    return {
        "pct_5yr":  percentile_of(current, h5,  higher_is_riskier),
        "pct_20yr": percentile_of(current, h20, higher_is_riskier),
    }


def normalize_series(series: pd.Series) -> pd.Series:
    """Min-max normalize to [0, 1] for vector similarity."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)


def rolling_percentile(series: pd.Series, window: int = None) -> pd.Series:
    """
    For each date, compute percentile within entire available history up to that date.
    window=None → expanding (uses all past data).
    """
    if window:
        return series.rolling(window).apply(
            lambda x: percentileofscore(x[:-1], x[-1], kind="rank") if len(x) > 1 else 50,
            raw=True
        )
    result = pd.Series(index=series.index, dtype=float)
    arr = series.dropna().values
    for i, val in enumerate(arr):
        if i == 0:
            result.iloc[i] = 50.0
        else:
            result.iloc[i] = percentileofscore(arr[:i], val, kind="rank")
    return result
