"""
app.py — Accounting Pro SaaS
Single-file entry point. All modules live in views/ (NOT pages/).
"""
import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Accounting Pro | PKR",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif !important;
}
.stApp { background: #F5F7FB !important; }

/* ── Hide ALL Streamlit default navigation (raw links at top of sidebar) ── */
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNav"],
section[data-testid="stSidebarNav"],
div[data-testid="stSidebarNavItems"],
ul[data-testid="stSidebarNavItems"],
.st-emotion-cache-1rtdyuf,
.st-emotion-cache-eczf4j,
nav[aria-label="Page navigation"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E8EBF3 !important;
    min-width: 240px !important;
    max-width: 240px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

/* ── Sidebar nav buttons ── */
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    text-align: left !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 9px 14px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #374151 !important;
    background: transparent !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
    margin-bottom: 1px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #F5F7FB !important;
    color: #1A1F36 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #EEF2FF !important;
    color: #3D5AF1 !important;
    font-weight: 700 !important;
    border-left: 3px solid #3D5AF1 !important;
}

/* ── Main content ── */
.main .block-container {
    padding: 1.5rem 2rem !important;
    max-width: 100% !important;
}

/* ── KPI Cards ── */
.kpi-card {
    background: #FFFFFF; border-radius: 12px;
    border: 1px solid #E8EBF3; padding: 0 0 18px 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05); overflow: hidden;
    transition: box-shadow 0.2s, transform 0.2s; height: 100%;
}
.kpi-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.09); transform: translateY(-2px); }
.kpi-accent-bar { height: 4px; width: 100%; margin-bottom: 16px; }
.kpi-title { font-size:10px; font-weight:700; text-transform:uppercase;
             letter-spacing:0.1em; color:#9CA3AF; padding:0 18px; margin-bottom:6px; }
.kpi-value { font-size:24px; font-weight:800; padding:0 18px; line-height:1.2; }
.kpi-subtitle { font-size:11px; color:#9CA3AF; padding:5px 18px 0 18px; }
.kpi-pill { display:inline-block; padding:3px 10px; border-radius:20px;
            font-size:10px; font-weight:700; margin:8px 18px 0 18px; }

/* ── Section header ── */
.section-header {
    font-size:10px; font-weight:700; text-transform:uppercase;
    letter-spacing:0.12em; color:#9CA3AF;
    margin:24px 0 12px 0; padding-bottom:8px;
    border-bottom:1px solid #F0F2F7;
}

/* ── Page title ── */
.page-title { font-size:24px; font-weight:800; color:#111827; margin-bottom:2px; }
.page-subtitle { font-size:13px; color:#9CA3AF; margin-bottom:4px; }
.topbar { font-size:12px; color:#9CA3AF; margin-bottom:6px; }

/* ── Badges ── */
.badge-paid    { background:#D1FAE5;color:#065F46;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600; }
.badge-unpaid  { background:#FEF3C7;color:#92400E;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600; }
.badge-partial { background:#DBEAFE;color:#1E40AF;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600; }
.badge-ok      { background:#D1FAE5;color:#065F46;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600; }
.badge-low     { background:#FEF3C7;color:#92400E;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600; }
.badge-out     { background:#FEE2E2;color:#991B1B;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600; }

/* ── Widgets ── */
.stDataFrame { border-radius:10px !important; overflow:hidden; }
.stButton > button { border-radius:8px !important; font-weight:600 !important; }
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > textarea { border-radius:8px !important; }

/* ── Hide Streamlit branding ── */
#MainMenu, footer, header, .stDeployButton { visibility:hidden !important; display:none !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

def nav_to(p: str):
    st.session_state.page = p
    st.rerun()

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:

    st.markdown(f"""
    <div style="padding:20px 16px 10px 16px;">
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="font-size:26px;">📊</div>
            <div>
                <div style="font-size:17px;font-weight:800;color:#3D5AF1;letter-spacing:-0.5px;">AccPro</div>
                <div style="font-size:10px;color:#9CA3AF;font-weight:500;">PKR Accounting Suite</div>
            </div>
        </div>
    </div>
    <div style="height:1px;background:#F0F2F7;margin:0 12px 6px 12px;"></div>
    """, unsafe_allow_html=True)

    current = st.session_state.page

    NAV = [
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

    for item in NAV:
        if len(item) == 1:
            st.markdown(
                f'<div style="font-size:9px;font-weight:800;color:#C4C9D4;'
                f'text-transform:uppercase;letter-spacing:0.14em;'
                f'padding:14px 14px 4px 14px;">{item[0]}</div>',
                unsafe_allow_html=True
            )
            continue
        label, icon, key = item
        if st.button(f"{icon}  {label}", key=f"nav_{key}",
                     width='stretch',
                     type="primary" if current == key else "secondary"):
            nav_to(key)

    st.markdown(f"""
    <div style="height:1px;background:#F0F2F7;margin:10px 12px 8px 12px;"></div>
    <div style="font-size:11px;color:#C4C9D4;padding:0 14px 16px 14px;">
        📅 {date.today().strftime('%d %b %Y')}
    </div>
    """, unsafe_allow_html=True)

# ─── Page Router ─────────────────────────────────────────────────────────────
p = st.session_state.page

if   p == "dashboard":    from views.dashboard    import render; render()
elif p == "journal":      from views.journal       import render; render()
elif p == "trial_balance":from views.trial_balance import render; render()
elif p == "accounts":     from views.accounts      import render; render()
elif p == "sales":        from views.invoices      import render; render("sale")
elif p == "purchases":    from views.invoices      import render; render("purchase")
elif p == "customers":    from views.customers     import render; render()
elif p == "suppliers":    from views.suppliers     import render; render()
elif p == "receipts":     from views.receipts      import render; render()
elif p == "payments":     from views.payments      import render; render()
elif p == "products":     from views.products      import render; render()
elif p == "stock":        from views.stock         import render; render()
elif p == "investors":    from views.investors     import render; render()
elif p == "reports":      from views.reports       import render; render()
elif p == "data_tools":   from views.data_tools    import render; render()
else:                     from views.dashboard     import render; render()
