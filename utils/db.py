"""
utils/db.py — Supabase connection and query helpers
All database operations go through this module.
"""

import streamlit as st
from supabase import create_client, Client
from datetime import date
import os

# ─── Connection ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    """Return a cached Supabase client."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
    except Exception:
        # Fallback to environment variables for local dev
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        st.error("⚠️ Supabase credentials not configured. Please set up .streamlit/secrets.toml")
        st.stop()
    return create_client(url, key)

# ─── Generic helpers ─────────────────────────────────────────────────────────
def run_query(table: str, filters: dict = None, order: str = None, limit: int = None):
    """Generic SELECT from any table."""
    sb = get_supabase()
    q = sb.table(table).select("*")
    if filters:
        for col, val in filters.items():
            q = q.eq(col, val)
    if order:
        q = q.order(order)
    if limit:
        q = q.limit(limit)
    return q.execute().data or []

def insert_row(table: str, data: dict):
    sb = get_supabase()
    return sb.table(table).insert(data).execute().data

def update_row(table: str, row_id: int, data: dict):
    sb = get_supabase()
    return sb.table(table).update(data).eq("id", row_id).execute().data

def delete_row(table: str, row_id: int):
    sb = get_supabase()
    return sb.table(table).delete().eq("id", row_id).execute().data

def upsert_row(table: str, data: dict, on_conflict: str = "id"):
    sb = get_supabase()
    return sb.table(table).upsert(data, on_conflict=on_conflict).execute().data

# ─── Accounts ────────────────────────────────────────────────────────────────
def get_accounts(acc_type: str = None):
    sb = get_supabase()
    q = sb.table("accounts").select("*").order("code")
    if acc_type:
        q = q.eq("type", acc_type)
    return q.execute().data or []

def get_account_by_code(code: str):
    sb = get_supabase()
    r = sb.table("accounts").select("*").eq("code", code).execute().data
    return r[0] if r else None

def next_gl_code(account_type: str) -> str:
    ranges = {
        "Asset": (1000, 1999), "Liability": (2000, 2999),
        "Equity": (3000, 3999), "Revenue": (4000, 4999), "Expense": (5000, 5999),
    }
    start, end = ranges.get(account_type, (9000, 9999))
    accounts = get_accounts()
    existing = set()
    for a in accounts:
        try:
            n = int(a["code"])
            if start <= n <= end:
                existing.add(n)
        except ValueError:
            pass
    nxt = start
    while nxt in existing and nxt <= end:
        nxt += 1
    return str(nxt) if nxt <= end else str(end + 1)

# ─── Trial Balance Computation ───────────────────────────────────────────────
def compute_trial_balance():
    """
    Compute all account balances from journal lines (same logic as desktop app).
    Returns: (by_code_dict, by_type_dict)
    """
    sb = get_supabase()
    accounts = sb.table("accounts").select("id,code,name,type,opening_balance").order("code").execute().data or []
    lines = sb.table("journal_lines").select("account_id,debit,credit").execute().data or []

    movements = {}
    for line in lines:
        aid = line["account_id"]
        dr = float(line.get("debit") or 0)
        cr = float(line.get("credit") or 0)
        if aid not in movements:
            movements[aid] = [0.0, 0.0]
        movements[aid][0] += dr
        movements[aid][1] += cr

    by_code = {}
    by_type = {}
    for a in accounts:
        aid = a["id"]
        ob = float(a.get("opening_balance") or 0)
        dr_mv, cr_mv = movements.get(aid, [0.0, 0.0])
        if a["type"] in ("Asset", "Expense"):
            balance = ob + dr_mv - cr_mv
        else:
            balance = ob + cr_mv - dr_mv
        by_code[a["code"]] = {
            "id": aid, "name": a["name"], "type": a["type"],
            "ob": ob, "dr": dr_mv, "cr": cr_mv, "balance": balance
        }
        by_type[a["type"]] = by_type.get(a["type"], 0.0) + balance

    return by_code, by_type

# ─── Journal Entries ─────────────────────────────────────────────────────────
def get_journal_entries(search: str = None):
    sb = get_supabase()
    q = sb.table("journal_entries").select("*").order("date", desc=True)
    data = q.execute().data or []
    if search:
        s = search.lower()
        data = [r for r in data if s in (r.get("entry_no") or "").lower()
                or s in (r.get("description") or "").lower()
                or s in (r.get("reference") or "").lower()]
    return data

def get_journal_lines(entry_id: int):
    sb = get_supabase()
    lines = sb.table("journal_lines").select("*,accounts(code,name,type)").eq("entry_id", entry_id).execute().data or []
    return lines

