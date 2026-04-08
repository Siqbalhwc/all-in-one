-- ============================================================
--  ACCOUNTING SAAS — Supabase PostgreSQL Schema
--  Run this in Supabase SQL Editor to set up your database
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Accounts (Chart of Accounts) ───────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('Asset','Liability','Equity','Revenue','Expense')),
    balance NUMERIC(15,2) DEFAULT 0,
    opening_balance NUMERIC(15,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Journal Entries ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    entry_no TEXT UNIQUE NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    reference TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Journal Lines ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS journal_lines (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER REFERENCES accounts(id),
    debit NUMERIC(15,2) DEFAULT 0,
    credit NUMERIC(15,2) DEFAULT 0,
    narration TEXT
);

-- ─── Customers ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    balance NUMERIC(15,2) DEFAULT 0
);

-- ─── Suppliers ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    balance NUMERIC(15,2) DEFAULT 0
);

-- ─── Investors ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS investors (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    investment_amount NUMERIC(15,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Products ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT DEFAULT 'PCS',
    cost_price NUMERIC(15,2) DEFAULT 0,
    sale_price NUMERIC(15,2) DEFAULT 0,
    qty_on_hand NUMERIC(15,2) DEFAULT 0,
    opening_qty NUMERIC(15,2) DEFAULT 0,
    reorder_level NUMERIC(15,2) DEFAULT 0,
    investor_id INTEGER REFERENCES investors(id),
    image_path TEXT
);

-- ─── Invoices ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_no TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('sale','purchase')),
    party_id INTEGER NOT NULL,
    date DATE NOT NULL,
    due_date DATE,
    total NUMERIC(15,2) DEFAULT 0,
    paid NUMERIC(15,2) DEFAULT 0,
    status TEXT DEFAULT 'Unpaid',
    notes TEXT,
    reference TEXT
);

-- ─── Invoice Items ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    description TEXT,
    qty NUMERIC(15,2) DEFAULT 1,
    unit_price NUMERIC(15,2) DEFAULT 0,
    total NUMERIC(15,2) DEFAULT 0
);

-- ─── Stock Moves ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_moves (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    move_type TEXT,
    qty NUMERIC(15,2),
    unit_price NUMERIC(15,2),
    ref TEXT,
    date TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Seed Default Chart of Accounts ─────────────────────────
INSERT INTO accounts (code, name, type) VALUES
    ('1000','Cash & Bank','Asset'),
    ('1100','Accounts Receivable','Asset'),
    ('1200','Inventory','Asset'),
    ('1300','Prepaid Expenses','Asset'),
    ('1500','Fixed Assets','Asset'),
    ('2000','Accounts Payable','Liability'),
    ('2100','Accrued Expenses','Liability'),
    ('2500','Long-term Loans','Liability'),
    ('3000','Owner Equity','Equity'),
    ('3100','Retained Earnings','Equity'),
    ('4000','Sales Revenue','Revenue'),
    ('4100','Other Income','Revenue'),
    ('5000','Cost of Goods Sold','Expense'),
    ('5100','Salaries Expense','Expense'),
    ('5200','Rent Expense','Expense'),
    ('5300','Utilities Expense','Expense'),
    ('5400','Office Expense','Expense'),
    ('5500','Depreciation','Expense'),
    ('5600','Advertisement Expense','Expense'),
    ('5700','Fuel Expense','Expense')
ON CONFLICT (code) DO NOTHING;

-- ─── Enable Row Level Security (optional but recommended) ───
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_moves ENABLE ROW LEVEL SECURITY;
ALTER TABLE investors ENABLE ROW LEVEL SECURITY;

-- Allow full access for service role (used by your app)
CREATE POLICY "Allow all for service role" ON accounts FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON journal_entries FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON journal_lines FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON customers FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON suppliers FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON products FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON invoices FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON invoice_items FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON stock_moves FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON investors FOR ALL USING (true);
