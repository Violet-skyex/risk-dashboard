"""Historical scenario display component."""

import streamlit as st
import numpy as np
from src.i18n import t
from src.config import risk_color


def render_scenarios(scenarios: list[dict], lang: str = "EN"):
    if not scenarios:
        msg = "Insufficient historical data to find analogues." if lang == "EN" \
              else "历史数据不足，无法找到相似情景。"
        st.info(msg)
        return

    for i, s in enumerate(scenarios):
        sim   = s.get("composite_sim", 0)
        date  = s.get("date", "")
        fwd3  = s.get("fwd_3m",  float("nan"))
        fwd12 = s.get("fwd_12m", float("nan"))
        dd    = s.get("max_dd",  float("nan"))
        dd_d  = s.get("dd_days", None)
        rec_d = s.get("recovery_days", None)

        m_sim  = s.get("macro_sim",      float("nan"))
        r_sim  = s.get("rates_sim",      float("nan"))
        se_sim = s.get("sentiment_sim",  float("nan"))
        te_sim = s.get("technical_sim",  float("nan"))

        with st.expander(
            f"#{i+1}  {date}  —  {t('sim_score', lang)}: **{sim}%**",
            expanded=(i == 0),
        ):
            col1, col2, col3 = st.columns(3)
            col1.markdown(_mini_bar(m_sim,  t("scenario_macro",     lang)))
            col2.markdown(_mini_bar(r_sim,  "Rates" if lang == "EN" else "利率"))
            col3.markdown(_mini_bar(se_sim, t("scenario_sentiment",  lang)))
            st.markdown(_mini_bar(te_sim, t("scenario_technical", lang)))

            st.markdown("---")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric(t("fwd_return_3m",  lang),
                      f"{fwd3:+.1f}%"  if not np.isnan(fwd3)  else "N/A")
            c2.metric(t("fwd_return_12m", lang),
                      f"{fwd12:+.1f}%" if not np.isnan(fwd12) else "N/A")
            c3.metric(t("max_dd",         lang),
                      f"{dd:.1f}%"     if not np.isnan(dd)    else "N/A")
            c4.metric(t("dd_duration",    lang),
                      f"{dd_d}d"       if dd_d                else "N/A")

            if rec_d is not None:
                rec_label = "Recovery to prior high" if lang == "EN" else "恢复至前高"
                st.caption(f"{rec_label}: **{rec_d} days**")


def _mini_bar(score: float, label: str) -> str:
    if np.isnan(score):
        return f"**{label}**: N/A"
    color = "#16a34a" if score > 80 else "#ca8a04" if score > 65 else "#94a3b8"
    bar_w = int(score)
    return (
        f"**{label}** {score:.0f}%  "
        f"<span style='display:inline-block;vertical-align:middle;"
        f"background:#e2e8f0;border-radius:3px;width:80px;height:6px'>"
        f"<span style='background:{color};display:block;width:{bar_w}%;height:6px;"
        f"border-radius:3px'></span></span>"
    )
