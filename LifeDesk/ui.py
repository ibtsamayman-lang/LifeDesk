"""
ui.py
------
Custom styling and reusable UI-rendering functions for the Streamlit app,
so LifeDesk looks like a polished product rather than a default
Streamlit prototype.
"""

import streamlit as st

from models import Document, STATUS_COLORS, STATUS_EMOJI, Priority, PRIORITY_EMOJI
from utils import format_date, format_amount

PRIMARY = "#4F6BFE"
INK = "#1F2430"
MUTED = "#6B7280"
BG = "#F7F8FB"
CARD_BG = "#FFFFFF"
BORDER = "#E7E9F1"


def inject_css():
    st.markdown(f"""
    <style>
        html, body, [class*="css"] {{
            font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
        }}
        .stApp {{
            background-color: {BG};
        }}
        #MainMenu, footer {{ visibility: hidden; }}
        section[data-testid="stSidebar"] {{
            background-color: #14162A;
        }}
        section[data-testid="stSidebar"] * {{
            color: #E9EAF5 !important;
        }}
        section[data-testid="stSidebar"] .stButton button {{
            background-color: transparent;
            border: none;
            text-align: left;
            width: 100%;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 15px;
        }}
        section[data-testid="stSidebar"] .stButton button:hover {{
            background-color: rgba(255,255,255,0.08);
        }}
        h1, h2, h3 {{
            color: {INK};
            font-weight: 700;
        }}
        .ld-hero {{
            padding: 6px 0 18px 0;
        }}
        .ld-hero-title {{
            font-size: 38px;
            font-weight: 800;
            color: {INK};
            letter-spacing: -0.5px;
        }}
        .ld-hero-sub {{
            font-size: 16px;
            color: {MUTED};
            margin-top: -6px;
        }}
        .ld-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px rgba(20,22,42,0.04);
            margin-bottom: 14px;
        }}
        .ld-metric-label {{
            font-size: 13px;
            color: {MUTED};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }}
        .ld-metric-value {{
            font-size: 30px;
            font-weight: 800;
            color: {INK};
            margin-top: 2px;
        }}
        .ld-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            color: white;
        }}
        .ld-doc-title {{
            font-size: 17px;
            font-weight: 700;
            color: {INK};
            margin: 6px 0 0 0;
        }}
        .ld-doc-sub {{
            font-size: 13px;
            color: {MUTED};
            margin-bottom: 8px;
        }}
        .ld-row {{
            font-size: 13.5px;
            color: {INK};
            margin: 3px 0;
        }}
        .ld-section-title {{
            font-size: 21px;
            font-weight: 800;
            color: {INK};
            margin: 26px 0 10px 0;
        }}
        .ld-alert {{
            border-left: 4px solid #E07B0F;
            background: #FFF6EC;
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 10px;
        }}
        .ld-alert-urgent {{
            border-left: 4px solid #D6423C;
            background: #FDEFEE;
        }}
        .ld-summary {{
            background: linear-gradient(135deg, #4F6BFE 0%, #7B5CFA 100%);
            color: white;
            border-radius: 18px;
            padding: 22px 26px;
            font-size: 15.5px;
            line-height: 1.6;
            margin-bottom: 20px;
        }}
        .ld-summary b {{ font-weight: 800; }}
        .ld-empty {{
            text-align: center;
            padding: 40px 20px;
            color: {MUTED};
        }}
        div[data-testid="stMetric"] {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 12px 16px;
        }}
    </style>
    """, unsafe_allow_html=True)


def hero(title: str, subtitle: str):
    st.markdown(f"""
    <div class="ld-hero">
        <div class="ld-hero-title">🧠 {title}</div>
        <div class="ld-hero-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def section_title(text: str):
    st.markdown(f'<div class="ld-section-title">{text}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: str):
    st.markdown(f"""
    <div class="ld-card">
        <div class="ld-metric-label">{label}</div>
        <div class="ld-metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def render_document_card_html(doc: Document) -> str:
    status = doc.compute_status()
    color = STATUS_COLORS[status]
    emoji = STATUS_EMOJI[status]
    date_label = "Expires" if doc.expiration_date else ("Renews" if doc.renewal_date else "Date")
    date_val = format_date(doc.relevant_date()) if doc.relevant_date() else "Not detected"
    amount_val = format_amount(doc.amount, doc.currency)

    return f"""
    <div class="ld-card">
        <span class="ld-badge" style="background:{color}">{doc.document_type}</span>
        <div class="ld-doc-title">{doc.icon()} {doc.title}</div>
        <div class="ld-doc-sub">{doc.organization if doc.organization else 'Not detected'}</div>
        <div class="ld-row">📅 {date_label}: {date_val}</div>
        <div class="ld-row">💰 {amount_val}</div>
        <div class="ld-row">{emoji} {status.value}</div>
    </div>
    """


def priority_badge_color(priority: str) -> str:
    mapping = {
        Priority.URGENT.value: "#D6423C",
        Priority.SOON.value: "#E07B0F",
        Priority.NORMAL.value: "#1E9E5A",
    }
    return mapping.get(priority, MUTED)
