"""Hedging instruments display — informational only, not advice."""

import streamlit as st
from src.i18n import t


HEDGE_TOOLS = {
    "broad_market": {
        "EN": "Broad Market (SPY/QQQ/SPX)",
        "CN": "大盘指数 (SPY/QQQ/SPX)",
        "instruments": [
            {"name": "SPXU",  "type": "Inverse ETF", "desc_EN": "3× inverse S&P 500",                        "desc_CN": "3倍做空标普500"},
            {"name": "SH",    "type": "Inverse ETF", "desc_EN": "1× inverse S&P 500",                        "desc_CN": "1倍做空标普500"},
            {"name": "SQQQ",  "type": "Inverse ETF", "desc_EN": "3× inverse Nasdaq-100",                     "desc_CN": "3倍做空纳斯达克100"},
            {"name": "PSQ",   "type": "Inverse ETF", "desc_EN": "1× inverse Nasdaq-100",                     "desc_CN": "1倍做空纳斯达克100"},
            {"name": "UVXY",  "type": "Vol Product", "desc_EN": "1.5× long VIX short-term futures",           "desc_CN": "1.5倍做多VIX短期期货"},
            {"name": "VXX",   "type": "Vol Product", "desc_EN": "Long VIX short-term futures (1×)",           "desc_CN": "做多VIX短期期货(1倍)"},
            {"name": "SPY Puts","type":"Options",    "desc_EN": "Put options on SPY; check IV before buying", "desc_CN": "SPY认沽期权，注意买入前查看IV"},
            {"name": "GLD",   "type": "Safe Haven",  "desc_EN": "Gold ETF — traditional flight-to-safety",   "desc_CN": "黄金ETF — 传统避险资产"},
            {"name": "SHY/BIL","type":"Safe Haven",  "desc_EN": "Short-term Treasuries — cash equivalent",   "desc_CN": "短期国债ETF — 等现金避险"},
            {"name": "UUP",   "type": "Safe Haven",  "desc_EN": "Long US Dollar index",                      "desc_CN": "做多美元指数"},
        ],
    },
    "single_stock": {
        "EN": "Single Stock",
        "CN": "个股",
        "instruments": [
            {"name": "[TICKER] Puts", "type": "Options",    "desc_EN": "Put options on the stock; ATM 30/60/90d", "desc_CN": "该股认沽期权，30/60/90天平值"},
            {"name": "Sector Short ETF","type":"Inverse ETF","desc_EN": "Inverse ETF on the stock's sector (e.g. SOXS for semis)", "desc_CN": "行业反向ETF（如半导体SOXS）"},
            {"name": "Collar Strategy","type":"Options",    "desc_EN": "Buy put + sell call to cap downside and upside", "desc_CN": "买认沽+卖认购，限制上下行风险"},
            {"name": "VIX Calls",     "type":"Vol Product", "desc_EN": "VIX call options for tail-risk hedge",  "desc_CN": "VIX认购期权，用于尾部风险对冲"},
        ],
    },
}


def render_hedge_tools(ticker: str, lang: str = "EN"):
    is_stock = ticker not in ("SPY", "QQQ", "^SPX", "^GSPC", "")

    st.markdown(
        f"<p style='color:#888;font-size:0.82em;margin-bottom:8px'>"
        f"{'Informational only — not investment advice.' if lang=='EN' else '仅供参考，不构成投资建议。'}"
        f"</p>",
        unsafe_allow_html=True,
    )

    tool_set = HEDGE_TOOLS["broad_market"]

    category = tool_set["EN"] if lang == "EN" else tool_set["CN"]
    st.markdown(f"**{category}**")
    _render_tool_table(tool_set["instruments"], lang, ticker)

    if is_stock:
        st.markdown("---")
        stock_set = HEDGE_TOOLS["single_stock"]
        category2 = stock_set["EN"] if lang == "EN" else stock_set["CN"]
        st.markdown(f"**{category2}: {ticker}**")
        instruments = []
        for item in stock_set["instruments"]:
            item = dict(item)
            item["name"] = item["name"].replace("[TICKER]", ticker)
            instruments.append(item)
        _render_tool_table(instruments, lang, ticker)


def _render_tool_table(instruments: list, lang: str, ticker: str):
    type_lbl = "Type" if lang == "EN" else "类型"
    desc_lbl = "Description" if lang == "EN" else "说明"

    html = (
        f"<table style='width:100%;border-collapse:collapse;font-size:0.82em'>"
        f"<thead><tr style='color:#888;border-bottom:1px solid #333'>"
        f"<th style='text-align:left;padding:4px'>Instrument</th>"
        f"<th style='text-align:left;padding:4px'>{type_lbl}</th>"
        f"<th style='text-align:left;padding:4px'>{desc_lbl}</th>"
        f"</tr></thead><tbody>"
    )
    for item in instruments:
        name = item["name"]
        itype = item["type"]
        desc = item["desc_CN"] if lang == "CN" else item["desc_EN"]
        html += (
            f"<tr style='border-bottom:1px solid #1a1a2e'>"
            f"<td style='padding:5px 4px;color:#cba6f7;font-weight:600'>{name}</td>"
            f"<td style='padding:5px 4px;color:#89b4fa'>{itype}</td>"
            f"<td style='padding:5px 4px;color:#a6adc8'>{desc}</td>"
            f"</tr>"
        )
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
