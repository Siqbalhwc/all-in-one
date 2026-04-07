"""
app.py — Main entry point for the Accounting SaaS
Streamlit multi-page app with sidebar navigation.
"""
import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Accounting Pro | PKR",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

from utils.styles import inject_global_css, fmt_currency, ACCENT, GREEN, RED, YELLOW, PURPLE, CYAN, AMBER

inject_global_css()

# ─── Navigation state ────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

def nav_to(page: str):
    st.session_state.page = page
    st.rerun()

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 16px 0 8px 0; text-align:center;">
        <div style="font-size:26px; font-weight:800; color:#3D5AF1; letter-spacing:-1px;">
            📊 AccPro
        </div>
        <div style="font-size:11px; color:#8A94A6; margin-top:2px;">PKR Accounting Suite</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Nav items: each is either ("SECTION HEADER",) or ("Label", "icon", "key")
    NAV_ITEMS = [
        ("OVERVIEW",),
        ("Dashboard",         "🏠", "dashboard"),
        ("FINANCE",),
        ("Journal Entries",   "📓", "journal"),
        ("Trial Balance",     "⚖️",  "trial_balance"),
        ("Chart of Accounts", "📋", "accounts"),
        ("SALES",),
        ("Sales Invoices",    "🧾", "sales"),
        ("Customers",         "👥", "customers"),
        ("Receipts",          "💰", "receipts"),
        ("PURCHASES",),
        ("Purchase Bills",    "🛒", "purchases"),
        ("Suppliers",         "🏭", "suppliers"),
        ("Payments",          "💳", "payments"),
        ("INVENTORY",),
        ("Products",          "📦", "products"),
        ("Stock Movements",   "🔄", "stock"),
        ("STAKEHOLDERS",),
        ("Investors",         "💼", "investors"),
        ("REPORTS",),
        ("Reports",           "📈", "reports"),
        ("SETTINGS",),
        ("Data Tools",        "🔧", "data_tools"),
    ]

    current = st.session_state.page

    for item in NAV_ITEMS:
        # Section header — only 1 element
        if len(item) == 1:
            st.markdown(f'<div style="font-size:10px;font-weight:700;color:#8A94A6;'
                        f'text-transform:uppercase;letter-spacing:0.08em;'
                        f'padding:14px 8px 4px 8px;">{item[0]}</div>',
                        unsafe_allow_html=True)
            continue

        # Nav button — 3 elements
        label, icon, key = item
        is_active = current == key
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {label}", key=f"nav_{key}",
                     use_container_width=True, type=btn_type):
            nav_to(key)

    st.divider()
    st.markdown(f"""
    <div style="font-size:11px; color:#8A94A6; padding:0 8px;">
        📅 {date.today().strftime('%d %b %Y')}
    </div>
    """, unsafe_allow_html=True)

# ─── Page Router ─────────────────────────────────────────────────────────────
page = st.session_state.page

if page == "dashboard":
    from pages.dashboard import render
    render()

elif page == "journal":
    from pages.journal import render
    render()

elif page == "trial_balance":
    from pages.trial_balance import render
    render()

elif page == "accounts":
    from pages.accounts import render
    render()

elif page == "sales":
    from pages.invoices import render
    render("sale")

elif page == "purchases":
    from pages.invoices import render
    render("purchase")

elif page == "customers":
    from pages.customers import render
    render()

elif page == "suppliers":
    from pages.suppliers import render
    render()

elif page == "receipts":
    from pages.receipts import render
    render()

elif page == "payments":
    from pages.payments import render
    render()

elif page == "products":
    from pages.products import render
    render()

elif page == "stock":
    from pages.stock import render
    render()

elif page == "investors":
    from pages.investors import render
    render()

elif page == "reports":
    from pages.reports import render
    render()

elif page == "data_tools":
    from pages.data_tools import render
    render()

else:
    from pages.dashboard import render
    render()
