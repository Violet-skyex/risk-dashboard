"""CNN Fear & Greed Index scraper — fast-cached."""

import requests
import streamlit as st
from src.config import CACHE_TTL_FAST


@st.cache_data(ttl=CACHE_TTL_FAST)
def fetch_fear_greed() -> dict:
    """
    Returns dict with keys: value (0-100), label, previous_close, prev_week, prev_month.
    Falls back to CNN API endpoint, then scraping.
    """
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer":    "https://edition.cnn.com/",
        }
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        fg = data["fear_and_greed"]
        return {
            "value":          round(float(fg["score"]), 1),
            "label":          fg["rating"].replace("_", " ").title(),
            "previous_close": round(float(fg["previous_close"]), 1),
            "prev_week":      round(float(fg["previous_1_week"]), 1),
            "prev_month":     round(float(fg["previous_1_month"]), 1),
        }
    except Exception:
        return {
            "value":          float("nan"),
            "label":          "N/A",
            "previous_close": float("nan"),
            "prev_week":      float("nan"),
            "prev_month":     float("nan"),
        }
