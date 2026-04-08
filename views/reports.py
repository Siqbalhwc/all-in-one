"""
pages/reports.py — Financial Reports: P&L, Balance Sheet, AR/AP Aging, Inventory
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.styles import fmt_currency, page_header, section_header, ACCENT, GREEN, RED, YELLOW, PURPLE, CYAN, AMBER, BLUE, CURRENCY
from utils.db import get_supabase, compute_trial_balance, get_products, get_customers, get_suppliers, get_invoices

def render():
    
    page_header("Reports", "Financial statements and analytics", "Reports")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 P&L Statement",
        "🏦 Balance Sheet",
        "📥 AR Aging",
        "📤 AP Aging",
        "📦 Inventory Report",
    ])

    with tab1: _pl_statement()
    with tab2: _balance_sheet()
    with tab3: _ar_aging()
    with tab4: _ap_aging()
    with tab5: _inventory_report()


def _pl_statement():
    section_header("PROFIT & LOSS STATEMENT")
    try:
        by_code, by_type = compute_trial_balance()
    except Exception as e:
        st.error(f"Error: {e}"); return

    revenue_accs  = [(c, v) for c, v in by_code.items() if v["type"] == "Revenue"]
    expense_accs  = [(c, v) for c, v in by_code.items() if v["type"] == "Expense"]
    total_revenue = sum(v["balance"] for _, v in revenue_accs)
    total_expense = sum(v["balance"] for _, v in expense_accs)
    net_profit    = total_revenue - total_expense

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div style="background:#fff;border-radius:8px;border:1px solid #E2E6EF;padding:16px;border-top:3px solid {GREEN};">
            <div style="font-size:10px;font-weight:700;color:#8A94A6;text-transform:uppercase;">Total Revenue</div>
            <div style="font-size:20px;font-weight:800;color:{GREEN};margin-top:4px;">{fmt_currency(total_revenue, compact=True)}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div style="background:#fff;border-radius:8px;border:1px solid #E2E6EF;padding:16px;border-top:3px solid {RED};">
            <div style="font-size:10px;font-weight:700;color:#8A94A6;text-transform:uppercase;">Total Expenses</div>
            <div style="font-size:20px;font-weight:800;color:{RED};margin-top:4px;">{fmt_currency(total_expense, compact=True)}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        profit_color = GREEN if net_profit >= 0 else RED
        st.markdown(f"""<div style="background:#fff;border-radius:8px;border:1px solid #E2E6EF;padding:16px;border-top:3px solid {profit_color};">
            <div style="font-size:10px;font-weight:700;color:#8A94A6;text-transform:uppercase;">Net {'Profit' if net_profit >= 0 else 'Loss'}</div>
            <div style="font-size:20px;font-weight:800;color:{profit_color};margin-top:4px;">{fmt_currency(net_profit, compact=True)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_r, col_e = st.columns(2)
    with col_r:
        st.markdown("**Revenue Accounts**")
        rev_rows = [{"Account": v["name"], "Balance": fmt_currency(v["balance"])} for _, v in sorted(revenue_accs, key=lambda x: -x[1]["balance"])]
        if rev_rows:
            rev_rows.append({"Account": "**TOTAL REVENUE**", "Balance": f"**{fmt_currency(total_revenue)}**"})
        st.dataframe(pd.DataFrame(rev_rows), use_container_width=True, hide_index=True)

    with col_e:
        st.markdown("**Expense Accounts**")
        exp_rows = [{"Account": v["name"], "Balance": fmt_currency(v["balance"])} for _, v in sorted(expense_accs, key=lambda x: -x[1]["balance"])]
        if exp_rows:
            exp_rows.append({"Account": "**TOTAL EXPENSES**", "Balance": f"**{fmt_currency(total_expense)}**"})
        st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)

    # Expense breakdown pie chart
    if expense_accs:
        labels = [v["name"] for _, v in expense_accs if v["balance"] > 0]
        values = [v["balance"] for _, v in expense_accs if v["balance"] > 0]
        if labels:
            fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4,
                                   marker_colors=[ACCENT, GREEN, RED, YELLOW, PURPLE, CYAN, AMBER, BLUE]))
            fig.update_layout(title="Expense Breakdown", height=300, margin=dict(l=10,r=10,t=40,b=10),
                              paper_bgcolor="#ffffff", showlegend=True,
                              legend=dict(font=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _balance_sheet():
    section_header("BALANCE SHEET")
    try:
        by_code, by_type = compute_trial_balance()
    except Exception as e:
        st.error(f"Error: {e}"); return

    assets  = [(c, v) for c, v in by_code.items() if v["type"] == "Asset"]
    liabs   = [(c, v) for c, v in by_code.items() if v["type"] == "Liability"]
    equity  = [(c, v) for c, v in by_code.items() if v["type"] == "Equity"]

    total_assets = sum(v["balance"] for _, v in assets)
    total_liabs  = sum(v["balance"] for _, v in liabs)
    total_equity = sum(v["balance"] for _, v in equity)

    # Retained earnings = Net Profit
    revenue  = by_type.get("Revenue", 0)
    expenses = by_type.get("Expense", 0)
    net_profit = revenue - expenses
    total_equity_with_profit = total_equity + net_profit
    total_liab_equity = total_liabs + total_equity_with_profit

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**ASSETS**")
        rows = [{"Code": c, "Account": v["name"], "Balance": fmt_currency(v["balance"])}
                for c, v in sorted(assets, key=lambda x: x[0])]
        rows.append({"Code": "", "Account": "**TOTAL ASSETS**", "Balance": f"**{fmt_currency(total_assets)}**"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with c2:
        st.markdown("**LIABILITIES & EQUITY**")
        rows = [{"Code": c, "Account": v["name"], "Balance": fmt_currency(v["balance"])}
                for c, v in sorted(liabs + equity, key=lambda x: x[0])]
        rows.append({"Code": "", "Account": "Net Profit (Current Period)", "Balance": fmt_currency(net_profit)})
        rows.append({"Code": "", "Account": "**TOTAL LIABILITIES + EQUITY**", "Balance": f"**{fmt_currency(total_liab_equity)}**"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    diff = abs(total_assets - total_liab_equity)
    if diff < 0.01:
        st.success(f"✅ Balance Sheet BALANCES — Assets = Liabilities + Equity = {fmt_currency(total_assets)}")
    else:
        st.error(f"⚠️ Balance Sheet out of balance by {fmt_currency(diff)}")


def _ar_aging():
    section_header("ACCOUNTS RECEIVABLE AGING")
    try:
        customers = get_customers()
        invoices  = get_invoices(inv_type="sale")
    except Exception as e:
        st.error(f"Error: {e}"); return

    from datetime import date, timedelta
    today = date.today()
    cust_map = {c["id"]: c["name"] for c in customers}

    buckets = {"Current (0-30)": [], "31-60 days": [], "61-90 days": [], "Over 90 days": []}
    for inv in invoices:
        if inv.get("status") == "Paid": continue
        due = float(inv.get("total") or 0) - float(inv.get("paid") or 0)
        if due <= 0: continue
        try:
            due_dt = date.fromisoformat(str(inv.get("due_date") or inv.get("date")))
        except:
            due_dt = today
        days = (today - due_dt).days
        row = {"Invoice": inv.get("invoice_no"), "Customer": cust_map.get(inv.get("party_id"),"—"),
               "Date": str(inv.get("date","")), "Due Date": str(inv.get("due_date") or "—"),
               "Due Amount": fmt_currency(due)}
        if days <= 30:    buckets["Current (0-30)"].append(row)
        elif days <= 60:  buckets["31-60 days"].append(row)
        elif days <= 90:  buckets["61-90 days"].append(row)
        else:             buckets["Over 90 days"].append(row)

    for bucket, rows in buckets.items():
        if rows:
            st.markdown(f"**{bucket}** — {len(rows)} invoice(s)")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _ap_aging():
    section_header("ACCOUNTS PAYABLE AGING")
    try:
        suppliers = get_suppliers()
        invoices  = get_invoices(inv_type="purchase")
    except Exception as e:
        st.error(f"Error: {e}"); return

    from datetime import date
    today = date.today()
    supp_map = {s["id"]: s["name"] for s in suppliers}

    buckets = {"Current (0-30)": [], "31-60 days": [], "61-90 days": [], "Over 90 days": []}
    for inv in invoices:
        if inv.get("status") == "Paid": continue
        due = float(inv.get("total") or 0) - float(inv.get("paid") or 0)
        if due <= 0: continue
        try:
            due_dt = date.fromisoformat(str(inv.get("due_date") or inv.get("date")))
        except:
            due_dt = today
        days = (today - due_dt).days
        row = {"Bill": inv.get("invoice_no"), "Supplier": supp_map.get(inv.get("party_id"),"—"),
               "Date": str(inv.get("date","")), "Due Date": str(inv.get("due_date") or "—"),
               "Due Amount": fmt_currency(due)}
        if days <= 30:    buckets["Current (0-30)"].append(row)
        elif days <= 60:  buckets["31-60 days"].append(row)
        elif days <= 90:  buckets["61-90 days"].append(row)
        else:             buckets["Over 90 days"].append(row)

    for bucket, rows in buckets.items():
        if rows:
            st.markdown(f"**{bucket}** — {len(rows)} bill(s)")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _inventory_report():
    section_header("INVENTORY VALUATION REPORT")
    try:
        products = get_products()
    except Exception as e:
        st.error(f"Error: {e}"); return

    total_cost  = sum(float(p.get("qty_on_hand") or 0) * float(p.get("cost_price") or 0) for p in products)
    total_sell  = sum(float(p.get("qty_on_hand") or 0) * float(p.get("sale_price") or 0) for p in products)
    total_units = sum(float(p.get("qty_on_hand") or 0) for p in products)

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Total Cost Value", fmt_currency(total_cost, compact=True))
    with c2: st.metric("Total Sale Value", fmt_currency(total_sell, compact=True))
    with c3: st.metric("Potential Margin", fmt_currency(total_sell - total_cost, compact=True))

    rows = []
    for p in sorted(products, key=lambda x: float(x.get("qty_on_hand") or 0) * float(x.get("cost_price") or 0), reverse=True):
        qty  = float(p.get("qty_on_hand") or 0)
        cost = float(p.get("cost_price") or 0)
        sell = float(p.get("sale_price") or 0)
        val  = qty * cost
        sell_val = qty * sell
        status = "✕ Out" if qty <= 0 else ("⚠ Low" if qty <= float(p.get("reorder_level") or 0) else "✓ OK")
        rows.append({
            "Code": p["code"],
            "Product": p["name"],
            "Qty": f"{qty:,.0f}",
            "Cost Price": fmt_currency(cost),
            "Sale Price": fmt_currency(sell),
            "Cost Value": fmt_currency(val),
            "Sale Value": fmt_currency(sell_val),
            "Margin": fmt_currency(sell_val - val),
            "Status": status,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
