"""
pages/invoices.py — Sales Invoices & Purchase Bills
Full GL posting: DR AR / CR Revenue / DR COGS for sales
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.styles import fmt_currency, page_header, section_header, status_badge, ACCENT, GREEN, RED, YELLOW, AMBER, CURRENCY
from utils.db import (get_supabase, get_invoices, get_invoice_with_items,
                      get_customers, get_suppliers, get_products,
                      next_invoice_no, get_accounts)

def render(inv_type: str = "sale"):
    
    is_sale = inv_type == "sale"
    title   = "Sales Invoices" if is_sale else "Purchase Bills"
    sub     = "Create and manage customer invoices" if is_sale else "Create and manage supplier bills"
    page_header(title, sub, title)

    tab1, tab2 = st.tabs([f"📋 {'Invoices' if is_sale else 'Bills'}", "➕ New"])

    with tab1:
        _list_invoices(inv_type)
    with tab2:
        _invoice_form(inv_type)


def _list_invoices(inv_type):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("🔍 Search", placeholder="Invoice no, party...", label_visibility="collapsed")
    with col2:
        status_filter = st.selectbox("Status", ["All","Unpaid","Partial","Paid"], label_visibility="collapsed")
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    try:
        invoices = get_invoices(inv_type=inv_type)
    except Exception as e:
        st.error(f"Error: {e}"); return

    if status_filter != "All":
        invoices = [i for i in invoices if i.get("status") == status_filter]
    if search:
        s = search.lower()
        invoices = [i for i in invoices if s in (i.get("invoice_no") or "").lower()
                    or s in str(i.get("party_id") or "").lower()
                    or s in (i.get("reference") or "").lower()]

    # KPI summary
    total_amt  = sum(float(i.get("total") or 0) for i in invoices)
    total_paid = sum(float(i.get("paid") or 0) for i in invoices)
    total_due  = total_amt - total_paid
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Invoices", len(invoices))
    with c2: st.metric("Total Amount", fmt_currency(total_amt, compact=True))
    with c3: st.metric("Total Paid", fmt_currency(total_paid, compact=True))
    with c4: st.metric("Outstanding", fmt_currency(total_due, compact=True))

    if not invoices:
        st.info(f"No {'invoices' if inv_type=='sale' else 'bills'} found."); return

    # Build party lookup
    sb = get_supabase()
    if inv_type == "sale":
        parties = {c["id"]: c["name"] for c in (sb.table("customers").select("id,name").execute().data or [])}
    else:
        parties = {s["id"]: s["name"] for s in (sb.table("suppliers").select("id,name").execute().data or [])}

    rows = []
    for inv in invoices:
        total = float(inv.get("total") or 0)
        paid  = float(inv.get("paid") or 0)
        due   = total - paid
        rows.append({
            "Invoice No": inv.get("invoice_no",""),
            "Party": parties.get(inv.get("party_id"),"—"),
            "Date": str(inv.get("date","")),
            "Due Date": str(inv.get("due_date") or "—"),
            "Total": fmt_currency(total),
            "Paid": fmt_currency(paid),
            "Due": fmt_currency(due),
            "Status": inv.get("status",""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── View invoice detail + payment ─────────────────────────────────────────
    st.markdown("---")
    section_header("VIEW INVOICE / RECORD PAYMENT")
    inv_options = {i.get("invoice_no","?"): i for i in invoices}
    selected_no = st.selectbox("Select invoice", list(inv_options.keys()))
    if selected_no:
        inv = inv_options[selected_no]
        _show_invoice_detail(inv, inv_type, parties)


def _show_invoice_detail(inv, inv_type, parties):
    sb = get_supabase()
    inv_obj, items = get_invoice_with_items(inv["id"])
    if not inv_obj: return

    total = float(inv_obj.get("total") or 0)
    paid  = float(inv_obj.get("paid") or 0)
    due   = total - paid

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f"**Invoice:** `{inv_obj.get('invoice_no')}`")
    with col2: st.markdown(f"**Party:** {parties.get(inv_obj.get('party_id'),'—')}")
    with col3: st.markdown(f"**Date:** {inv_obj.get('date')}")
    with col4: st.markdown(f"**Status:** {inv_obj.get('status')}")

    if items:
        item_rows = [{
            "Description": it.get("description",""),
            "Qty": it.get("qty",0),
            "Unit Price": fmt_currency(it.get("unit_price",0)),
            "Total": fmt_currency(it.get("total",0)),
        } for it in items]
        st.dataframe(pd.DataFrame(item_rows), use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Total", fmt_currency(total))
    with c2: st.metric("Paid", fmt_currency(paid))
    with c3: st.metric("Due", fmt_currency(due))

    # Record payment
    if due > 0.01:
        with st.expander("💰 Record Payment"):
            with st.form(f"payment_{inv['id']}"):
                pay_amt = st.number_input("Payment Amount", min_value=0.01, max_value=due, value=due, step=100.0)
                pay_ref = st.text_input("Reference (cheque/bank)", placeholder="CHQ-001")
                pay_date = st.date_input("Payment Date", value=date.today())
                if st.form_submit_button("✅ Record Payment", type="primary"):
                    _record_payment(sb, inv_obj, inv_type, pay_amt, pay_ref, str(pay_date), parties)

    with st.expander("⚠️ Delete Invoice"):
        st.warning("This will permanently delete this invoice and reverse all GL entries.")
        if st.button(f"🗑️ Delete {inv_obj.get('invoice_no')}", key=f"delinv_{inv['id']}"):
            _delete_invoice(sb, inv_obj, inv_type)


def _record_payment(sb, inv, inv_type, amount, ref, pay_date, parties):
    try:
        new_paid = float(inv.get("paid") or 0) + amount
        total    = float(inv.get("total") or 0)
        status   = "Paid" if new_paid >= total - 0.01 else "Partial"
        sb.table("invoices").update({"paid": new_paid, "status": status}).eq("id", inv["id"]).execute()

        # GL entry
        party_name = parties.get(inv.get("party_id"), "Party")
        if inv_type == "sale":
            # DR Cash / CR AR
            cash_acc = sb.table("accounts").select("id,balance").eq("code","1000").execute().data[0]
            ar_acc   = sb.table("accounts").select("id,balance").eq("code","1100").execute().data[0]
            je = sb.table("journal_entries").insert({
                "entry_no": f"RCPT-{inv['invoice_no']}", "date": pay_date,
                "description": f"Receipt - {party_name}", "reference": ref or ""
            }).execute().data
            if je:
                je_id = je[0]["id"]
                sb.table("journal_lines").insert([
                    {"entry_id": je_id, "account_id": cash_acc["id"], "debit": amount, "credit": 0, "narration": f"Receipt - {party_name}"},
                    {"entry_id": je_id, "account_id": ar_acc["id"], "debit": 0, "credit": amount, "narration": f"Receipt - {party_name}"},
                ]).execute()
                sb.table("accounts").update({"balance": float(cash_acc["balance"] or 0) + amount}).eq("id", cash_acc["id"]).execute()
                sb.table("accounts").update({"balance": float(ar_acc["balance"] or 0) - amount}).eq("id", ar_acc["id"]).execute()
        else:
            # DR AP / CR Cash
            ap_acc   = sb.table("accounts").select("id,balance").eq("code","2000").execute().data[0]
            cash_acc = sb.table("accounts").select("id,balance").eq("code","1000").execute().data[0]
            je = sb.table("journal_entries").insert({
                "entry_no": f"PYMT-{inv['invoice_no']}", "date": pay_date,
                "description": f"Payment - {party_name}", "reference": ref or ""
            }).execute().data
            if je:
                je_id = je[0]["id"]
                sb.table("journal_lines").insert([
                    {"entry_id": je_id, "account_id": ap_acc["id"], "debit": amount, "credit": 0, "narration": f"Payment - {party_name}"},
                    {"entry_id": je_id, "account_id": cash_acc["id"], "debit": 0, "credit": amount, "narration": f"Payment - {party_name}"},
                ]).execute()
                sb.table("accounts").update({"balance": float(ap_acc["balance"] or 0) - amount}).eq("id", ap_acc["id"]).execute()
                sb.table("accounts").update({"balance": float(cash_acc["balance"] or 0) - amount}).eq("id", cash_acc["id"]).execute()

        st.success(f"✅ Payment of {fmt_currency(amount)} recorded. Status: {status}")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")


def _delete_invoice(sb, inv, inv_type):
    try:
        sb.table("invoice_items").delete().eq("invoice_id", inv["id"]).execute()
        prefix = "JE-SI-" if inv_type == "sale" else "JE-PI-"
        inv_no = inv.get("invoice_no","")
        for pref in ([prefix, "JE-COGS-"] if inv_type == "sale" else [prefix]):
            jes = sb.table("journal_entries").select("id").ilike("entry_no", f"{pref}{inv_no}%").execute().data or []
            for je in jes:
                sb.table("journal_lines").delete().eq("entry_id", je["id"]).execute()
                sb.table("journal_entries").delete().eq("id", je["id"]).execute()
        sb.table("invoices").delete().eq("id", inv["id"]).execute()
        st.success(f"✅ Invoice {inv_no} deleted.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")


def _invoice_form(inv_type):
    sb = get_supabase()
    is_sale = inv_type == "sale"

    parties = get_customers() if is_sale else get_suppliers()
    products = get_products()
    party_options = {f"{p['code']} — {p['name']}": p for p in parties}
    prod_options  = {f"{p['code']} — {p['name']}": p for p in products}

    with st.form("invoice_form"):
        st.markdown(f"### New {'Sales Invoice' if is_sale else 'Purchase Bill'}")
        col1, col2, col3 = st.columns(3)
        with col1:
            inv_no = st.text_input("Invoice No *", value=next_invoice_no(inv_type))
        with col2:
            inv_date = st.date_input("Date *", value=date.today())
        with col3:
            due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30))

        col4, col5 = st.columns(2)
        with col4:
            party_sel = st.selectbox(f"{'Customer' if is_sale else 'Supplier'} *", ["— Select —"] + list(party_options.keys()))
        with col5:
            ref = st.text_input("Reference", placeholder="PO No, Challan...")

        notes = st.text_area("Notes", height=60)

        section_header("LINE ITEMS")
        items_data = []
        grand_total = 0.0

        for i in range(1, 9):
            c1, c2, c3, c4 = st.columns([3, 1, 1.5, 1.5])
            with c1:
                prod_sel = st.selectbox(f"Item {i}", ["— Select / Type Description —"] + list(prod_options.keys()), key=f"inv_prod_{i}")
            with c2:
                qty = st.number_input(f"Qty {i}", min_value=0.0, step=1.0, value=0.0, key=f"inv_qty_{i}", label_visibility="collapsed" if i > 1 else "visible")
            with c3:
                if prod_sel != "— Select / Type Description —":
                    default_price = float(prod_options[prod_sel].get("sale_price" if is_sale else "cost_price") or 0)
                else:
                    default_price = 0.0
                price = st.number_input(f"Price {i}", min_value=0.0, step=100.0, value=default_price, key=f"inv_price_{i}", label_visibility="collapsed" if i > 1 else "visible")
            with c4:
                line_total = qty * price
                st.markdown(f"<div style='padding-top:28px;font-weight:600;color:#3D5AF1;'>{fmt_currency(line_total)}</div>" if i == 1 else f"<div style='padding-top:8px;font-weight:600;color:#3D5AF1;'>{fmt_currency(line_total)}</div>", unsafe_allow_html=True)

            if qty > 0 and price > 0:
                desc = prod_sel if prod_sel != "— Select / Type Description —" else f"Item {i}"
                prod_id = prod_options[prod_sel]["id"] if prod_sel != "— Select / Type Description —" else None
                items_data.append({"product_id": prod_id, "description": desc, "qty": qty, "unit_price": price, "total": line_total})
                grand_total += line_total

        st.markdown(f"**Grand Total: {fmt_currency(grand_total)}**")

        submitted = st.form_submit_button("💾 Save & Post Invoice", type="primary", use_container_width=True)

        if submitted:
            if party_sel == "— Select —":
                st.error("Please select a customer/supplier"); return
            if not items_data:
                st.error("Add at least one line item"); return
            if not inv_no.strip():
                st.error("Invoice number is required"); return
            try:
                party_id = party_options[party_sel]["id"]
                inv_data = {
                    "invoice_no": inv_no.strip(), "type": inv_type, "party_id": party_id,
                    "date": str(inv_date), "due_date": str(due_date),
                    "total": grand_total, "paid": 0, "status": "Unpaid",
                    "notes": notes, "reference": ref
                }
                res = sb.table("invoices").insert(inv_data).execute()
                inv_id = res.data[0]["id"]

                for it in items_data:
                    it["invoice_id"] = inv_id
                    sb.table("invoice_items").insert(it).execute()
                    # Update stock
                    if it.get("product_id"):
                        prod = sb.table("products").select("qty_on_hand").eq("id", it["product_id"]).execute().data
                        if prod:
                            new_qty = float(prod[0].get("qty_on_hand") or 0)
                            new_qty += it["qty"] if not is_sale else -it["qty"]
                            sb.table("products").update({"qty_on_hand": max(0, new_qty)}).eq("id", it["product_id"]).execute()
                            sb.table("stock_moves").insert({
                                "product_id": it["product_id"], "move_type": inv_type,
                                "qty": it["qty"], "unit_price": it["unit_price"],
                                "ref": inv_no, "date": str(inv_date)
                            }).execute()

                # Post GL entry
                _post_invoice_gl(sb, inv_id, inv_type, inv_no.strip(), party_id, party_options[party_sel], grand_total, str(inv_date))
                st.success(f"✅ Invoice {inv_no} saved and posted to GL!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")


def _post_invoice_gl(sb, inv_id, inv_type, inv_no, party_id, party, grand_total, inv_date):
    party_name = party.get("name","Party")
    if inv_type == "sale":
        ar  = sb.table("accounts").select("id,balance").eq("code","1100").execute().data[0]
        rev = sb.table("accounts").select("id,balance").eq("code","4000").execute().data[0]
        je = sb.table("journal_entries").insert({
            "entry_no": f"JE-SI-{inv_no}", "date": inv_date,
            "description": f"Sales Invoice - {party_name}", "reference": inv_no
        }).execute().data
        if je:
            je_id = je[0]["id"]
            sb.table("journal_lines").insert([
                {"entry_id": je_id, "account_id": ar["id"], "debit": grand_total, "credit": 0, "narration": f"Invoice {inv_no}"},
                {"entry_id": je_id, "account_id": rev["id"], "debit": 0, "credit": grand_total, "narration": f"Sales {inv_no}"},
            ]).execute()
            sb.table("accounts").update({"balance": float(ar["balance"] or 0) + grand_total}).eq("id", ar["id"]).execute()
            sb.table("accounts").update({"balance": float(rev["balance"] or 0) + grand_total}).eq("id", rev["id"]).execute()
        # Customer balance
        sb.table("customers").update({"balance": sb.table("customers").select("balance").eq("id", party_id).execute().data[0].get("balance", 0) + grand_total}).eq("id", party_id).execute()
    else:
        inv_acc = sb.table("accounts").select("id,balance").eq("code","1200").execute().data[0]
        ap  = sb.table("accounts").select("id,balance").eq("code","2000").execute().data[0]
        je = sb.table("journal_entries").insert({
            "entry_no": f"JE-PI-{inv_no}", "date": inv_date,
            "description": f"Purchase Bill - {party_name}", "reference": inv_no
        }).execute().data
        if je:
            je_id = je[0]["id"]
            sb.table("journal_lines").insert([
                {"entry_id": je_id, "account_id": inv_acc["id"], "debit": grand_total, "credit": 0, "narration": f"Purchase {inv_no}"},
                {"entry_id": je_id, "account_id": ap["id"], "debit": 0, "credit": grand_total, "narration": f"Invoice {inv_no}"},
            ]).execute()
            sb.table("accounts").update({"balance": float(inv_acc["balance"] or 0) + grand_total}).eq("id", inv_acc["id"]).execute()
            sb.table("accounts").update({"balance": float(ap["balance"] or 0) + grand_total}).eq("id", ap["id"]).execute()
        # Supplier balance
        sup_bal = sb.table("suppliers").select("balance").eq("id", party_id).execute().data[0].get("balance", 0)
        sb.table("suppliers").update({"balance": float(sup_bal or 0) + grand_total}).eq("id", party_id).execute()
