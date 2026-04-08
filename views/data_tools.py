"""
pages/data_tools.py — Data Tools: Opening Inventory, Clear Invoices, Clear Journal
Mirrors the desktop app's DataToolsFrame exactly.
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.styles import fmt_currency, page_header, section_header, RED, YELLOW, GREEN, PURPLE, CURRENCY
from utils.db import get_supabase, get_products, get_investors

def render():
    
    page_header("Data Tools", "Opening balances, data resets, and maintenance tools", "Data Tools")

    st.warning("⚠️ **These tools make permanent changes.** Always backup your data before using.")

    tab1, tab2, tab3 = st.tabs(["📦 Opening Inventory Entry", "🗑️ Clear Invoices", "🔄 Clear Journal"])

    with tab1:
        _opening_inventory()
    with tab2:
        _clear_invoices()
    with tab3:
        _clear_journal()


# ─── Opening Inventory Entry ─────────────────────────────────────────────────
def _opening_inventory():
    section_header("POST OPENING INVENTORY JOURNAL ENTRY")
    st.info("This posts a single journal entry: DR Inventory (1200) / CR Capital accounts per investor.")

    try:
        products = get_products()
        investors = get_investors()
    except Exception as e:
        st.error(f"Error: {e}"); return

    if not products:
        st.info("No products found. Add products first."); return

    # Preview table
    rows = []
    grand_total = 0.0
    inv_groups = {}

    for p in products:
        opening = float(p.get("opening_qty") or 0)
        cost    = float(p.get("cost_price") or 0)
        value   = opening * cost
        if value <= 0: continue
        investor = (p.get("investors") or {})
        inv_name = investor.get("name") or "General"
        inv_code = f"CAP-{inv_name.upper().replace(' ','-')[:8]}"

        if inv_name not in inv_groups:
            inv_groups[inv_name] = {"total": 0.0, "cap_code": inv_code, "cap_name": f"Capital - {inv_name}"}
        inv_groups[inv_name]["total"] += value
        grand_total += value

        rows.append({
            "Product": p["name"], "Code": p["code"],
            "Opening Qty": f"{opening:,.0f}",
            "Cost Price": fmt_currency(cost),
            "Value": fmt_currency(value),
            "Investor": inv_name,
        })

    if not rows:
        st.info("No products with opening qty × cost price > 0. Set opening quantities and cost prices first.")
        return

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown(f"**Grand Total: {fmt_currency(grand_total)}**")

    st.markdown("**Journal Entry Preview:**")
    preview_rows = [{"Account": "1200 — Inventory", "Debit": fmt_currency(grand_total), "Credit": "—"}]
    for inv_name, g in inv_groups.items():
        preview_rows.append({"Account": f"{g['cap_code']} — {g['cap_name']}", "Debit": "—", "Credit": fmt_currency(g["total"])})
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    je_no = "JE-OPEN-INV"
    if st.button(f"📮 Post Opening Inventory Entry ({je_no})", type="primary"):
        _post_opening_inventory(grand_total, inv_groups, je_no)


def _post_opening_inventory(grand_total, groups, je_no):
    sb = get_supabase()
    try:
        # Delete existing if any
        existing = sb.table("journal_entries").select("id").eq("entry_no", je_no).execute().data
        if existing:
            je_id = existing[0]["id"]
            sb.table("journal_lines").delete().eq("entry_id", je_id).execute()
            sb.table("journal_entries").delete().eq("id", je_id).execute()

        # Create new
        je = sb.table("journal_entries").insert({
            "entry_no": je_no, "date": date.today().isoformat(),
            "description": "Opening Inventory Entry", "reference": "Opening Balance"
        }).execute().data
        if not je:
            st.error("Failed to create journal entry"); return
        je_id = je[0]["id"]

        # DR Inventory
        inv_acc = sb.table("accounts").select("id,balance").eq("code","1200").execute().data[0]
        sb.table("journal_lines").insert({
            "entry_id": je_id, "account_id": inv_acc["id"],
            "debit": grand_total, "credit": 0, "narration": "Opening inventory value"
        }).execute()
        sb.table("accounts").update({"balance": float(inv_acc.get("balance") or 0) + grand_total}).eq("id", inv_acc["id"]).execute()

        # CR Capital per investor
        for inv_name, g in groups.items():
            # Create capital account if doesn't exist
            cap_acc = sb.table("accounts").select("id,balance").eq("code", g["cap_code"]).execute().data
            if not cap_acc:
                res = sb.table("accounts").insert({
                    "code": g["cap_code"], "name": g["cap_name"], "type": "Equity", "balance": 0
                }).execute().data
                cap_id = res[0]["id"]
                cap_bal = 0.0
            else:
                cap_id = cap_acc[0]["id"]
                cap_bal = float(cap_acc[0].get("balance") or 0)

            sb.table("journal_lines").insert({
                "entry_id": je_id, "account_id": cap_id,
                "debit": 0, "credit": g["total"], "narration": f"Opening capital - {inv_name}"
            }).execute()
            sb.table("accounts").update({"balance": cap_bal + g["total"]}).eq("id", cap_id).execute()

        st.success(f"✅ Opening Inventory Entry posted!\nDR 1200 Inventory: {fmt_currency(grand_total)}\nCR Capital accounts: {fmt_currency(grand_total)}")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")


# ─── Clear Invoices ───────────────────────────────────────────────────────────
def _clear_invoices():
    section_header("CLEAR INVOICES")
    st.error("🔴 **DANGER ZONE** — This permanently deletes invoice data.")

    col1, col2, col3 = st.columns(3)
    with col1:
        clear_sales = st.checkbox("Clear Sales Invoices")
    with col2:
        clear_purch = st.checkbox("Clear Purchase Bills")
    with col3:
        restore_stock = st.checkbox("Restore Stock to Opening Qty")

    if not clear_sales and not clear_purch:
        st.info("Select at least one option above."); return

    types_label = []
    if clear_sales: types_label.append("Sales Invoices")
    if clear_purch: types_label.append("Purchase Bills")
    if restore_stock: types_label.append("Stock → restored to opening qty")

    st.markdown(f"**Will delete:** {', '.join(types_label)}")
    st.markdown("Master data (products, customers, suppliers) will be **KEPT**.")

    confirm = st.checkbox("⚠️ I understand this cannot be undone")
    if confirm:
        if st.button("🗑️ CLEAR NOW", type="primary"):
            _do_clear_invoices(clear_sales, clear_purch, restore_stock)


def _do_clear_invoices(do_sales, do_purch, restore_stock):
    sb = get_supabase()
    try:
        inv_types = []
        if do_sales: inv_types.append("sale")
        if do_purch: inv_types.append("purchase")

        # Get invoice IDs
        for t in inv_types:
            invs = sb.table("invoices").select("id").eq("type", t).execute().data or []
            for inv in invs:
                sb.table("invoice_items").delete().eq("invoice_id", inv["id"]).execute()

        # Remove GL entries
        prefixes = []
        if do_sales:  prefixes += ["JE-SI-", "JE-COGS-", "RCPT-"]
        if do_purch:  prefixes += ["JE-PI-", "PYMT-"]
        for prefix in prefixes:
            jes = sb.table("journal_entries").select("id").ilike("entry_no", f"{prefix}%").execute().data or []
            for je in jes:
                sb.table("journal_lines").delete().eq("entry_id", je["id"]).execute()
                sb.table("journal_entries").delete().eq("id", je["id"]).execute()

        # Delete stock moves
        for t in inv_types:
            sb.table("stock_moves").delete().eq("move_type", t).execute()

        # Delete invoices
        for t in inv_types:
            sb.table("invoices").delete().eq("type", t).execute()

        # Reset balances
        if do_sales:  sb.table("customers").update({"balance": 0}).neq("id", 0).execute()
        if do_purch:  sb.table("suppliers").update({"balance": 0}).neq("id", 0).execute()

        # Restore stock
        if restore_stock:
            prods = sb.table("products").select("id,opening_qty").execute().data or []
            for p in prods:
                sb.table("products").update({"qty_on_hand": float(p.get("opening_qty") or 0)}).eq("id", p["id"]).execute()

        # Recalculate account balances
        _recalculate_all_balances(sb)

        st.success("✅ Cleared successfully! Account balances recalculated.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")


# ─── Clear Journal ────────────────────────────────────────────────────────────
def _clear_journal():
    section_header("CLEAR ALL JOURNAL ENTRIES")
    st.error("🔴 **EXTREME DANGER** — This deletes ALL journal entries and resets ALL account balances to opening balances.")

    st.markdown("""
    This will:
    - Delete all journal entries and lines
    - Reset all account balances to their opening balances
    - Reset all customer and supplier balances to 0
    - Delete all stock movements
    """)

    confirm1 = st.checkbox("I understand all journal history will be permanently deleted")
    confirm2 = st.checkbox("I have backed up my data")

    if confirm1 and confirm2:
        if st.button("🗑️ CLEAR ALL JOURNAL ENTRIES", type="primary"):
            _do_clear_journal()


def _do_clear_journal():
    sb = get_supabase()
    try:
        sb.table("journal_lines").delete().neq("id", 0).execute()
        sb.table("journal_entries").delete().neq("id", 0).execute()
        sb.table("stock_moves").delete().neq("id", 0).execute()
        sb.table("customers").update({"balance": 0}).neq("id", 0).execute()
        sb.table("suppliers").update({"balance": 0}).neq("id", 0).execute()

        # Reset accounts to opening balances
        accs = sb.table("accounts").select("id,opening_balance").execute().data or []
        for a in accs:
            sb.table("accounts").update({"balance": float(a.get("opening_balance") or 0)}).eq("id", a["id"]).execute()

        st.success("✅ All journal entries cleared. Account balances reset to opening balances.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")


def _recalculate_all_balances(sb):
    """Recalculate all account balances from remaining journal lines."""
    accs  = sb.table("accounts").select("id,type,opening_balance").execute().data or []
    lines = sb.table("journal_lines").select("account_id,debit,credit").execute().data or []
    movements = {}
    for l in lines:
        aid = l["account_id"]
        if aid not in movements: movements[aid] = [0,0]
        movements[aid][0] += float(l.get("debit") or 0)
        movements[aid][1] += float(l.get("credit") or 0)
    for a in accs:
        ob = float(a.get("opening_balance") or 0)
        dr, cr = movements.get(a["id"], [0,0])
        new_bal = (ob + dr - cr) if a["type"] in ("Asset","Expense") else (ob + cr - dr)
        sb.table("accounts").update({"balance": new_bal}).eq("id", a["id"]).execute()
