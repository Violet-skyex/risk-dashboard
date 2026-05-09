"""Risk gauge and supporting chart components."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from src.config import risk_color, risk_label

_FONT = {"color": "#1e293b", "family": "Inter, sans-serif"}


def render_risk_gauge(score: float, ticker: str, lang: str = "EN") -> go.Figure:
    color = risk_color(score) if not np.isnan(score) else "#94a3b8"
    label = risk_label(score, lang) if not np.isnan(score) else "N/A"
    display_score = round(score, 1) if not np.isnan(score) else 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=display_score,
        title={"text": f"<b>{ticker}</b><br><span style='font-size:0.85em;color:#64748b'>{label}</span>",
               "font": {"size": 16, "color": "#1e293b"}},
        number={"font": {"size": 40, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
            "bar":  {"color": color, "thickness": 0.25},
            "bgcolor": "#f8fafc",
            "borderwidth": 1,
            "bordercolor": "#e2e8f0",
            "steps": [
                {"range": [0, 25],   "color": "rgba(46,204,113,0.15)"},
                {"range": [25, 50],  "color": "rgba(241,196,15,0.15)"},
                {"range": [50, 75],  "color": "rgba(230,126,34,0.15)"},
                {"range": [75, 100], "color": "rgba(231,76,60,0.15)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.8,
                "value": display_score,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=_FONT,
    )
    return fig


def render_panic_bubble_chart(bubble_score: float, panic_score: float, lang: str = "EN") -> go.Figure:
    bubble_label = "Bubble" if lang == "EN" else "泡沫"
    panic_label  = "Panic"  if lang == "EN" else "恐慌"

    fig = go.Figure()

    fig.add_shape(type="line", x0=50, x1=50, y0=0, y1=100,
                  line=dict(color="#cbd5e1", width=1, dash="dot"))
    fig.add_shape(type="line", x0=0, x1=100, y0=50, y1=50,
                  line=dict(color="#cbd5e1", width=1, dash="dot"))

    fig.add_trace(go.Scatter(
        x=[bubble_score], y=[panic_score],
        mode="markers+text",
        marker=dict(size=22, color="#2563eb", symbol="circle",
                    line=dict(color="white", width=2)),
        text=["NOW"],
        textposition="top center",
        textfont=dict(color="#1e293b", size=11),
        hovertemplate=(
            f"<b>Current Market</b><br>"
            f"{bubble_label}: {bubble_score}<br>"
            f"{panic_label}: {panic_score}<extra></extra>"
        ),
    ))

    fig.update_layout(
        xaxis=dict(
            title=dict(text=f"← Neutral   {bubble_label} →", font=dict(color="#475569")),
            range=[0, 100], showgrid=False, zeroline=False, tickfont=dict(size=10),
        ),
        yaxis=dict(
            title=dict(text=f"← Neutral   {panic_label} →", font=dict(color="#475569")),
            range=[0, 100], showgrid=False, zeroline=False, tickfont=dict(size=10),
        ),
        height=280,
        margin=dict(l=60, r=20, t=20, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        font=_FONT,
        showlegend=False,
    )

    for x, y, txt in [
        (75, 75, "Volatile"),
        (25, 75, "Panic Zone" if lang == "EN" else "恐慌区"),
        (75, 25, "Bubble Zone" if lang == "EN" else "泡沫区"),
        (25, 25, "Calm" if lang == "EN" else "平静"),
    ]:
        fig.add_annotation(x=x, y=y, text=f"<i>{txt}</i>",
                           showarrow=False, font=dict(color="#94a3b8", size=10))

    # Disable zoom so the chart can't get stuck in a zoomed state
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    return fig


def render_drawdown_distribution(scenarios: list[dict], lang: str = "EN") -> go.Figure:
    if not scenarios:
        return go.Figure()

    rows = [(s["date"][:7], s["max_dd"], s.get("composite_sim", 0))
            for s in scenarios
            if s.get("max_dd") is not None and not np.isnan(s.get("max_dd", np.nan))]
    if not rows:
        return go.Figure()

    labels, max_dds, sims = zip(*rows)

    title = (
        "SPY Max Drawdown in 12M After Each Historical Analogue"
        if lang == "EN" else
        "各历史相似情景后12个月内SPY最大回撤"
    )
    fig = px.bar(
        x=list(labels), y=list(max_dds),
        labels={"x": "Historical Analogue Start", "y": "Max Drawdown (%)"},
        color=list(max_dds),
        color_continuous_scale=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
        title=title,
        hover_data={"Similarity": [f"{s:.0f}%" for s in sims]},
    )
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        font=_FONT,
        showlegend=False,
        coloraxis_showscale=False,
    )
    fig.update_traces(marker_line_width=0)
    return fig
