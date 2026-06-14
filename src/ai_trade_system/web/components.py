from __future__ import annotations

from typing import Iterable

import streamlit as st


def apply_platform_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ats-bg: #f6f8fb;
            --ats-surface: #ffffff;
            --ats-border: #d9e1ec;
            --ats-text: #1f2937;
            --ats-muted: #667085;
            --ats-blue: #2563eb;
            --ats-green: #16a34a;
            --ats-red: #dc2626;
            --ats-amber: #d97706;
        }
        .stApp {
            background: var(--ats-bg);
            color: var(--ats-text);
        }
        [data-testid="stHeader"] {
            height: 0;
            visibility: hidden;
        }
        #MainMenu,
        footer {
            visibility: hidden;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--ats-border);
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--ats-text);
        }
        div[data-testid="stMetric"] {
            background: var(--ats-surface);
            border: 1px solid var(--ats-border);
            border-radius: 8px;
            padding: 12px 14px;
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] * {
            color: var(--ats-muted) !important;
        }
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] * {
            color: #111827 !important;
        }
        [data-testid="stMetricDelta"],
        [data-testid="stMetricDelta"] * {
            color: var(--ats-muted) !important;
        }
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] *,
        [data-testid="stWidgetLabel"] p,
        [data-testid="stMarkdownContainer"] p,
        label,
        .stTextInput label,
        .stSelectbox label,
        .stNumberInput label,
        .stTextArea label {
            color: #334155 !important;
        }
        [data-testid="stTextInputRootElement"],
        [data-testid="stNumberInputContainer"],
        [data-testid="stTextArea"] textarea,
        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea {
            background: #ffffff !important;
            color: #111827 !important;
            -webkit-text-fill-color: #111827 !important;
            border: 1px solid var(--ats-border) !important;
            border-radius: 6px !important;
        }
        [data-testid="stTextInputRootElement"] input,
        [data-testid="stNumberInputContainer"] input,
        [data-testid="stNumberInputField"] {
            color: #111827 !important;
            -webkit-text-fill-color: #111827 !important;
        }
        div[data-baseweb="select"] > div {
            background: #ffffff !important;
            color: #111827 !important;
            border-color: var(--ats-border) !important;
            border-radius: 6px !important;
        }
        div[data-baseweb="select"] span {
            color: #111827 !important;
        }
        .ats-topbar {
            border: 1px solid var(--ats-border);
            border-radius: 8px;
            background: #ffffff;
            padding: 10px 14px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            font-size: 14px;
        }
        .ats-topbar strong {
            font-size: 18px;
            color: #111827;
        }
        .ats-panel {
            background: #ffffff;
            border: 1px solid var(--ats-border);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 14px;
        }
        .ats-section-title {
            font-size: 17px;
            line-height: 1.2;
            font-weight: 700;
            margin-bottom: 2px;
            color: #111827;
        }
        .ats-section-caption {
            color: var(--ats-muted);
            font-size: 13px;
            margin-bottom: 12px;
        }
        .ats-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 2px 8px;
            font-size: 12px;
            border: 1px solid var(--ats-border);
            background: #f8fafc;
            color: var(--ats-muted);
            margin-right: 6px;
        }
        .ats-pill-green {
            border-color: #bbf7d0;
            background: #f0fdf4;
            color: #15803d;
        }
        .ats-pill-red {
            border-color: #fecaca;
            background: #fef2f2;
            color: #b91c1c;
        }
        .ats-pill-amber {
            border-color: #fde68a;
            background: #fffbeb;
            color: #b45309;
        }
        .ats-pill-blue {
            border-color: #bfdbfe;
            background: #eff6ff;
            color: #1d4ed8;
        }
        .ats-muted {
            color: var(--ats-muted);
            font-size: 13px;
        }
        .ats-insight {
            border-left: 4px solid var(--ats-green);
            background: #f8fafc;
            padding: 12px;
            border-radius: 6px;
        }
        .block-container {
            padding-top: 1.2rem;
            max-width: 1480px;
        }
        button[kind="primary"] {
            border-radius: 6px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar(title: str, items: Iterable[str]) -> None:
    right = " · ".join(items)
    st.markdown(
        f"""
        <div class="ats-topbar">
          <strong>{title}</strong>
          <span class="ats-muted">{right}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, caption: str | None = None) -> None:
    caption_html = f'<div class="ats-section-caption">{caption}</div>' if caption else ""
    st.markdown(
        f'<div class="ats-section-title">{title}</div>{caption_html}',
        unsafe_allow_html=True,
    )


def status_pill(label: str, tone: str = "neutral") -> None:
    class_name = "ats-pill" if tone == "neutral" else f"ats-pill ats-pill-{tone}"
    st.markdown(f'<span class="{class_name}">{label}</span>', unsafe_allow_html=True)


def insight_box(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="ats-insight">
          <div style="font-weight:700;margin-bottom:4px;">{title}</div>
          <div class="ats-muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
