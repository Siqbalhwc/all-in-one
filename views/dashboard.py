"""
pages/dashboard.py — Premium Dashboard with KPI cards, charts, alerts
Mirrors the desktop DashboardFrame exactly.
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import date
import pandas as pd

from utils.styles import (
    fmt_currency, kpi_card_html, section_header,
    ACCENT, GREEN, RED, YELLOW, PURPLE, CYAN, BLUE, AMBER, CURRENCY
)
from utils.db import get_dashboard_kpis, get_recent_journal_entries, get_monthly_data

MONTH_ABBR = {
    "01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May","06":"Jun",
    "07":"Jul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"
}

def mo_label(ym):
    try:
        parts = ym.split("-")
        return f"{MONTH_ABBR.get(parts[1], parts[1])} {parts[0][-2:]}"
    except:
        return ym

def render():
    

    # ── Topbar ────────────────────────────────────────────────────────────────
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown(f"""
        <div style="padding:4px 0 8px 0;">
            <div style="font-size:22px;font-weight:800;color:#1A1F36;">Dashboard</div>
            <div style="font-size:13px;color:#8A94A6;">Welcome back — here's your financial overview</div>
        </div>
        """, unsafe_allow_html=True)
    with col_r:
        btn_cols = st.columns(3)
        with btn_cols[0]:
            if st.button("＋ New Invoice", use_container_width=True, type="primary"):
                st.session_state.page = "sales"
                st.rerun()
        with btn_cols[1]:
            if st.button("＋ Receipt", use_container_width=True):
                st.session_state.page = "receipts"
                st.rerun()
        with btn_cols[2]:
            if st.button("＋ Expense", use_container_width=True):
                st.session_state.page = "journal"
                st.rerun()

    st.markdown("---")

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("Loading dashboard..."):
        try:
            kpis = get_dashboard_kpis()
        except Exception as e:
            st.error(f"Database error: {e}")
            st.info("💡 Make sure your Supabase credentials are configured in `.streamlit/secrets.toml`")
            _demo_dashboard()
            return

    # ── Row 1: Financial Overview + Quick Stats ───────────────────────────────
    section_header("FINANCIAL OVERVIEW")

    fin_cols = st.columns(4)
    fin_kpis = [
        ("Total Assets",  fmt_currency(kpis["total_assets"], compact=True), "All assets",       BLUE,   "→ View", None),
        ("Liabilities",   fmt_currency(kpis["total_liab"],   compact=True), "Total debts",      RED,    "→ View", None),
        ("Revenue",       fmt_currency(kpis["revenue"],      compact=True), "Sales revenue",    GREEN,  "→ View", None),
        ("Net Profit",    fmt_currency(kpis["net_profit"],   compact=True), "P&L result",       PURPLE,
            "↑ Profit" if kpis["net_profit"] > 0 else "↓ Loss",
            True if kpis["net_profit"] > 0 else False),
    ]

    for col, (title, val, sub, color, trend, trend_up) in zip(fin_cols, fin_kpis):
        with col:
            st.markdown(kpi_card_html(title, val, sub, color, trend, trend_up), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Operations KPIs ────────────────────────────────────────────────
    section_header("OPERATIONS")
    op_cols = st.columns(4)
    ar_val = kpis["ar_val"]
    ap_val = kpis["ap_val"]

    op_kpis = [
        ("Receivables", str(kpis["open_ar"]),
         fmt_currency(ar_val, compact=True) + " outstanding" if ar_val > 0 else "No outstanding", BLUE),
        ("Payables", str(kpis["open_ap"]),
         fmt_currency(ap_val, compact=True) + " outstanding" if ap_val > 0 else "No outstanding", AMBER),
        ("Low Stock", str(kpis["low_stock"]),
         f"{kpis['out_stock']} out of stock", RED),
        ("Customers", str(kpis["total_cust"]),
         f"{kpis['total_supp']} suppliers · {kpis['total_prod']} products", CYAN),
    ]
    for col, (title, val, sub, color) in zip(op_cols, op_kpis):
        with col:
            st.markdown(kpi_card_html(title, val, sub, color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 3: Quick Stats + Alerts + Recent Transactions ────────────────────
    stats_col, alerts_col = st.columns([1, 1])

    with stats_col:
        section_header("QUICK STATS")
        stats_data = [
            ("Products",    str(kpis["total_prod"]),                          BLUE),
            ("Customers",   str(kpis["total_cust"]),                          CYAN),
            ("Suppliers",   str(kpis["total_supp"]),                          GREEN),
            ("Inv. Value",  fmt_currency(kpis["inv_value"], compact=True),   PURPLE),
        ]
        stats_html = '<div style="background:#fff;border-radius:10px;border:1px solid #E2E6EF;overflow:hidden;">'
        for i, (label, val, color) in enumerate(stats_data):
            border = "" if i == len(stats_data)-1 else "border-bottom:1px solid #F8F9FC;"
            stats_html += f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:12px 16px;{border}">
                <span style="font-size:13px;color:#8A94A6;">{label}</span>
                <span style="font-size:13px;font-weight:700;color:{color};">{val}</span>
            </div>"""
        stats_html += "</div>"
        st.markdown(stats_html, unsafe_allow_html=True)

    with alerts_col:
        section_header("ALERTS")
        alerts = []
        if kpis["out_stock"] > 0:
            alerts.append(("✕", f"{kpis['out_stock']} out of stock", RED))
        if kpis["low_stock"] > 0:
            alerts.append(("⚠", f"{kpis['low_stock']} below reorder level", AMBER))
        if ar_val > 0:
            alerts.append(("◎", f"{fmt_currency(ar_val, True)} receivable outstanding", BLUE))
        if ap_val > 0:
            alerts.append(("⚠", f"{fmt_currency(ap_val, True)} payable outstanding", AMBER))
        if not alerts:
            alerts.append(("✓", "All systems clear!", GREEN))

        alerts_html = '<div style="background:#fff;border-radius:10px;border:1px solid #E2E6EF;overflow:hidden;">'
        for i, (icon, text, color) in enumerate(alerts):
            border = "" if i == len(alerts)-1 else "border-bottom:1px solid #F8F9FC;"
            alerts_html += f"""
            <div style="display:flex;align-items:center;gap:12px;padding:10px 16px;{border}">
                <div style="width:24px;height:24px;border-radius:50%;background:{color};
                            display:flex;align-items:center;justify-content:center;
                            color:#fff;font-size:10px;font-weight:700;flex-shrink:0;">
                    {icon}
                </div>
                <span style="font-size:13px;color:#1A1F36;">{text}</span>
            </div>"""
        alerts_html += "</div>"
        st.markdown(alerts_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 4: Monthly Charts ─────────────────────────────────────────────────
    section_header("MONTHLY TRENDS (LAST 6 MONTHS)")
    try:
        income_data, profit_data = get_monthly_data()
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            _bar_chart("Monthly Income (Sales)", income_data, GREEN)

        with chart_col2:
            _bar_chart("Monthly Profit / Loss", profit_data, BLUE, allow_negative=True)
    except Exception:
        st.info("No monthly data available yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 5: Recent Journal Entries ─────────────────────────────────────────
    section_header("RECENT TRANSACTIONS")
    try:
        recent = get_recent_journal_entries(limit=8)
        if recent:
            txn_data = []
            for r in recent:
                txn_data.append({
                    "Entry No": r.get("entry_no", "—"),
                    "Date": str(r.get("date", "—")),
                    "Description": (r.get("description") or "—")[:40],
                    "Debit": fmt_currency(r["total_dr"]) if r["total_dr"] else "—",
                    "Credit": fmt_currency(r["total_cr"]) if r["total_cr"] else "—",
                })
            df = pd.DataFrame(txn_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No journal entries yet. Add your first entry in Journal Entries.")
    except Exception as e:
        st.info("No transaction data available yet.")


def _bar_chart(title: str, data: list, accent: str, allow_negative: bool = False):
    """Render a Plotly bar chart matching the desktop app style."""
    if not data:
        st.info(f"No data for {title}")
        return

    labels = [mo_label(str(d[0])) for d in data]
    values = [float(d[1]) if d[1] else 0.0 for d in data]

    colors = []
    for v in values:
        if v >= 0:
            colors.append(accent)
        else:
            colors.append("#EF4444")

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f"{int(abs(v)/1000)}K" if abs(v) >= 1000 else str(int(abs(v))) for v in values],
        textposition="outside",
        textfont=dict(size=10, color="#64748B"),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#1A1F36"), x=0),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color="#94A3B8")),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9",
                   tickfont=dict(size=9, color="#94A3B8"),
                   zeroline=True, zerolinecolor="#E2E8F0"),
        height=220,
        showlegend=False,
        bargap=0.35,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _demo_dashboard():
    """Show demo layout when database is not connected."""
    st.warning("📡 Database not connected — showing demo layout")
    cols = st.columns(4)
    demos = [
        ("Total Assets",  "PKR 4.2M",  "All assets",     BLUE),
        ("Liabilities",   "PKR 1.1M",  "Total debts",    RED),
        ("Revenue",       "PKR 2.8M",  "Sales revenue",  GREEN),
        ("Net Profit",    "PKR 890K",  "P&L result",     PURPLE),
    ]
    for col, (t, v, s, c) in zip(cols, demos):
        with col:
            st.markdown(kpi_card_html(t, v, s, c, "↑ vs last month", True), unsafe_allow_html=True)
