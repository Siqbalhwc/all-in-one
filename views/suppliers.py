"""
pages/suppliers.py — Suppliers: list, add, edit, delete
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.styles import fmt_currency, page_header, section_header, GREEN, RED, AMBER, CURRENCY
from utils.db import get_supabase, get_suppliers, next_supplier_code

def render():
    
    page_header("Suppliers", "Manage suppliers and payables", "Suppliers")

    tab1, tab2 = st.tabs(["🏭 Supplier List", "➕ Add Supplier"])

    with tab1:
        _list_suppliers()
    with tab2:
        _supplier_form()


def _list_suppliers():
    search = st.text_input("🔍 Search suppliers", placeholder="Name, code, phone...", label_visibility="collapsed")
    try:
        suppliers = get_suppliers()
    except Exception as e:
        st.error(f"Error: {e}"); return

    if search:
        s = search.lower()
        suppliers = [x for x in suppliers if s in x["name"].lower() or s in (x.get("code") or "").lower()
                     or s in (x.get("phone") or "").lower()]

    if not suppliers:
        st.info("No suppliers yet."); return

    total_bal = sum(float(x.get("balance") or 0) for x in suppliers)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Suppliers", len(suppliers))
    with col2:
        st.metric("Total Payable", fmt_currency(total_bal, compact=True))

    rows = []
    for s in suppliers:
        rows.append({
            "Code": s["code"], "Name": s["name"],
            "Phone": s.get("phone") or "—", "Email": s.get("email") or "—",
            "Address": (s.get("address") or "—")[:30],
            "Balance": fmt_currency(s.get("balance") or 0),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    section_header("EDIT / DELETE SUPPLIER")
    options = {f"{s['code']} — {s['name']}": s for s in suppliers}
    selected = st.selectbox("Select supplier", list(options.keys()))
    if selected:
        sup = options[selected]
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state["edit_supplier"] = sup
                st.rerun()
        with c2:
            if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                _delete_supplier(sup)

    if "edit_supplier" in st.session_state:
        _supplier_form(mode="edit", data=st.session_state["edit_supplier"])


def _supplier_form(mode="new", data=None):
    sb = get_supabase()
    with st.form(f"supplier_form_{mode}"):
        st.markdown(f"### {'Edit' if mode=='edit' else 'New'} Supplier")
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("Code *", value=data["code"] if data else next_supplier_code())
            phone = st.text_input("Phone", value=data.get("phone") or "" if data else "")
        with col2:
            name = st.text_input("Name *", value=data["name"] if data else "")
            email = st.text_input("Email", value=data.get("email") or "" if data else "")
        address = st.text_input("Address", value=data.get("address") or "" if data else "")
        ob = st.number_input("Opening Balance (PKR)", min_value=0.0, step=100.0,
                             value=float(data.get("balance") or 0) if data else 0.0)
        if mode == "new":
            st.caption("💡 Opening balance posts: DR Owner Equity (3000) / CR Accounts Payable (2000)")

        submitted = st.form_submit_button("💾 Save Supplier", type="primary")
        if submitted:
            if not name.strip() or not code.strip():
                st.error("Code and name are required"); return
            try:
                row_data = {"code": code.strip(), "name": name.strip(),
                            "phone": phone, "email": email, "address": address, "balance": ob}
                if mode == "new":
                    res = sb.table("suppliers").insert(row_data).execute()
                    sup_id = res.data[0]["id"]
                    if ob > 0:
                        _post_supplier_ob(sb, sup_id, name.strip(), ob)
                    st.success(f"✅ Supplier '{name}' added!")
                else:
                    sb.table("suppliers").update(row_data).eq("id", data["id"]).execute()
                    if "edit_supplier" in st.session_state:
                        del st.session_state["edit_supplier"]
                    st.success(f"✅ Supplier '{name}' updated!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")

    if mode == "edit" and st.button("✕ Cancel Edit"):
        if "edit_supplier" in st.session_state:
            del st.session_state["edit_supplier"]
        st.rerun()


def _post_supplier_ob(sb, sup_id, sup_name, amount):
    ap = sb.table("accounts").select("id,balance").eq("code","2000").execute().data
    eq = sb.table("accounts").select("id,balance").eq("code","3000").execute().data
    if not ap or not eq: return
    ap_id = ap[0]["id"]; eq_id = eq[0]["id"]
    je = sb.table("journal_entries").insert({
        "entry_no": f"OB-SUPP-{sup_id}", "date": date.today().isoformat(),
        "description": f"Opening Balance - {sup_name}", "reference": "Opening Balance"
    }).execute().data
    if je:
        je_id = je[0]["id"]
        sb.table("journal_lines").insert({"entry_id": je_id, "account_id": eq_id, "debit": amount, "credit": 0, "narration": f"OB Offset - {sup_name}"}).execute()
        sb.table("journal_lines").insert({"entry_id": je_id, "account_id": ap_id, "debit": 0, "credit": amount, "narration": f"OB - {sup_name}"}).execute()
        sb.table("accounts").update({"balance": float(eq[0].get("balance") or 0) - amount}).eq("id", eq_id).execute()
        sb.table("accounts").update({"balance": float(ap[0].get("balance") or 0) + amount}).eq("id", ap_id).execute()


def _delete_supplier(sup):
    sb = get_supabase()
    try:
        sb.table("suppliers").delete().eq("id", sup["id"]).execute()
        st.success(f"✅ Supplier '{sup['name']}' deleted.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")
