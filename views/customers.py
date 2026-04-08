"""
pages/customers.py — Customers: list, add, edit, delete with GL balance
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.styles import fmt_currency, page_header, section_header, ACCENT, GREEN, RED, CYAN, CURRENCY
from utils.db import get_supabase, get_customers, next_customer_code, compute_customer_balance

def render():
    
    page_header("Customers", "Manage customers and receivables", "Customers")

    tab1, tab2 = st.tabs(["👥 Customer List", "➕ Add Customer"])

    with tab1:
        _list_customers()
    with tab2:
        _customer_form()


def _list_customers():
    search = st.text_input("🔍 Search customers", placeholder="Name, code, phone...", label_visibility="collapsed")

    try:
        customers = get_customers()
    except Exception as e:
        st.error(f"Error: {e}"); return

    if search:
        s = search.lower()
        customers = [c for c in customers if s in c["name"].lower() or s in (c["code"] or "").lower()
                     or s in (c.get("phone") or "").lower()]

    if not customers:
        st.info("No customers yet. Add your first customer above."); return

    # Summary KPIs
    total_bal = sum(float(c.get("balance") or 0) for c in customers)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Customers", len(customers))
    with col2:
        st.metric("Total Outstanding", fmt_currency(total_bal, compact=True))
    with col3:
        owing = sum(1 for c in customers if float(c.get("balance") or 0) > 0)
        st.metric("Customers with Balance", owing)

    rows = []
    for c in customers:
        rows.append({
            "Code": c["code"],
            "Name": c["name"],
            "Phone": c.get("phone") or "—",
            "Email": c.get("email") or "—",
            "Address": (c.get("address") or "—")[:30],
            "Balance": fmt_currency(c.get("balance") or 0),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    section_header("EDIT / DELETE CUSTOMER")
    cust_options = {f"{c['code']} — {c['name']}": c for c in customers}
    selected = st.selectbox("Select customer", list(cust_options.keys()))
    if selected:
        cust = cust_options[selected]
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state["edit_customer"] = cust
                st.rerun()
        with c2:
            if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                _delete_customer(cust)
        with c3:
            if st.button("🔄 Recalc Balance", use_container_width=True):
                _recalc_balance(cust)

    if "edit_customer" in st.session_state:
        _customer_form(mode="edit", data=st.session_state["edit_customer"])


def _customer_form(mode="new", data=None):
    sb = get_supabase()
    title = "Edit Customer" if mode == "edit" else "New Customer"

    with st.form(f"customer_form_{mode}"):
        st.markdown(f"### {title}")
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("Code *", value=data["code"] if data else next_customer_code())
            phone = st.text_input("Phone", value=data.get("phone") or "" if data else "")
        with col2:
            name = st.text_input("Name *", value=data["name"] if data else "")
            email = st.text_input("Email", value=data.get("email") or "" if data else "")

        address = st.text_input("Address", value=data.get("address") or "" if data else "")
        ob = st.number_input("Opening Balance (PKR)", min_value=0.0, step=100.0,
                             value=float(data.get("balance") or 0) if data else 0.0)
        if mode == "new":
            st.caption("💡 Opening balance posts: DR Accounts Receivable (1100) / CR Owner Equity (3000)")

        submitted = st.form_submit_button("💾 Save Customer", type="primary")
        if submitted:
            if not name.strip():
                st.error("Customer name is required"); return
            if not code.strip():
                st.error("Customer code is required"); return
            try:
                row_data = {
                    "code": code.strip(), "name": name.strip(),
                    "phone": phone, "email": email, "address": address, "balance": ob
                }
                if mode == "new":
                    res = sb.table("customers").insert(row_data).execute()
                    cust_id = res.data[0]["id"]
                    # Post opening balance GL entry
                    if ob > 0:
                        _post_customer_ob(sb, cust_id, name.strip(), ob)
                    st.success(f"✅ Customer '{name}' added!")
                else:
                    sb.table("customers").update(row_data).eq("id", data["id"]).execute()
                    if "edit_customer" in st.session_state:
                        del st.session_state["edit_customer"]
                    st.success(f"✅ Customer '{name}' updated!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")

    if mode == "edit" and st.button("✕ Cancel Edit"):
        if "edit_customer" in st.session_state:
            del st.session_state["edit_customer"]
        st.rerun()


def _post_customer_ob(sb, cust_id, cust_name, amount):
    ar = sb.table("accounts").select("id,balance").eq("code","1100").execute().data
    eq = sb.table("accounts").select("id,balance").eq("code","3000").execute().data
    if not ar or not eq: return
    ar_id = ar[0]["id"]; eq_id = eq[0]["id"]
    je_no = f"OB-CUST-{cust_id}"
    je = sb.table("journal_entries").insert({
        "entry_no": je_no, "date": date.today().isoformat(),
        "description": f"Opening Balance - {cust_name}", "reference": "Opening Balance"
    }).execute().data
    if je:
        je_id = je[0]["id"]
        sb.table("journal_lines").insert({"entry_id": je_id, "account_id": ar_id, "debit": amount, "credit": 0, "narration": f"OB - {cust_name}"}).execute()
        sb.table("journal_lines").insert({"entry_id": je_id, "account_id": eq_id, "debit": 0, "credit": amount, "narration": f"OB Offset - {cust_name}"}).execute()
        sb.table("accounts").update({"balance": float(ar[0].get("balance") or 0) + amount}).eq("id", ar_id).execute()
        sb.table("accounts").update({"balance": float(eq[0].get("balance") or 0) + amount}).eq("id", eq_id).execute()


def _delete_customer(cust):
    sb = get_supabase()
    try:
        sb.table("customers").delete().eq("id", cust["id"]).execute()
        st.success(f"✅ Customer '{cust['name']}' deleted.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")


def _recalc_balance(cust):
    sb = get_supabase()
    try:
        new_bal = compute_customer_balance(cust["id"], cust["name"])
        sb.table("customers").update({"balance": new_bal}).eq("id", cust["id"]).execute()
        st.success(f"✅ Balance recalculated: {fmt_currency(new_bal)}")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")
