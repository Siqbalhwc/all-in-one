"""
pages/accounts.py — Chart of Accounts: list, add, edit, delete
"""
import streamlit as st
import pandas as pd
from utils.styles import fmt_currency, page_header, section_header, ACCENT, GREEN, RED, YELLOW, CURRENCY
from utils.db import get_supabase, get_accounts, next_gl_code

PROTECTED = {"1000","1100","1200","2000","3000","3100","4000","5000"}

def render():
    
    page_header("Chart of Accounts", "Manage your GL accounts", "Chart of Accounts")

    tab1, tab2 = st.tabs(["📋 All Accounts", "➕ New Account"])

    with tab1:
        _list_accounts()
    with tab2:
        _account_form()


def _list_accounts():
    col_s, col_f = st.columns([3, 1])
    with col_s:
        search = st.text_input("🔍 Search accounts", placeholder="Code, name, type...", label_visibility="collapsed")
    with col_f:
        filter_type = st.selectbox("Type", ["All","Asset","Liability","Equity","Revenue","Expense"], label_visibility="collapsed")

    try:
        accounts = get_accounts()
    except Exception as e:
        st.error(f"Error: {e}"); return

    if search:
        s = search.lower()
        accounts = [a for a in accounts if s in a["code"].lower() or s in a["name"].lower() or s in a["type"].lower()]
    if filter_type != "All":
        accounts = [a for a in accounts if a["type"] == filter_type]

    if not accounts:
        st.info("No accounts found."); return

    type_colors = {"Asset": ACCENT, "Liability": RED, "Equity": "#8B5CF6", "Revenue": GREEN, "Expense": YELLOW}

    rows = []
    for a in accounts:
        rows.append({
            "Code": a["code"],
            "Account Name": a["name"],
            "Type": a["type"],
            "Opening Bal.": fmt_currency(a.get("opening_balance") or 0),
            "Balance": fmt_currency(a.get("balance") or 0),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={"Balance": st.column_config.TextColumn(width=130)})

    st.markdown("---")
    section_header("EDIT / DELETE ACCOUNT")
    acc_options = {f"{a['code']} — {a['name']}": a for a in accounts}
    selected = st.selectbox("Select account", list(acc_options.keys()))
    if selected:
        acc = acc_options[selected]
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Edit Account", use_container_width=True):
                st.session_state["edit_account"] = acc
                st.rerun()
        with col2:
            if acc["code"] not in PROTECTED:
                if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
                    _delete_account(acc)

    if "edit_account" in st.session_state:
        _account_form(mode="edit", data=st.session_state["edit_account"])


def _account_form(mode="new", data=None):
    sb = get_supabase()
    with st.form("account_form"):
        st.markdown(f"### {'Edit Account' if mode=='edit' else 'New Account'}")

        acc_type = st.selectbox("Account Type *", ["Asset","Liability","Equity","Revenue","Expense"],
                                index=["Asset","Liability","Equity","Revenue","Expense"].index(data["type"]) if data else 0)
        ranges = {"Asset":"1000-1999","Liability":"2000-2999","Equity":"3000-3999","Revenue":"4000-4999","Expense":"5000-5999"}
        st.caption(f"Standard range for {acc_type}: {ranges.get(acc_type,'')}")

        col1, col2 = st.columns(2)
        with col1:
            suggested = next_gl_code(acc_type) if mode=="new" else (data["code"] if data else "")
            code = st.text_input("Account Code *", value=suggested)
        with col2:
            name = st.text_input("Account Name *", value=data["name"] if data else "")

        ob = st.number_input("Opening Balance (PKR)", min_value=0.0, step=100.0,
                             value=float(data.get("opening_balance") or 0) if data else 0.0)

        submitted = st.form_submit_button("💾 Save Account", type="primary")
        if submitted:
            if not code.strip() or not name.strip():
                st.error("Code and name are required"); return
            try:
                if mode == "new":
                    sb.table("accounts").insert({
                        "code": code.strip(), "name": name.strip(),
                        "type": acc_type, "opening_balance": ob, "balance": ob
                    }).execute()
                    st.success(f"✅ Account '{name}' created!")
                else:
                    sb.table("accounts").update({
                        "code": code.strip(), "name": name.strip(),
                        "type": acc_type, "opening_balance": ob
                    }).eq("id", data["id"]).execute()
                    if "edit_account" in st.session_state:
                        del st.session_state["edit_account"]
                    st.success(f"✅ Account '{name}' updated!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")


def _delete_account(acc):
    if acc["code"] in PROTECTED:
        st.error("This is a system account and cannot be deleted."); return
    sb = get_supabase()
    try:
        sb.table("journal_lines").delete().eq("account_id", acc["id"]).execute()
        sb.table("accounts").delete().eq("id", acc["id"]).execute()
        st.success(f"✅ Account '{acc['code']} — {acc['name']}' deleted.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")