def next_entry_no():
    sb = get_supabase()
    entries = sb.table("journal_entries").select("entry_no").execute().data or []
    nums = []
    for e in entries:
        en = e.get("entry_no", "")
        if en.startswith("JE-"):
            try:
                nums.append(int(en.split("-")[1]))
            except Exception:
                pass
    nxt = max(nums, default=0) + 1
    return f"JE-{nxt:04d}"

def post_journal_entry(entry_no, description, ref, lines_data):
    """
    Post a balanced journal entry.
    lines_data = [{"account_id": int, "debit": float, "credit": float, "narration": str}, ...]
    """
    sb = get_supabase()
    je = sb.table("journal_entries").insert({
        "entry_no": entry_no,
        "date": date.today().isoformat(),
        "description": description,
        "reference": ref or ""
    }).execute().data
    if not je:
        return False
    je_id = je[0]["id"]
    for line in lines_data:
        sb.table("journal_lines").insert({
            "entry_id": je_id,
            "account_id": line["account_id"],
            "debit": float(line.get("debit") or 0),
            "credit": float(line.get("credit") or 0),
            "narration": line.get("narration", "")
        }).execute()
        # Update account balance
        a = sb.table("accounts").select("id,type,balance").eq("id", line["account_id"]).execute().data
        if a:
            acc = a[0]
            dr = float(line.get("debit") or 0)
            cr = float(line.get("credit") or 0)
            if acc["type"] in ("Asset", "Expense"):
                new_bal = float(acc["balance"] or 0) + dr - cr
            else:
                new_bal = float(acc["balance"] or 0) + cr - dr
            sb.table("accounts").update({"balance": new_bal}).eq("id", line["account_id"]).execute()
    return je_id

# ─── Customers ───────────────────────────────────────────────────────────────
def get_customers():
    sb = get_supabase()
    return sb.table("customers").select("*").order("name").execute().data or []

def next_customer_code():
    custs = get_customers()
    return f"C-{len(custs)+1:04d}"

def compute_customer_balance(customer_id: int, customer_name: str) -> float:
    sb = get_supabase()
    inv = sb.table("invoices").select("total").eq("party_id", customer_id).eq("type", "sale").execute().data or []
    total_invoiced = sum(float(r.get("total") or 0) for r in inv)
    # Opening balance debits to 1100
    entries = sb.table("journal_entries").select("id,entry_no").ilike("entry_no", "OB-CUST-%").execute().data or []
    ob_debit = 0.0
    for e in entries:
        if customer_name.lower() in (e.get("description") or "").lower():
            lines = sb.table("journal_lines").select("debit,accounts(code)").eq("entry_id", e["id"]).execute().data or []
            for l in lines:
                if l.get("accounts", {}).get("code") == "1100":
                    ob_debit += float(l.get("debit") or 0)
    # Receipts
    receipt_entries = sb.table("journal_entries").select("id").ilike("description", f"%Receipt - {customer_name}%").execute().data or []
    total_collected = 0.0
    for e in receipt_entries:
        lines = sb.table("journal_lines").select("credit,accounts(code)").eq("entry_id", e["id"]).execute().data or []
        for l in lines:
            if l.get("accounts", {}).get("code") == "1100":
                total_collected += float(l.get("credit") or 0)
    return total_invoiced + ob_debit - total_collected

# ─── Suppliers ───────────────────────────────────────────────────────────────
def get_suppliers():
    sb = get_supabase()
    return sb.table("suppliers").select("*").order("name").execute().data or []

def next_supplier_code():
    supps = get_suppliers()
    return f"S-{len(supps)+1:04d}"

# ─── Products ────────────────────────────────────────────────────────────────
def get_products():
    sb = get_supabase()
    return sb.table("products").select("*,investors(name)").order("name").execute().data or []

def next_product_code():
    prods = get_products()
    return f"P-{len(prods)+1:04d}"

# ─── Investors ───────────────────────────────────────────────────────────────
def get_investors():
    sb = get_supabase()
    return sb.table("investors").select("*").order("name").execute().data or []

def next_investor_code():
    investors = get_investors()
    return f"INV-{len(investors)+1:04d}"

# ─── Invoices ────────────────────────────────────────────────────────────────
def get_invoices(inv_type: str = None, status: str = None):
    sb = get_supabase()
    q = sb.table("invoices").select("*").order("date", desc=True)
    if inv_type:
        q = q.eq("type", inv_type)
    if status:
        q = q.eq("status", status)
    return q.execute().data or []

def get_invoice_with_items(invoice_id: int):
    sb = get_supabase()
    inv = sb.table("invoices").select("*").eq("id", invoice_id).execute().data
    if not inv:
        return None, []
    items = sb.table("invoice_items").select("*").eq("invoice_id", invoice_id).execute().data or []
    return inv[0], items

