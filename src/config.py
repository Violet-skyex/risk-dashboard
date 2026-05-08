import streamlit as st

def _get_secret(key: str) -> str:
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        st.error(
            f"Missing secret: `{key}`. "
            "Go to **Manage app → Settings → Secrets** and add your API keys. "
            "See the README for the required format.",
            icon="🔑",
        )
        st.stop()

FRED_API_KEY = _get_secret("FRED_API_KEY")
NEWS_API_KEY = _get_secret("NEWS_API_KEY")

DEFAULT_TICKERS = ["SPY", "QQQ"]

FRED_SERIES = {
    "yield_curve_10y2y": "T10Y2Y",
    "yield_curve_10y3m": "T10Y3M",
    "hy_spread":         "BAMLH0A0HYM2",
    "ig_spread":         "BAMLC0A0CM",
    "fed_funds":         "FEDFUNDS",
    "real_yield_10y":    "DFII10",
    "vix_history":       "VIXCLS",
    "dollar_index":      "DTWEXBGS",
    "unemployment":      "UNRATE",
    "cpi":               "CPIAUCSL",
    "wilshire5000":      "WILL5000PR",
    "gdp":               "GDP",
}

LAYER_NAMES_EN = {
    "macro":     "Macro / Valuation",
    "rates":     "Rates & Credit",
    "sentiment": "Market Sentiment",
    "technical": "Technical / Momentum",
    "news":      "News Sentiment",
}
LAYER_NAMES_CN = {
    "macro":     "宏观 / 估值",
    "rates":     "利率 & 信用",
    "sentiment": "市场情绪",
    "technical": "技术面 / 动量",
    "news":      "新闻情绪",
}

RISK_COLORS = {
    "low":    "#2ecc71",
    "medium": "#f1c40f",
    "high":   "#e67e22",
    "extreme":"#e74c3c",
}

def risk_color(score: float) -> str:
    if score < 25:   return RISK_COLORS["low"]
    if score < 50:   return RISK_COLORS["medium"]
    if score < 75:   return RISK_COLORS["high"]
    return RISK_COLORS["extreme"]

def risk_label(score: float, lang: str = "EN") -> str:
    if lang == "CN":
        if score < 25:  return "低风险"
        if score < 50:  return "中等风险"
        if score < 75:  return "偏高风险"
        return "极高风险"
    else:
        if score < 25:  return "Low Risk"
        if score < 50:  return "Moderate Risk"
        if score < 75:  return "Elevated Risk"
        return "Extreme Risk"

CACHE_TTL_FAST  = 300       # 5 min — prices, VIX
CACHE_TTL_DAILY = 86400     # 24 hr — macro, FRED
NEWS_COUNT      = 20
HISTORY_YEARS   = 20
