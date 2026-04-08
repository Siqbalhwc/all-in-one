"""
pages/trial_balance.py — Trial Balance report
Computed from journal lines, never from stored balance column.
"""
import streamlit as st
import pandas as pd
from utils.styles import fmt_currency, page_header, GREEN, RED, ACCENT, CURRENCY
from utils.db import compute_trial_balance, get_supabase

def render():
    
    page_header("Trial Balance", "Computed from journal entries", "Trial Balance")

    col1, col2 = st.columns([3,1])
    with col1:
        hide_zero = st.checkbox("Hide zero-balance accounts", value=True)
    with col2:
        if st.button("🔧 Recalculate All Balances", use_container_width=True):
            _recalc_all()

    try:
        by_code, by_type = compute_trial_balance()
    except Exception as e:
        st.error(f"Error: {e}"); return

    rows = []
    total_dr = total_cr = 0.0

    for code, acc in sorted(by_code.items()):
        bal = acc["balance"]
        acc_type = acc["type"]

        if acc_type in ("Asset","Expense"):
            dr = bal if bal > 0 else 0
            cr = (-bal) if bal < 0 else 0
        else:
            cr = bal if bal > 0 else 0
            dr = (-bal) if bal < 0 else 0

        if hide_zero and dr == 0 and cr == 0:
            continue

        total_dr += dr; total_cr += cr
        rows.append({
            "Code": code,
            "Account Name": acc["name"],
            "Type": acc_type,
            "Debit": fmt_currency(dr) if dr else "—",
            "Credit": fmt_currency(cr) if cr else "—",
        })

    if rows:
        rows.append({"Code":"","Account Name":"TOTAL","Type":"",
                     "Debit": fmt_currency(total_dr), "Credit": fmt_currency(total_cr)})

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Code": st.column_config.TextColumn(width=70),
                     "Type": st.column_config.TextColumn(width=90),
                 })

    diff = abs(total_dr - total_cr)
    if diff < 0.01:
        st.success(f"✅ Trial Balance is **BALANCED** — Total DR = CR = {fmt_currency(total_dr)}")
    else:
        st.error(f"⚠️ OUT OF BALANCE by {fmt_currency(diff)} | DR: {fmt_currency(total_dr)} | CR: {fmt_currency(total_cr)}")

    # Type summary
    st.markdown("---")
    st.markdown("#### Balance by Account Type")
    type_cols = st.columns(5)
    types = ["Asset","Liability","Equity","Revenue","Expense"]
    colors = [ACCENT, RED, "#8B5CF6", GREEN, "#F59E0B"]
    for col, t, c in zip(type_cols, types, colors):
        with col:
            val = by_type.get(t, 0)
            st.markdown(f"""
            <div style="background:#fff;border-radius:8px;border:1px solid #E2E6EF;padding:12px 14px;border-top:3px solid {c};">
                <div style="font-size:10px;font-weight:700;color:#8A94A6;text-transform:uppercase;">{t}</div>
                <div style="font-size:16px;font-weight:800;color:{c};margin-top:4px;">{fmt_currency(val, compact=True)}</div>
            </div>""", unsafe_allow_html=True)


def _recalc_all():
    """Recalculate all account balances from journal lines."""
    sb = get_supabase()
    try:
        accs = sb.table("accounts").select("id,type,opening_balance").execute().data or []
        lines = sb.table("journal_lines").select("account_id,debit,credit").execute().data or []
        movements = {}
        for l in lines:
            aid = l["account_id"]
            dr = float(l.get("debit") or 0); cr = float(l.get("credit") or 0)
            if aid not in movements: movements[aid] = [0,0]
            movements[aid][0] += dr; movements[aid][1] += cr

        for a in accs:
            ob = float(a.get("opening_balance") or 0)
            dr_mv, cr_mv = movements.get(a["id"], [0,0])
            if a["type"] in ("Asset","Expense"):
                new_bal = ob + dr_mv - cr_mv
            else:
                new_bal = ob + cr_mv - dr_mv
            sb.table("accounts").update({"balance": new_bal}).eq("id", a["id"]).execute()

        st.success("✅ All account balances recalculated. Trial Balance is now accurate.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")