def next_invoice_no(inv_type: str) -> str:
    sb = get_supabase()
    prefix = "SI" if inv_type == "sale" else "PI"
    invs = sb.table("invoices").select("invoice_no").eq("type", inv_type).execute().data or []
    nums = []
    for i in invs:
        no = i.get("invoice_no", "")
        if no.startswith(f"{prefix}-"):
            try:
                nums.append(int(no.split("-")[1]))
            except Exception:
                pass
    nxt = max(nums, default=0) + 1
    return f"{prefix}-{nxt:04d}"

# ─── Dashboard KPIs ──────────────────────────────────────────────────────────
def get_dashboard_kpis():
    sb = get_supabase()
    by_code, by_type = compute_trial_balance()

    total_assets  = by_type.get("Asset", 0.0)
    total_liab    = by_type.get("Liability", 0.0)
    revenue       = by_type.get("Revenue", 0.0)
    expenses      = by_type.get("Expense", 0.0)
    net_profit    = revenue - expenses

    ar_val = by_code.get("1100", {}).get("balance", 0.0)
    ap_val = by_code.get("2000", {}).get("balance", 0.0)

    prods = sb.table("products").select("qty_on_hand,cost_price,reorder_level").execute().data or []
    inv_value  = sum(float(p.get("qty_on_hand") or 0) * float(p.get("cost_price") or 0) for p in prods)
    low_stock  = sum(1 for p in prods if 0 < float(p.get("qty_on_hand") or 0) <= float(p.get("reorder_level") or 0))
    out_stock  = sum(1 for p in prods if float(p.get("qty_on_hand") or 0) <= 0)

    total_prod  = len(prods)
    total_cust  = len(sb.table("customers").select("id").execute().data or [])
    total_supp  = len(sb.table("suppliers").select("id").execute().data or [])

    open_ar = len(sb.table("invoices").select("id").eq("type","sale").neq("status","Paid").execute().data or [])
    open_ap = len(sb.table("invoices").select("id").eq("type","purchase").neq("status","Paid").execute().data or [])

    # Monthly income (last 6 months)
    monthly_sales = sb.table("invoices").select("date,total").eq("type","sale").execute().data or []

    return {
        "total_assets": total_assets,
        "total_liab": total_liab,
        "revenue": revenue,
        "expenses": expenses,
        "net_profit": net_profit,
        "ar_val": ar_val,
        "ap_val": ap_val,
        "inv_value": inv_value,
        "low_stock": low_stock,
        "out_stock": out_stock,
        "total_prod": total_prod,
        "total_cust": total_cust,
        "total_supp": total_supp,
        "open_ar": open_ar,
        "open_ap": open_ap,
        "monthly_sales": monthly_sales,
    }

def get_recent_journal_entries(limit=6):
    sb = get_supabase()
    entries = sb.table("journal_entries").select("id,entry_no,date,description").order("created_at", desc=True).limit(limit).execute().data or []
    result = []
    for e in entries:
        lines = sb.table("journal_lines").select("debit,credit").eq("entry_id", e["id"]).execute().data or []
        total_dr = sum(float(l.get("debit") or 0) for l in lines)
        total_cr = sum(float(l.get("credit") or 0) for l in lines)
        result.append({**e, "total_dr": total_dr, "total_cr": total_cr})
    return result

def get_monthly_data():
    """Return last 6 months of income and profit for charts."""
    sb = get_supabase()
    from collections import defaultdict
    import calendar

    sales = sb.table("invoices").select("date,total").eq("type","sale").execute().data or []
    monthly_income = defaultdict(float)
    for s in sales:
        if s.get("date"):
            mo = str(s["date"])[:7]
            monthly_income[mo] += float(s.get("total") or 0)

    # Profit per month from journal lines
    lines = sb.table("journal_lines").select("entry_id,account_id,debit,credit,accounts(type)").execute().data or []
    entries = {e["id"]: e["date"][:7] for e in (sb.table("journal_entries").select("id,date").execute().data or [])}
    monthly_profit = defaultdict(float)
    for l in lines:
        mo = entries.get(l.get("entry_id"))
        if not mo:
            continue
        acc_type = (l.get("accounts") or {}).get("type")
        dr = float(l.get("debit") or 0)
        cr = float(l.get("credit") or 0)
        if acc_type == "Revenue":
            monthly_profit[mo] += (cr - dr)
        elif acc_type == "Expense":
            monthly_profit[mo] -= (dr - cr)

    # Get last 6 months
    import datetime
    today = datetime.date.today()
    months = []
    for i in range(5, -1, -1):
        d = today.replace(day=1) - datetime.timedelta(days=i*28)
        months.append(d.strftime("%Y-%m"))

    income_data  = [(mo, monthly_income.get(mo, 0)) for mo in months]
    profit_data  = [(mo, monthly_profit.get(mo, 0)) for mo in months]
    return income_data, profit_data
