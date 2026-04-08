"""
pages/products.py — Products & Inventory management
"""
import streamlit as st
import pandas as pd
from utils.styles import fmt_currency, page_header, section_header, stock_badge, ACCENT, GREEN, RED, YELLOW, PURPLE, CURRENCY
from utils.db import get_supabase, get_products, get_investors, next_product_code

def render():
    
    page_header("Products & Inventory", "Manage products and stock levels", "Products")

    tab1, tab2 = st.tabs(["📦 Product List", "➕ Add Product"])

    with tab1:
        _list_products()
    with tab2:
        _product_form()


def _list_products():
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search = st.text_input("🔍 Search products", placeholder="Name, code, category...", label_visibility="collapsed")
    with col2:
        stock_filter = st.selectbox("Stock Status", ["All","OK","Low","Out"], label_visibility="collapsed")
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    try:
        products = get_products()
    except Exception as e:
        st.error(f"Error: {e}"); return

    if search:
        s = search.lower()
        products = [p for p in products if s in p["name"].lower() or s in (p.get("code") or "").lower()
                    or s in (p.get("category") or "").lower()]

    if stock_filter == "OK":
        products = [p for p in products if float(p.get("qty_on_hand") or 0) > float(p.get("reorder_level") or 0)]
    elif stock_filter == "Low":
        products = [p for p in products if 0 < float(p.get("qty_on_hand") or 0) <= float(p.get("reorder_level") or 0)]
    elif stock_filter == "Out":
        products = [p for p in products if float(p.get("qty_on_hand") or 0) <= 0]

    # KPI summary
    total_val  = sum(float(p.get("qty_on_hand") or 0) * float(p.get("cost_price") or 0) for p in products)
    low_cnt    = sum(1 for p in products if 0 < float(p.get("qty_on_hand") or 0) <= float(p.get("reorder_level") or 0))
    out_cnt    = sum(1 for p in products if float(p.get("qty_on_hand") or 0) <= 0)
    total_qty  = sum(float(p.get("qty_on_hand") or 0) for p in products)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("Products", len(products))
    with c2: st.metric("Total Value", fmt_currency(total_val, compact=True))
    with c3: st.metric("Total Units", f"{total_qty:,.0f}")
    with c4: st.metric("⚠ Low Stock", low_cnt)
    with c5: st.metric("✕ Out of Stock", out_cnt)

    if not products:
        st.info("No products found."); return

    rows = []
    for p in products:
        qty = float(p.get("qty_on_hand") or 0)
        reorder = float(p.get("reorder_level") or 0)
        val = qty * float(p.get("cost_price") or 0)
        status = "✕ Out" if qty <= 0 else ("⚠ Low" if qty <= reorder else "✓ OK")
        investor = (p.get("investors") or {}).get("name") or "—"
        rows.append({
            "Code": p["code"],
            "Name": p["name"],
            "Category": p.get("category") or "—",
            "Unit": p.get("unit") or "PCS",
            "Qty": f"{qty:,.0f}",
            "Reorder": f"{reorder:,.0f}",
            "Cost": fmt_currency(p.get("cost_price") or 0),
            "Price": fmt_currency(p.get("sale_price") or 0),
            "Value": fmt_currency(val),
            "Status": status,
            "Investor": investor,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    section_header("EDIT / DELETE PRODUCT")
    prod_options = {f"{p['code']} — {p['name']}": p for p in products}
    selected = st.selectbox("Select product", list(prod_options.keys()))
    if selected:
        prod = prod_options[selected]
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Edit Product", use_container_width=True):
                st.session_state["edit_product"] = prod
                st.rerun()
        with c2:
            if st.button("🗑️ Delete Product", use_container_width=True, type="secondary"):
                _delete_product(prod)

    if "edit_product" in st.session_state:
        _product_form(mode="edit", data=st.session_state["edit_product"])


def _product_form(mode="new", data=None):
    sb = get_supabase()
    investors = get_investors()
    inv_options = {"— None —": None}
    inv_options.update({f"{i['code']} — {i['name']}": i["id"] for i in investors})

    with st.form(f"product_form_{mode}"):
        st.markdown(f"### {'Edit' if mode=='edit' else 'New'} Product")

        col1, col2, col3 = st.columns(3)
        with col1:
            code = st.text_input("Code *", value=data["code"] if data else next_product_code())
            category = st.text_input("Category", value=data.get("category") or "" if data else "")
        with col2:
            name = st.text_input("Name *", value=data["name"] if data else "")
            unit = st.selectbox("Unit", ["PCS","KG","LTR","MTR","BOX","SET","PAIR","DOZ"],
                                index=["PCS","KG","LTR","MTR","BOX","SET","PAIR","DOZ"].index(data.get("unit","PCS")) if data else 0)
        with col3:
            cost_price = st.number_input("Cost Price (PKR)", min_value=0.0, step=10.0,
                                         value=float(data.get("cost_price") or 0) if data else 0.0)
            sale_price = st.number_input("Sale Price (PKR)", min_value=0.0, step=10.0,
                                         value=float(data.get("sale_price") or 0) if data else 0.0)

        col4, col5, col6 = st.columns(3)
        with col4:
            qty = st.number_input("Qty on Hand", min_value=0.0, step=1.0,
                                  value=float(data.get("qty_on_hand") or 0) if data else 0.0)
        with col5:
            opening_qty = st.number_input("Opening Qty", min_value=0.0, step=1.0,
                                          value=float(data.get("opening_qty") or 0) if data else 0.0)
        with col6:
            reorder = st.number_input("Reorder Level", min_value=0.0, step=1.0,
                                      value=float(data.get("reorder_level") or 0) if data else 0.0)

        # Investor assignment
        current_inv = "— None —"
        if data and data.get("investor_id"):
            for k, v in inv_options.items():
                if v == data.get("investor_id"):
                    current_inv = k; break
        inv_idx = list(inv_options.keys()).index(current_inv) if current_inv in inv_options else 0
        investor_sel = st.selectbox("Assign Investor", list(inv_options.keys()), index=inv_idx)

        submitted = st.form_submit_button("💾 Save Product", type="primary")
        if submitted:
            if not code.strip() or not name.strip():
                st.error("Code and name are required"); return
            try:
                row_data = {
                    "code": code.strip(), "name": name.strip(),
                    "category": category, "unit": unit,
                    "cost_price": cost_price, "sale_price": sale_price,
                    "qty_on_hand": qty, "opening_qty": opening_qty,
                    "reorder_level": reorder,
                    "investor_id": inv_options.get(investor_sel)
                }
                if mode == "new":
                    sb.table("products").insert(row_data).execute()
                    st.success(f"✅ Product '{name}' added!")
                else:
                    sb.table("products").update(row_data).eq("id", data["id"]).execute()
                    if "edit_product" in st.session_state:
                        del st.session_state["edit_product"]
                    st.success(f"✅ Product '{name}' updated!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")

    if mode == "edit" and st.button("✕ Cancel Edit"):
        if "edit_product" in st.session_state:
            del st.session_state["edit_product"]
        st.rerun()


def _delete_product(prod):
    sb = get_supabase()
    try:
        sb.table("stock_moves").delete().eq("product_id", prod["id"]).execute()
        sb.table("products").delete().eq("id", prod["id"]).execute()
        st.success(f"✅ Product '{prod['name']}' deleted.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")
