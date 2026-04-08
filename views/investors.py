"""
pages/investors.py — Investors management and capital tracking
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.styles import fmt_currency, page_header, section_header, PURPLE, CURRENCY
from utils.db import get_supabase, get_investors, next_investor_code, get_products

def render():
    
    page_header("Investors", "Manage investors and their capital", "Investors")

    tab1, tab2 = st.tabs(["💼 Investor List", "➕ Add Investor"])

    with tab1:
        _list_investors()
    with tab2:
        _investor_form()


def _list_investors():
    try:
        investors = get_investors()
    except Exception as e:
        st.error(f"Error: {e}"); return

    if not investors:
        st.info("No investors yet."); return

    total_investment = sum(float(i.get("investment_amount") or 0) for i in investors)
    col1, col2 = st.columns(2)
    with col1: st.metric("Total Investors", len(investors))
    with col2: st.metric("Total Investment", fmt_currency(total_investment, compact=True))

    # Get product counts per investor
    sb = get_supabase()
    products = get_products()
    prod_by_inv = {}
    for p in products:
        inv_id = p.get("investor_id")
        if inv_id:
            if inv_id not in prod_by_inv:
                prod_by_inv[inv_id] = {"count": 0, "value": 0.0}
            prod_by_inv[inv_id]["count"] += 1
            prod_by_inv[inv_id]["value"] += float(p.get("qty_on_hand") or 0) * float(p.get("cost_price") or 0)

    rows = []
    for inv in investors:
        inv_products = prod_by_inv.get(inv["id"], {"count": 0, "value": 0.0})
        rows.append({
            "Code": inv["code"],
            "Name": inv["name"],
            "Phone": inv.get("phone") or "—",
            "Email": inv.get("email") or "—",
            "Investment": fmt_currency(inv.get("investment_amount") or 0),
            "Products": inv_products["count"],
            "Stock Value": fmt_currency(inv_products["value"]),
            "Notes": (inv.get("notes") or "—")[:30],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    section_header("EDIT / DELETE INVESTOR")
    options = {f"{i['code']} — {i['name']}": i for i in investors}
    selected = st.selectbox("Select investor", list(options.keys()))
    if selected:
        inv = options[selected]
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state["edit_investor"] = inv
                st.rerun()
        with c2:
            if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                _delete_investor(inv)

    if "edit_investor" in st.session_state:
        _investor_form(mode="edit", data=st.session_state["edit_investor"])


def _investor_form(mode="new", data=None):
    sb = get_supabase()
    with st.form(f"investor_form_{mode}"):
        st.markdown(f"### {'Edit' if mode=='edit' else 'New'} Investor")
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("Code *", value=data["code"] if data else next_investor_code())
            phone = st.text_input("Phone", value=data.get("phone") or "" if data else "")
        with col2:
            name = st.text_input("Name *", value=data["name"] if data else "")
            email = st.text_input("Email", value=data.get("email") or "" if data else "")

        investment = st.number_input("Investment Amount (PKR)", min_value=0.0, step=1000.0,
                                     value=float(data.get("investment_amount") or 0) if data else 0.0)
        notes = st.text_area("Notes", value=data.get("notes") or "" if data else "", height=80)

        submitted = st.form_submit_button("💾 Save Investor", type="primary")
        if submitted:
            if not name.strip() or not code.strip():
                st.error("Code and name are required"); return
            try:
                row_data = {
                    "code": code.strip(), "name": name.strip(),
                    "phone": phone, "email": email,
                    "investment_amount": investment, "notes": notes
                }
                if mode == "new":
                    res = sb.table("investors").insert(row_data).execute()
                    inv_id = res.data[0]["id"]
                    # Post capital contribution to GL
                    if investment > 0:
                        _post_investor_capital(sb, inv_id, name.strip(), investment)
                    st.success(f"✅ Investor '{name}' added!")
                else:
                    sb.table("investors").update(row_data).eq("id", data["id"]).execute()
                    if "edit_investor" in st.session_state:
                        del st.session_state["edit_investor"]
                    st.success(f"✅ Investor '{name}' updated!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")

    if mode == "edit" and st.button("✕ Cancel Edit"):
        if "edit_investor" in st.session_state:
            del st.session_state["edit_investor"]
        st.rerun()


def _post_investor_capital(sb, inv_id, inv_name, amount):
    cash = sb.table("accounts").select("id,balance").eq("code","1000").execute().data
    eq   = sb.table("accounts").select("id,balance").eq("code","3000").execute().data
    if not cash or not eq: return
    cash_id = cash[0]["id"]; eq_id = eq[0]["id"]
    je = sb.table("journal_entries").insert({
        "entry_no": f"CAPINV-{inv_id}", "date": date.today().isoformat(),
        "description": f"Capital Investment - {inv_name}", "reference": "Investment"
    }).execute().data
    if je:
        je_id = je[0]["id"]
        sb.table("journal_lines").insert([
            {"entry_id": je_id, "account_id": cash_id, "debit": amount, "credit": 0, "narration": f"Capital - {inv_name}"},
            {"entry_id": je_id, "account_id": eq_id, "debit": 0, "credit": amount, "narration": f"Capital - {inv_name}"},
        ]).execute()
        sb.table("accounts").update({"balance": float(cash[0].get("balance") or 0) + amount}).eq("id", cash_id).execute()
        sb.table("accounts").update({"balance": float(eq[0].get("balance") or 0) + amount}).eq("id", eq_id).execute()


def _delete_investor(inv):
    sb = get_supabase()
    try:
        sb.table("investors").delete().eq("id", inv["id"]).execute()
        st.success(f"✅ Investor '{inv['name']}' deleted.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")
