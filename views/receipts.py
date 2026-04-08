"""
pages/receipts.py — Standalone receipt recording (not tied to specific invoice)
DR Cash / CR Accounts Receivable
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.styles import fmt_currency, page_header, section_header, GREEN, CURRENCY
from utils.db import get_supabase, get_customers

def render():
    
    page_header("Receipts", "Record customer payments", "Receipts")

    tab1, tab2 = st.tabs(["📋 Receipt History", "➕ New Receipt"])

    with tab1:
        _list_receipts()
    with tab2:
        _receipt_form()


def _list_receipts():
    sb = get_supabase()
    try:
        entries = sb.table("journal_entries").select("id,entry_no,date,description,reference").ilike("description", "Receipt%").order("date", desc=True).execute().data or []
    except Exception as e:
        st.error(f"Error: {e}"); return

    if not entries:
        st.info("No receipts recorded yet."); return

    rows = []
    for e in entries:
        lines = sb.table("journal_lines").select("debit,credit").eq("entry_id", e["id"]).execute().data or []
        amount = sum(float(l.get("debit") or 0) for l in lines) / 2 if lines else 0
        rows.append({
            "Entry No": e.get("entry_no",""),
            "Date": str(e.get("date","")),
            "Customer / Description": e.get("description","")[:50],
            "Reference": e.get("reference") or "—",
            "Amount": fmt_currency(amount),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _receipt_form():
    sb = get_supabase()
    customers = get_customers()
    cust_options = {f"{c['code']} — {c['name']}": c for c in customers}

    with st.form("receipt_form"):
        st.markdown("### New Receipt")
        col1, col2 = st.columns(2)
        with col1:
            cust_sel = st.selectbox("Customer *", ["— Select —"] + list(cust_options.keys()))
        with col2:
            receipt_date = st.date_input("Date *", value=date.today())

        col3, col4 = st.columns(2)
        with col3:
            amount = st.number_input("Amount (PKR) *", min_value=0.01, step=100.0, value=0.0)
        with col4:
            ref = st.text_input("Reference", placeholder="Cheque no, bank ref...")

        notes = st.text_input("Notes", placeholder="Additional notes...")

        # Auto-generate entry no
        existing = sb.table("journal_entries").select("entry_no").ilike("entry_no","RCPT-%").execute().data or []
        nums = []
        for e in existing:
            try: nums.append(int(e["entry_no"].split("-")[1]))
            except: pass
        entry_no = f"RCPT-{max(nums, default=0)+1:04d}"
        st.caption(f"Entry No: `{entry_no}`")

        submitted = st.form_submit_button("💾 Record Receipt", type="primary", use_container_width=True)
        if submitted:
            if cust_sel == "— Select —":
                st.error("Please select a customer"); return
            if amount <= 0:
                st.error("Amount must be greater than 0"); return
            try:
                cust = cust_options[cust_sel]
                cash_acc = sb.table("accounts").select("id,balance").eq("code","1000").execute().data[0]
                ar_acc   = sb.table("accounts").select("id,balance").eq("code","1100").execute().data[0]

                je = sb.table("journal_entries").insert({
                    "entry_no": entry_no, "date": str(receipt_date),
                    "description": f"Receipt - {cust['name']}", "reference": ref or ""
                }).execute().data
                if je:
                    je_id = je[0]["id"]
                    sb.table("journal_lines").insert([
                        {"entry_id": je_id, "account_id": cash_acc["id"], "debit": amount, "credit": 0, "narration": f"Receipt from {cust['name']}"},
                        {"entry_id": je_id, "account_id": ar_acc["id"], "debit": 0, "credit": amount, "narration": f"Receipt from {cust['name']}"},
                    ]).execute()
                    sb.table("accounts").update({"balance": float(cash_acc["balance"] or 0) + amount}).eq("id", cash_acc["id"]).execute()
                    sb.table("accounts").update({"balance": float(ar_acc["balance"] or 0) - amount}).eq("id", ar_acc["id"]).execute()
                    # Update customer balance
                    cur_bal = float(cust.get("balance") or 0)
                    sb.table("customers").update({"balance": max(0, cur_bal - amount)}).eq("id", cust["id"]).execute()

                st.success(f"✅ Receipt of {fmt_currency(amount)} recorded for {cust['name']}")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")
