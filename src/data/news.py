"""NewsAPI fetcher + FinBERT sentiment — cached per session."""

import streamlit as st
import requests
import numpy as np
from src.config import NEWS_API_KEY, NEWS_COUNT, CACHE_TTL_FAST

RISK_KEYWORDS = [
    "recession", "crash", "default", "contagion", "tariff", "war",
    "rate hike", "inflation", "layoffs", "bankruptcy", "debt ceiling",
    "bank failure", "credit crunch", "liquidity crisis", "sanctions",
    "geopolitical", "yield surge", "earnings miss", "guidance cut",
    "margin call", "deleveraging", "systemic risk",
]


@st.cache_resource
def load_finbert():
    from transformers import pipeline
    return pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        top_k=None,
        device=-1,
    )


@st.cache_data(ttl=CACHE_TTL_FAST)
def fetch_news(query: str = "stock market economy fed") -> list[dict]:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q":        query,
        "language": "en",
        "sortBy":   "publishedAt",
        "pageSize": NEWS_COUNT,
        "apiKey":   NEWS_API_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        articles = r.json().get("articles", [])
        return [
            {
                "title":       a.get("title", ""),
                "description": a.get("description", ""),
                "publishedAt": a.get("publishedAt", ""),
                "source":      a.get("source", {}).get("name", ""),
                "url":         a.get("url", ""),
            }
            for a in articles
            if a.get("title")
        ]
    except Exception:
        return []


def analyze_news_sentiment(ticker: str = "SPY") -> dict:
    """Run FinBERT on fetched headlines. Returns sentiment summary."""
    query = f"{ticker} stock market economy federal reserve" if ticker not in ("SPY", "QQQ") \
            else "stock market economy federal reserve interest rates"
    articles = fetch_news(query)
    if not articles:
        return {
            "score":        float("nan"),
            "positive_pct": float("nan"),
            "negative_pct": float("nan"),
            "neutral_pct":  float("nan"),
            "keywords":     [],
            "articles":     [],
        }

    finbert = load_finbert()
    texts = [
        (a["title"] + ". " + (a["description"] or ""))[:512]
        for a in articles
    ]

    results = finbert(texts, batch_size=8, truncation=True)

    pos = neg = neu = 0
    for r in results:
        scores = {item["label"]: item["score"] for item in r}
        pos += scores.get("positive", 0)
        neg += scores.get("negative", 0)
        neu += scores.get("neutral",  0)

    n = len(results)
    pos_pct = pos / n * 100
    neg_pct = neg / n * 100
    neu_pct = neu / n * 100

    # Sentiment score: 0 = very negative, 100 = very positive
    # Inverted for risk: high negative → high risk
    sentiment_score = (pos_pct - neg_pct + 100) / 2  # 0-100 scale

    # Keyword scan
    all_text = " ".join(texts).lower()
    found_keywords = [kw for kw in RISK_KEYWORDS if kw in all_text]

    return {
        "score":        round(sentiment_score, 1),
        "positive_pct": round(pos_pct, 1),
        "negative_pct": round(neg_pct, 1),
        "neutral_pct":  round(neu_pct, 1),
        "keywords":     found_keywords,
        "articles":     articles[:10],
    }
