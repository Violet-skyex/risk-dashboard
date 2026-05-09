"""Historical scenario display component."""

import streamlit as st
import numpy as np
from src.i18n import t


def render_scenarios(scenarios: list[dict], lang: str = "EN", ticker: str = "SPY"):
    if not scenarios:
        msg = "Insufficient historical data to find analogues." if lang == "EN" \
              else "历史数据不足，无法找到相似情景。"
        st.info(msg)
        return

    intro = (
        f"Each scenario is a historical period where market conditions were most similar to today, "
        f"ranked by composite similarity across macro, rates, sentiment, and technical layers. "
        f"Forward returns and drawdowns show what {ticker} did in the 12 months after that period."
    ) if lang == "EN" else (
        f"以下每个情景为历史上与当前市场结构最相似的时期，按宏观、利率、情绪、技术面四层向量综合相似度排序。"
        f"前瞻收益和回撤数据为该时期后12个月内 {ticker} 的实际表现。"
    )
    st.caption(intro)

    fwd3_lbl  = f"{ticker} 3M Return"  if lang == "EN" else f"{ticker} 3个月收益"
    fwd12_lbl = f"{ticker} 12M Return" if lang == "EN" else f"{ticker} 12个月收益"
    dd_lbl    = t("max_dd",       lang)
    dur_lbl   = t("dd_duration",  lang)
    rec_lbl   = "Recovery to prior high" if lang == "EN" else "恢复至前高"

    macro_lbl = t("scenario_macro",     lang)
    rates_lbl = "Rates" if lang == "EN" else "利率"
    sent_lbl  = t("scenario_sentiment", lang)
    tech_lbl  = t("scenario_technical", lang)

    for i, s in enumerate(scenarios):
        sim   = s.get("composite_sim", 0)
        date  = s.get("date", "")
        fwd3  = s.get("fwd_3m",  float("nan"))
        fwd6  = s.get("fwd_6m",  float("nan"))
        fwd12 = s.get("fwd_12m", float("nan"))
        dd    = s.get("max_dd",  float("nan"))
        dd_d  = s.get("dd_days", None)
        rec_d = s.get("recovery_days", None)
        m_sim = s.get("macro_sim",     float("nan"))
        r_sim = s.get("rates_sim",     float("nan"))
        se_sim= s.get("sentiment_sim", float("nan"))
        te_sim= s.get("technical_sim", float("nan"))

        label = t("sim_score", lang)
        with st.expander(f"#{i+1}  {date}   {label}: {sim:.0f}%", expanded=(i == 0)):

            # ── similarity breakdown ──────────────────────────────────
            sim_hdr = "Layer Similarity" if lang == "EN" else "各层相似度"
            st.markdown(f"**{sim_hdr}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(macro_lbl, f"{m_sim:.0f}%"  if not np.isnan(m_sim)  else "N/A")
            c2.metric(rates_lbl, f"{r_sim:.0f}%"  if not np.isnan(r_sim)  else "N/A")
            c3.metric(sent_lbl,  f"{se_sim:.0f}%" if not np.isnan(se_sim) else "N/A")
            c4.metric(tech_lbl,  f"{te_sim:.0f}%" if not np.isnan(te_sim) else "N/A")

            st.markdown("---")

            # ── SPY forward performance ───────────────────────────────
            perf_hdr = "SPY Forward Performance After This Period" if lang == "EN" \
                       else "该时期后标普500表现"
            st.markdown(f"**{perf_hdr}**")
            o1, o2, o3, o4 = st.columns(4)

            o1.metric(fwd3_lbl,
                      f"{fwd3:+.1f}%"  if not np.isnan(fwd3)  else "N/A",
                      delta_color="normal")
            o2.metric(fwd12_lbl,
                      f"{fwd12:+.1f}%" if not np.isnan(fwd12) else "N/A",
                      delta_color="normal")
            o3.metric(dd_lbl,
                      f"{dd:.1f}%"     if not np.isnan(dd)    else "N/A")
            o4.metric(dur_lbl,
                      f"{dd_d}d"       if dd_d is not None     else "N/A")

            if rec_d is not None:
                st.caption(f"{rec_lbl}: **{rec_d} days**")
