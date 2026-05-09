"""
Market Risk Dashboard — main Streamlit entrypoint.
Run: streamlit run app.py
"""

import streamlit as st
import numpy as np

st.set_page_config(
    page_title="Market Risk Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── light theme CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stExpander    { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
  .section-title { color: #2563eb; font-weight: 700; font-size: 1.05em;
                   border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; margin: 16px 0 10px 0; }
  .divider       { border-top: 1px solid #e2e8f0; margin: 20px 0; }
</style>
""", unsafe_allow_html=True)

from src.i18n import t

# ── session state defaults ───────────────────────────────────────────────────
if "lang"   not in st.session_state: st.session_state.lang   = "EN"
if "ticker" not in st.session_state: st.session_state.ticker = ""

# ── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    col_title, col_lang = st.columns([3, 1])
    with col_lang:
        if st.button(t("lang_toggle", st.session_state.lang), use_container_width=True):
            st.session_state.lang = "CN" if st.session_state.lang == "EN" else "EN"
            st.rerun()

    lang = st.session_state.lang

    st.markdown(f"## {t('title', lang)}")
    st.caption(t("subtitle", lang))
    st.markdown("---")

    ticker_input = st.text_input(
        t("ticker_input", lang),
        value=st.session_state.ticker,
        placeholder=t("ticker_placeholder", lang),
        key="ticker_box",
    ).upper().strip()
    st.session_state.ticker = ticker_input

    st.markdown("---")
    st.caption("Data refreshes on every page load.\n\nFast data: ~5 min cache\nMacro: daily cache")

lang   = st.session_state.lang
ticker = st.session_state.ticker

tickers_to_show = ["SPY", "QQQ"]
if ticker and ticker not in tickers_to_show:
    tickers_to_show.append(ticker)

# ── page title ───────────────────────────────────────────────────────────────
st.markdown(
    f"<h2 style='margin-bottom:0'>{t('title', lang)}</h2>"
    f"<p style='color:#888;margin-top:2px'>{t('subtitle', lang)}</p>",
    unsafe_allow_html=True,
)

# ── load all data ─────────────────────────────────────────────────────────────
from src.analysis.scoring import compute_composite_score
from src.analysis.panic_bubble import classify_panic_bubble
from src.analysis.similarity import find_historical_scenarios
from src.analysis.earnings import get_earnings_risk
from src.ui.gauge import render_risk_gauge, render_panic_bubble_chart, render_drawdown_distribution
from src.ui.cards import render_layer_card, render_news_card
from src.ui.scenarios import render_scenarios
from src.ui.hedges import render_hedge_tools

with st.spinner(t("loading", lang)):
    scores = {}
    for tk in tickers_to_show:
        scores[tk] = compute_composite_score(tk)

    # Panic/Bubble: one per ticker
    pb = {tk: classify_panic_bubble(tk) for tk in tickers_to_show}

    scenarios = find_historical_scenarios("SPY", top_n=5)

    earnings = {}
    if ticker and ticker not in ("SPY", "QQQ"):
        earnings[ticker] = get_earnings_risk(ticker)

char_map_en = {"bubble": "Bubble / Euphoria", "panic": "Panic / Fear",
               "volatile": "Volatile", "neutral": "Neutral"}
char_map_cn = {"bubble": "泡沫 / 狂热", "panic": "恐慌 / 恐惧",
               "volatile": "双向高压", "neutral": "中性"}

# ═══════════════════════════════════════════════════════════════════
# SECTION 1 — RISK GAUGES
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"<div class='section-title'>{t('composite_score', lang)}</div>", unsafe_allow_html=True)

gauge_cols = st.columns(len(tickers_to_show))
for i, tk in enumerate(tickers_to_show):
    with gauge_cols[i]:
        score = scores[tk]["composite"]
        fig = render_risk_gauge(score, tk, lang)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════
# SECTION 2 — PANIC / BUBBLE POSITIONING (one per ticker)
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"<div class='section-title'>{t('panic_bubble', lang)}</div>", unsafe_allow_html=True)

pb_cols = st.columns(len(tickers_to_show))
for i, tk in enumerate(tickers_to_show):
    with pb_cols[i]:
        p = pb[tk]
        bscore = p["bubble_score"]
        pscore = p["panic_score"]
        char_label = (char_map_cn if lang == "CN" else char_map_en).get(p["character"], p["character"])
        st.markdown(f"**{tk}** — {char_label}")
        c1, c2 = st.columns(2)
        c1.metric(t("bubble_score", lang), f"{bscore:.0f}")
        c2.metric(t("panic_score",  lang), f"{pscore:.0f}")
        pb_fig = render_panic_bubble_chart(bscore, pscore, lang)
        st.plotly_chart(pb_fig, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════
# SECTION 3 — FACTOR BREAKDOWN (columns per ticker)
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"<div class='section-title'>{t('factor_breakdown', lang)}</div>", unsafe_allow_html=True)

factor_cols = st.columns(len(tickers_to_show))
layer_order = ["macro", "rates", "sentiment", "technical"]

for i, tk in enumerate(tickers_to_show):
    with factor_cols[i]:
        st.markdown(f"**{tk}**")
        result = scores[tk]
        for lk in layer_order:
            layer_data = result["layers"].get(lk, {})
            render_layer_card(lk, layer_data, lang)
        render_news_card(result["news"], lang)

        # Earnings risk (only for individual stocks)
        if tk in earnings and not earnings[tk].get("is_index"):
            st.markdown("---")
            st.markdown(f"**{t('earnings_risk', lang)}**")
            er = earnings[tk]
            if "error" not in er:
                e1, e2 = st.columns(2)
                e1.metric(t("days_to_earn", lang),   f"{er.get('days_to', 'N/A')}d")
                e2.metric(t("implied_move",  lang),  f"±{er.get('implied_move', float('nan')):.1f}%"
                          if er.get('implied_move') else "N/A")
                e1.metric(t("hist_earn_move", lang), f"±{er.get('avg_reaction', float('nan')):.1f}%"
                          if er.get('avg_reaction') else "N/A")
                e2.metric(t("revision_trend", lang), er.get("revision_trend", "N/A"))

# ═══════════════════════════════════════════════════════════════════
# SECTION 4 — HISTORICAL SCENARIOS
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"<div class='section-title'>{t('scenarios', lang)}</div>", unsafe_allow_html=True)

render_scenarios(scenarios, lang)

# Drawdown distribution chart
if scenarios:
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-title'>{t('drawdown_dist', lang)}</div>", unsafe_allow_html=True)
    dd_fig = render_drawdown_distribution(scenarios, lang)
    st.plotly_chart(dd_fig, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════
# SECTION 5 — HEDGING INSTRUMENTS
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"<div class='section-title'>{t('hedge_tools', lang)}</div>", unsafe_allow_html=True)
render_hedge_tools(ticker if ticker else "SPY", lang)

# ── footer ───────────────────────────────────────────────────────────────────
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#555;font-size:0.75em;text-align:center'>"
    "For informational purposes only. Not investment advice. "
    "Data sources: FRED, Yahoo Finance, NewsAPI, CNN Fear &amp; Greed, multpl.com"
    "</p>",
    unsafe_allow_html=True,
)
