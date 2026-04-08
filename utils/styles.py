"""
utils/styles.py — Shared CSS, colors, and UI helpers for the SaaS app
Mirrors the desktop app's design tokens exactly.
"""
import streamlit as st

CURRENCY = "PKR"

# Design tokens — matches desktop app
ACCENT   = "#3D5AF1"
ACCENT2  = "#10B981"
RED      = "#EF4444"
GREEN    = "#10B981"
YELLOW   = "#F59E0B"
PURPLE   = "#8B5CF6"
CYAN     = "#0891B2"
BLUE     = "#1D4ED8"
AMBER    = "#D97706"

def inject_global_css():
    st.markdown("""
    <style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif !important;
    }

    /* ── Page background ── */
    .stApp {
        background: #F5F7FB !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #FFFFFF !important;
        border-right: 1px solid #E2E6EF;
        width: 240px !important;
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #1A1F36;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        color: #8A94A6;
        margin: 18px 0 6px 0;
    }

    /* ── KPI Cards ── */
    .kpi-card {
        background: #FFFFFF;
        border-radius: 10px;
        border: 1px solid #E2E6EF;
        padding: 0 0 16px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        overflow: hidden;
        cursor: pointer;
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }
    .kpi-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.10);
        transform: translateY(-1px);
    }
    .kpi-accent-bar {
        height: 3px;
        width: 100%;
        margin-bottom: 14px;
    }
    .kpi-title {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8A94A6;
        padding: 0 16px;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 800;
        padding: 0 16px;
        line-height: 1.2;
    }
    .kpi-subtitle {
        font-size: 11px;
        color: #8A94A6;
        padding: 4px 16px 0 16px;
    }
    .kpi-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 10px;
        font-weight: 700;
        margin: 6px 16px 0 16px;
    }

    /* ── Section headers ── */
    .section-header {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #8A94A6;
        margin: 20px 0 10px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid #F0F2F7;
    }

    /* ── Table cards ── */
    .data-table-card {
        background: #FFFFFF;
        border-radius: 10px;
        border: 1px solid #E2E6EF;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        overflow: hidden;
        margin-bottom: 16px;
    }
    .table-header-row {
        background: #F8F9FC;
        padding: 10px 16px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #8A94A6;
        border-bottom: 1px solid #E2E6EF;
    }

    /* ── Status badges ── */
    .badge-paid     { background: #D1FAE5; color: #065F46; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .badge-unpaid   { background: #FEF3C7; color: #92400E; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .badge-partial  { background: #DBEAFE; color: #1E40AF; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .badge-ok       { background: #D1FAE5; color: #065F46; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .badge-low      { background: #FEF3C7; color: #92400E; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
    .badge-out      { background: #FEE2E2; color: #991B1B; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }

    /* ── Alert cards ── */
    .alert-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        border-bottom: 1px solid #F8F9FC;
        font-size: 13px;
    }
    .alert-icon {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 700;
        color: white;
        flex-shrink: 0;
    }

    /* ── Page title ── */
    .page-title {
        font-size: 22px;
        font-weight: 800;
        color: #1A1F36;
        margin-bottom: 2px;
    }
    .page-subtitle {
        font-size: 13px;
        color: #8A94A6;
        margin-bottom: 20px;
    }

    /* ── Streamlit overrides ── */
    div[data-testid="stMetricValue"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .stTextInput>div>div>input,
    .stSelectbox>div>div>div,
    .stNumberInput>div>div>input {
        border-radius: 6px;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* ── Topbar breadcrumb ── */
    .topbar {
        background: #FFFFFF;
        border-bottom: 1px solid #E2E6EF;
        padding: 12px 20px;
        margin: -1rem -1rem 1rem -1rem;
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
    }

    /* ── Hide Streamlit default elements ── */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header    { visibility: hidden; }
    .stDeployButton { display: none; }
    </style>
    """, unsafe_allow_html=True)

def fmt_currency(value, compact=False):
    """Format a number as PKR currency."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"{CURRENCY} 0"
    if compact:
        if abs(v) >= 1_000_000:
            return f"{CURRENCY} {v/1_000_000:.1f}M"
        if abs(v) >= 10_000:
            return f"{CURRENCY} {v/1_000:.0f}K"
        if abs(v) >= 1_000:
            return f"{CURRENCY} {v/1_000:.1f}K"
    return f"{CURRENCY} {v:,.2f}"

def kpi_card_html(title, value, subtitle="", color=ACCENT, trend_text="", trend_up=None):
    """Render a premium KPI card as HTML."""
    if trend_text:
        if trend_up is True:
            pill_bg, pill_fg, arrow = "#F0FDF4", "#16A34A", "↑"
        elif trend_up is False:
            pill_bg, pill_fg, arrow = "#FEF2F2", "#DC2626", "↓"
        else:
            pill_bg, pill_fg, arrow = "#F8FAFC", "#8A94A6", ""
        pill_html = f'<span class="kpi-pill" style="background:{pill_bg};color:{pill_fg}">{arrow} {trend_text}</span>'
    else:
        pill_html = ""

    return f"""
    <div class="kpi-card">
        <div class="kpi-accent-bar" style="background:{color}"></div>
        <div class="kpi-title">{title}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
        {f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ''}
        {pill_html}
    </div>
    """

def status_badge(status: str) -> str:
    s = str(status).lower()
    if s == "paid":    return f'<span class="badge-paid">✓ Paid</span>'
    if s == "partial": return f'<span class="badge-partial">◑ Partial</span>'
    if s == "unpaid":  return f'<span class="badge-unpaid">⏳ Unpaid</span>'
    return f'<span class="badge-unpaid">{status}</span>'

def stock_badge(qty, reorder) -> str:
    q = float(qty or 0); r = float(reorder or 0)
    if q <= 0:      return '<span class="badge-out">✕ Out</span>'
    if q <= r:      return '<span class="badge-low">⚠ Low</span>'
    return '<span class="badge-ok">✓ OK</span>'

def page_header(title: str, subtitle: str = "", breadcrumb: str = ""):
    if breadcrumb:
        st.markdown(f'<div class="topbar">📊 <span style="color:#8A94A6">Accounting</span> <span style="color:#8A94A6">/</span> <strong>{breadcrumb}</strong></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)

def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

def success_toast(msg: str):
    st.success(f"✅ {msg}")

def error_toast(msg: str):
    st.error(f"❌ {msg}")
