"""
pages/payments.py — Supplier payment recording
DR Accounts Payable / CR Cash
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.styles import fmt_currency, page_header, AMBER, CURRENCY
from utils.db import get_supabase, get_suppliers

def render():
    
    page_header("Payments", "Record supplier payments", "Payments")

    tab1, tab2 = st.tabs(["📋 Payment History", "➕ New Payment"])

    with tab1:
        _list_payments()
    with tab2:
        _payment_form()


def _list_payments():
    sb = get_supabase()
    try:
        entries = sb.table("journal_entries").select("id,entry_no,date,description,reference").ilike("description", "Payment%").order("date", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Error: {e}"); return

    if not entries:
        st.info("No payments recorded yet."); return

    rows = []
    for e in entries:
        lines = sb.table("journal_lines").select("debit,credit").eq("entry_id", e["id"]).execute().data or []
        amount = sum(float(l.get("credit") or 0) for l in lines) / 2 if lines else 0
        rows.append({
            "Entry No": e.get("entry_no",""),
            "Date": str(e.get("date","")),
            "Supplier / Description": e.get("description","")[:50],
            "Reference": e.get("reference") or "—",
            "Amount": fmt_currency(amount),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _payment_form():
    sb = get_supabase()
    suppliers = get_suppliers()
    sup_options = {f"{s['code']} — {s['name']}": s for s in suppliers}

    with st.form("payment_form"):
        st.markdown("### New Supplier Payment")
        col1, col2 = st.columns(2)
        with col1:
            sup_sel = st.selectbox("Supplier *", ["— Select —"] + list(sup_options.keys()))
        with col2:
            payment_date = st.date_input("Date *", value=date.today())

        col3, col4 = st.columns(2)
        with col3:
            amount = st.number_input("Amount (PKR) *", min_value=0.01, step=100.0, value=0.0)
        with col4:
            ref = st.text_input("Reference", placeholder="Cheque no, bank ref...")

        existing = sb.table("journal_entries").select("entry_no").ilike("entry_no","PYMT-%").execute().data or []
        nums = []
        for e in existing:
            try: nums.append(int(e["entry_no"].split("-")[1]))
            except: pass
        entry_no = f"PYMT-{max(nums, default=0)+1:04d}"
        st.caption(f"Entry No: `{entry_no}`")

        submitted = st.form_submit_button("💾 Record Payment", type="primary", use_container_width=True)
        if submitted:
            if sup_sel == "— Select —":
                st.error("Please select a supplier"); return
            if amount <= 0:
                st.error("Amount must be greater than 0"); return
            try:
                sup = sup_options[sup_sel]
                ap_acc   = sb.table("accounts").select("id,balance").eq("code","2000").execute().data[0]
                cash_acc = sb.table("accounts").select("id,balance").eq("code","1000").execute().data[0]

                je = sb.table("journal_entries").insert({
                    "entry_no": entry_no, "date": str(payment_date),
                    "description": f"Payment - {sup['name']}", "reference": ref or ""
                }).execute().data
                if je:
                    je_id = je[0]["id"]
                    sb.table("journal_lines").insert([
                        {"entry_id": je_id, "account_id": ap_acc["id"], "debit": amount, "credit": 0, "narration": f"Payment to {sup['name']}"},
                        {"entry_id": je_id, "account_id": cash_acc["id"], "debit": 0, "credit": amount, "narration": f"Payment to {sup['name']}"},
                    ]).execute()
                    sb.table("accounts").update({"balance": float(ap_acc["balance"] or 0) - amount}).eq("id", ap_acc["id"]).execute()
                    sb.table("accounts").update({"balance": float(cash_acc["balance"] or 0) - amount}).eq("id", cash_acc["id"]).execute()
                    cur_bal = float(sup.get("balance") or 0)
                    sb.table("suppliers").update({"balance": max(0, cur_bal - amount)}).eq("id", sup["id"]).execute()

                st.success(f"✅ Payment of {fmt_currency(amount)} recorded for {sup['name']}")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")
