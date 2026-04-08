# 📊 Accounting Pro — Online SaaS

Your full-featured PKR accounting system, now online.  
Built with **Streamlit** + **Supabase** + **GitHub**.

---

## 🗂️ Project Structure

```
accounting_saas/
├── app.py                      ← Main entry point (run this)
├── requirements.txt
├── supabase_schema.sql         ← Run this in Supabase SQL Editor
├── .streamlit/
│   ├── config.toml             ← Theme & layout settings
│   └── secrets.toml            ← YOUR Supabase credentials (never commit this)
├── utils/
│   ├── db.py                   ← All Supabase queries & business logic
│   └── styles.py               ← CSS, design tokens, UI helpers
└── pages/
    ├── dashboard.py            ← KPIs, charts, alerts
    ├── journal.py              ← Journal Entries (double-entry)
    ├── trial_balance.py        ← Trial Balance report
    ├── accounts.py             ← Chart of Accounts
    ├── invoices.py             ← Sales Invoices & Purchase Bills
    ├── customers.py            ← Customer management + GL balance
    ├── suppliers.py            ← Supplier management + GL balance
    ├── receipts.py             ← Customer receipts
    ├── payments.py             ← Supplier payments
    ├── products.py             ← Products & inventory
    ├── stock.py                ← Stock movements & alerts
    ├── investors.py            ← Investor capital tracking
    ├── reports.py              ← P&L, Balance Sheet, AR/AP Aging
    └── data_tools.py           ← Opening inventory, data resets
```

---

## 🚀 STEP 1 — Set Up Supabase Database

1. Go to **https://supabase.com** and sign up (free)
2. Click **"New Project"** → give it a name like `accounting-pro`
3. Choose a region close to you (e.g. Singapore for Pakistan)
4. Set a database password — save it somewhere safe
5. Wait ~2 minutes for it to provision

### Run the database schema:
1. In your Supabase dashboard → click **SQL Editor** (left sidebar)
2. Click **"New Query"**
3. Open the file `supabase_schema.sql` from this project
4. Copy the entire contents and paste into the SQL Editor
5. Click **"Run"** (green button)
6. You should see: `Success. No rows returned`

### Get your API credentials:
1. In Supabase → **Settings** → **API** (left sidebar)
2. Copy:
   - **Project URL** (looks like: `https://abcdefgh.supabase.co`)
   - **anon public key** (long string starting with `eyJ...`)

---

## 🔑 STEP 2 — Configure Credentials

Edit the file `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://YOUR-PROJECT-ID.supabase.co"
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YOUR-KEY-HERE"
```

Replace with your actual values from Step 1.

> ⚠️ **IMPORTANT:** Never commit `secrets.toml` to GitHub. It's already in `.gitignore`.

---

## 💻 STEP 3 — Run Locally (Test First)

```bash
# Install Python 3.9+ if not already installed

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open at **http://localhost:8501**

---

## 🌐 STEP 4 — Deploy to GitHub + Streamlit Cloud (Free)

### 4a. Push to GitHub

```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit — Accounting Pro SaaS"

# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR-USERNAME/accounting-pro.git
git push -u origin main
```

> ⚠️ Make sure `secrets.toml` is in `.gitignore` so credentials are NOT pushed to GitHub.

### 4b. Deploy on Streamlit Cloud

1. Go to **https://share.streamlit.io** → Sign in with GitHub
2. Click **"New app"**
3. Select your repository and branch (`main`)
4. Set **Main file path**: `app.py`
5. Click **"Advanced settings"** → **Secrets** tab
6. Paste your secrets:
   ```toml
   [supabase]
   url = "https://YOUR-PROJECT-ID.supabase.co"
   anon_key = "eyJ..."
   ```
7. Click **"Deploy!"**

Your app will be live at:  
`https://YOUR-APP-NAME.streamlit.app` 🎉

---

## 📋 Features

| Module | Features |
|--------|----------|
| **Dashboard** | KPI cards (Assets, Liabilities, Revenue, Profit), Operations metrics, Alerts, Monthly charts |
| **Journal Entries** | Double-entry posting, balance validation, search, delete with GL reversal |
| **Trial Balance** | Live computation from journal lines, recalculate button, type summary |
| **Chart of Accounts** | Full CRUD, auto-GL code suggestion, opening balances |
| **Sales Invoices** | Multi-line invoices, GL auto-posting, payment recording, status tracking |
| **Purchase Bills** | Multi-line bills, GL auto-posting, payment recording |
| **Customers** | Full CRUD, opening balances posted to GL, balance computation |
| **Suppliers** | Full CRUD, opening balances posted to GL |
| **Receipts** | Standalone receipt entry (DR Cash / CR AR) |
| **Payments** | Standalone payment entry (DR AP / CR Cash) |
| **Products** | Full inventory management, investor assignment, stock levels |
| **Stock Movements** | Movement log, manual adjustments, stock alerts |
| **Investors** | Capital tracking, GL posting for investments |
| **Reports** | P&L Statement, Balance Sheet, AR Aging, AP Aging, Inventory Valuation |
| **Data Tools** | Opening inventory journal entry, clear invoices, clear journal |

---

## 🔄 Migrating Your Existing Data

To move data from your existing SQLite database:

### Option A — Manual entry
Re-enter key data directly in the online app (recommended for small datasets).

### Option B — Export/Import via CSV
1. Use a SQLite viewer (like **DB Browser for SQLite**) to export tables as CSV
2. Use the Supabase dashboard → **Table Editor** → **Import CSV** for each table

### Option C — Python migration script
```python
import sqlite3
from supabase import create_client

# Connect to both
sqlite_conn = sqlite3.connect("accounting.db")
sb = create_client("YOUR_URL", "YOUR_KEY")

# Example: migrate customers
cursor = sqlite_conn.cursor()
cursor.execute("SELECT code, name, phone, email, address, balance FROM customers")
for row in cursor.fetchall():
    sb.table("customers").insert({
        "code": row[0], "name": row[1], "phone": row[2],
        "email": row[3], "address": row[4], "balance": row[5]
    }).execute()

print("Done!")
```

---

## 🔧 Customization

### Change currency
Edit `utils/styles.py` → find `CURRENCY = "PKR"` → change to your currency

### Change company name
Edit `app.py` → find `AccPro` in the sidebar HTML → change to your company name

### Add logo
Place `logo.png` in the project root, then in `app.py` sidebar section add:
```python
st.image("logo.png", width=120)
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `supabase credentials not configured` | Check `.streamlit/secrets.toml` has correct values |
| `Error loading entries` | Run `supabase_schema.sql` in Supabase SQL Editor |
| App is slow | Normal on first load — Supabase free tier has cold starts |
| Data not showing | Check if `supabase_schema.sql` ran successfully |
| Can't delete protected account | Accounts 1000, 1100, 1200, 2000, 3000, 3100, 4000, 5000 are system accounts |

---

## 📞 Support

If you need help:
1. Check Streamlit docs: https://docs.streamlit.io
2. Check Supabase docs: https://supabase.com/docs
3. Ask Claude for help with specific customizations!

---

*Built with ❤️ using Streamlit + Supabase*
