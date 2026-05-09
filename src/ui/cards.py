"""Factor card and indicator row rendering."""

import streamlit as st
import numpy as np
from src.i18n import t
from src.config import risk_color


def _pct_badge(pct: float) -> str:
    if np.isnan(pct):
        return "<span style='color:#94a3b8'>N/A</span>"
    if pct >= 80:
        color = "#dc2626"
    elif pct >= 60:
        color = "#ea580c"
    elif pct >= 40:
        color = "#ca8a04"
    else:
        color = "#16a34a"
    return f"<span style='color:{color};font-weight:700'>{pct:.0f}%</span>"


def _score_bar(score: float, width_px: int = 120) -> str:
    if np.isnan(score):
        return ""
    color = risk_color(score)
    filled = int(score / 100 * width_px)
    return (
        f"<div style='background:#e2e8f0;border-radius:4px;width:{width_px}px;"
        f"height:8px;display:inline-block'>"
        f"<div style='background:{color};width:{filled}px;height:8px;border-radius:4px'>"
        f"</div></div>"
    )


def render_layer_card(layer_key: str, layer_data: dict, lang: str = "EN"):
    layer_name = t(f"layer_{layer_key}", lang)
    score = layer_data.get("score", float("nan"))
    indicators = layer_data.get("indicators", {})

    color = risk_color(score) if not np.isnan(score) else "#94a3b8"
    score_str = f"{score:.0f}" if not np.isnan(score) else "N/A"

    header_html = (
        f"<div style='display:flex;align-items:center;justify-content:space-between;"
        f"padding:8px 0'>"
        f"<span style='font-weight:700;font-size:1em;color:#1e293b'>{layer_name}</span>"
        f"<span style='color:{color};font-weight:800;font-size:1.1em'>{score_str}</span>"
        f"</div>"
    )
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown(_score_bar(score), unsafe_allow_html=True)

    with st.expander(t("factor_breakdown", lang), expanded=False):
        _render_indicator_table(indicators, lang)


def _render_indicator_table(indicators: dict, lang: str):
    pct_5yr  = t("pct_5yr",    lang)
    pct_20yr = t("pct_20yr",   lang)
    cur_lbl  = t("current_val", lang)

    header = (
        f"<table style='width:100%;border-collapse:collapse;font-size:0.82em'>"
        f"<thead><tr style='color:#64748b;border-bottom:1px solid #e2e8f0'>"
        f"<th style='text-align:left;padding:4px'>Indicator</th>"
        f"<th style='text-align:right;padding:4px'>{cur_lbl}</th>"
        f"<th style='text-align:right;padding:4px'>{pct_5yr}</th>"
        f"<th style='text-align:right;padding:4px'>{pct_20yr}</th>"
        f"</tr></thead><tbody>"
    )
    rows = ""
    for key, ind in indicators.items():
        label   = t(ind.get("label", key), lang) if ind.get("label") else key
        current = ind.get("current", float("nan"))
        unit    = ind.get("unit", "")
        p5      = ind.get("pct_5yr",  float("nan"))
        p20     = ind.get("pct_20yr", float("nan"))

        try:
            cur_str = f"{float(current):.2f}{unit}" if current is not None and not np.isnan(float(current)) else "N/A"
        except (TypeError, ValueError):
            cur_str = "N/A"

        rows += (
            f"<tr style='border-bottom:1px solid #f1f5f9'>"
            f"<td style='padding:5px 4px;color:#1e293b'>{label}</td>"
            f"<td style='text-align:right;padding:5px 4px;color:#0f766e;font-weight:600'>{cur_str}</td>"
            f"<td style='text-align:right;padding:5px 4px'>{_pct_badge(p5)}</td>"
            f"<td style='text-align:right;padding:5px 4px'>{_pct_badge(p20)}</td>"
            f"</tr>"
        )

    st.markdown(header + rows + "</tbody></table>", unsafe_allow_html=True)


def render_news_card(news_data: dict, lang: str = "EN"):
    score    = news_data.get("raw_sentiment", {}).get("score", float("nan"))
    pos      = news_data.get("raw_sentiment", {}).get("positive_pct", float("nan"))
    neg      = news_data.get("raw_sentiment", {}).get("negative_pct", float("nan"))
    keywords = news_data.get("raw_sentiment", {}).get("keywords", [])
    articles = news_data.get("raw_sentiment", {}).get("articles", [])

    risk_score = news_data.get("score", float("nan"))
    color = risk_color(risk_score) if not np.isnan(risk_score) else "#94a3b8"

    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center'>"
        f"<span style='font-weight:700;color:#1e293b'>{t('layer_news', lang)}</span>"
        f"<span style='color:{color};font-weight:800;font-size:1.1em'>"
        f"{'N/A' if np.isnan(risk_score) else f'{risk_score:.0f}'}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_score_bar(risk_score), unsafe_allow_html=True)

    with st.expander(t("factor_breakdown", lang), expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("Positive" if lang == "EN" else "正面", f"{pos:.1f}%" if not np.isnan(pos) else "N/A")
        c2.metric("Negative" if lang == "EN" else "负面", f"{neg:.1f}%" if not np.isnan(neg) else "N/A")
        c3.metric(t("news_sentiment", lang), f"{score:.1f}" if not np.isnan(score) else "N/A")

        if keywords:
            st.markdown(f"**{t('top_keywords', lang)}:** " + " · ".join([f"`{k}`" for k in keywords[:8]]))

        if articles:
            st.markdown("---")
            for a in articles[:5]:
                title = a.get("title", "")
                url   = a.get("url", "#")
                src   = a.get("source", "")
                pub   = a.get("publishedAt", "")[:10]
                st.markdown(f"- [{title}]({url}) *{src} · {pub}*")
