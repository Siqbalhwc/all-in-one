"""
pages/stock.py — Stock Movements log and manual adjustments
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.styles import fmt_currency, page_header, section_header, GREEN, RED, PURPLE, CURRENCY
from utils.db import get_supabase, get_products

def render():
    
    page_header("Stock Movements", "Track all inventory in/out movements", "Stock Movements")

    tab1, tab2, tab3 = st.tabs(["📋 Movement Log", "➕ Adjust Stock", "⚠️ Stock Alerts"])

    with tab1:
        _list_moves()
    with tab2:
        _adjust_stock()
    with tab3:
        _stock_alerts()


def _list_moves():
    sb = get_supabase()
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search moves", placeholder="Product, type, ref...", label_visibility="collapsed")
    with col2:
        move_type = st.selectbox("Type", ["All","sale","purchase","adjustment","opening"], label_visibility="collapsed")

    try:
        q = sb.table("stock_moves").select("*,products(code,name)").order("date", desc=True).limit(200)
        moves = q.execute().data or []
    except Exception as e:
        st.error(f"Error: {e}"); return

    if move_type != "All":
        moves = [m for m in moves if m.get("move_type") == move_type]
    if search:
        s = search.lower()
        moves = [m for m in moves if s in ((m.get("products") or {}).get("name","")).lower()
                 or s in (m.get("ref") or "").lower()]

    if not moves:
        st.info("No stock movements found."); return

    rows = []
    for m in moves:
        prod = m.get("products") or {}
        rows.append({
            "Date": str(m.get("date",""))[:10],
            "Product": f"{prod.get('code','')} — {prod.get('name','')}",
            "Type": m.get("move_type",""),
            "Qty": f"{float(m.get('qty') or 0):,.0f}",
            "Unit Price": fmt_currency(m.get("unit_price") or 0),
            "Value": fmt_currency(float(m.get("qty") or 0) * float(m.get("unit_price") or 0)),
            "Reference": m.get("ref") or "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _adjust_stock():
    sb = get_supabase()
    products = get_products()
    prod_options = {f"{p['code']} — {p['name']} (Qty: {float(p.get('qty_on_hand') or 0):,.0f})": p for p in products}

    with st.form("stock_adjust"):
        st.markdown("### Manual Stock Adjustment")
        st.info("Use this to correct stock quantities (e.g. after physical stock count).")

        prod_sel = st.selectbox("Product *", ["— Select —"] + list(prod_options.keys()))
        col1, col2 = st.columns(2)
        with col1:
            adj_type = st.selectbox("Adjustment Type", ["IN (Add Stock)","OUT (Remove Stock)","SET (Set Exact Qty)"])
        with col2:
            qty = st.number_input("Quantity *", min_value=0.0, step=1.0)

        col3, col4 = st.columns(2)
        with col3:
            price = st.number_input("Unit Price (PKR)", min_value=0.0, step=10.0)
        with col4:
            ref = st.text_input("Reference", placeholder="Stock count ref, reason...")

        adj_date = st.date_input("Date", value=date.today())

        submitted = st.form_submit_button("💾 Apply Adjustment", type="primary", use_container_width=True)
        if submitted:
            if prod_sel == "— Select —":
                st.error("Please select a product"); return
            if qty <= 0:
                st.error("Quantity must be greater than 0"); return
            try:
                prod = prod_options[prod_sel]
                current = float(prod.get("qty_on_hand") or 0)
                if "IN" in adj_type:
                    new_qty = current + qty
                    move_type = "adjustment_in"
                elif "OUT" in adj_type:
                    new_qty = max(0, current - qty)
                    move_type = "adjustment_out"
                else:
                    new_qty = qty
                    move_type = "adjustment_set"

                sb.table("products").update({"qty_on_hand": new_qty}).eq("id", prod["id"]).execute()
                sb.table("stock_moves").insert({
                    "product_id": prod["id"], "move_type": move_type,
                    "qty": qty, "unit_price": price,
                    "ref": ref or "Manual Adjustment", "date": str(adj_date)
                }).execute()
                st.success(f"✅ Stock adjusted. {prod['name']}: {current:,.0f} → {new_qty:,.0f}")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")


def _stock_alerts():
    try:
        products = get_products()
    except Exception as e:
        st.error(f"Error: {e}"); return

    out_of_stock = [p for p in products if float(p.get("qty_on_hand") or 0) <= 0]
    low_stock    = [p for p in products if 0 < float(p.get("qty_on_hand") or 0) <= float(p.get("reorder_level") or 0)]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("❌ Out of Stock", len(out_of_stock))
    with col2:
        st.metric("⚠️ Below Reorder Level", len(low_stock))

    if out_of_stock:
        section_header("OUT OF STOCK")
        rows = [{"Code": p["code"], "Name": p["name"], "Cost": fmt_currency(p.get("cost_price") or 0),
                 "Reorder Level": f"{float(p.get('reorder_level') or 0):,.0f}"} for p in out_of_stock]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if low_stock:
        section_header("BELOW REORDER LEVEL")
        rows = [{"Code": p["code"], "Name": p["name"],
                 "Qty": f"{float(p.get('qty_on_hand') or 0):,.0f}",
                 "Reorder": f"{float(p.get('reorder_level') or 0):,.0f}",
                 "Cost": fmt_currency(p.get("cost_price") or 0)} for p in low_stock]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if not out_of_stock and not low_stock:
        st.success("✅ All products are adequately stocked!")
