"""
pages/journal.py — Journal Entries: list, create, edit, delete
Full double-entry bookkeeping with balanced validation.
"""
import streamlit as st
import pandas as pd
from datetime import date

from utils.styles import fmt_currency, page_header, section_header, ACCENT, GREEN, RED, YELLOW, CURRENCY
from utils.db import (
    get_supabase, get_journal_entries, get_journal_lines, get_accounts,
    next_entry_no, post_journal_entry, compute_trial_balance
)


def render():
    
    page_header("Journal Entries", "All double-entry postings", "Journal Entries")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["📋 All Entries", "➕ New Entry"])

    with tab1:
        _list_entries()

    with tab2:
        _new_entry_form()


def _list_entries():
    col_search, col_count = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Search entries", placeholder="Entry no, description, reference...", label_visibility="collapsed")

    try:
        entries = get_journal_entries(search=search)
    except Exception as e:
        st.error(f"Error loading entries: {e}")
        return

    with col_count:
        st.markdown(f'<div style="text-align:right;color:#8A94A6;font-size:13px;padding-top:10px;">{len(entries)} entries</div>', unsafe_allow_html=True)

    if not entries:
        st.info("No journal entries found. Use the 'New Entry' tab to add your first entry.")
        return

    # Build display table with totals
    sb = get_supabase()
    rows = []
    for e in entries:
        lines = sb.table("journal_lines").select("debit,credit").eq("entry_id", e["id"]).execute().data or []
        total_dr = sum(float(l.get("debit") or 0) for l in lines)
        total_cr = sum(float(l.get("credit") or 0) for l in lines)
        rows.append({
            "Entry No": e.get("entry_no", ""),
            "Date": str(e.get("date", "")),
            "Description": (e.get("description") or "")[:50],
            "Reference": e.get("reference") or "",
            "Debit": fmt_currency(total_dr) if total_dr else "—",
            "Credit": fmt_currency(total_cr) if total_cr else "—",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Entry No": st.column_config.TextColumn(width=100),
                     "Date": st.column_config.TextColumn(width=90),
                     "Description": st.column_config.TextColumn(width=260),
                 })

    # ── Select entry to view/delete ───────────────────────────────────────────
    st.markdown("---")
    section_header("VIEW / DELETE ENTRY")
    entry_nos = [e.get("entry_no") for e in entries]
    selected_no = st.selectbox("Select entry to view", entry_nos, index=0 if entry_nos else None)

    if selected_no:
        entry = next((e for e in entries if e.get("entry_no") == selected_no), None)
        if entry:
            _show_entry_detail(entry)


def _show_entry_detail(entry):
    sb = get_supabase()
    lines = sb.table("journal_lines").select("*,accounts(code,name,type)").eq("entry_id", entry["id"]).execute().data or []

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Entry No:** `{entry.get('entry_no')}`")
    with col2:
        st.markdown(f"**Date:** {entry.get('date')}")
    with col3:
        st.markdown(f"**Reference:** {entry.get('reference') or '—'}")

    st.markdown(f"**Description:** {entry.get('description') or '—'}")

    rows = []
    total_dr = total_cr = 0
    for l in lines:
        acc = l.get("accounts") or {}
        dr = float(l.get("debit") or 0)
        cr = float(l.get("credit") or 0)
        total_dr += dr; total_cr += cr
        rows.append({
            "Account Code": acc.get("code", ""),
            "Account Name": acc.get("name", ""),
            "Type": acc.get("type", ""),
            "Debit": fmt_currency(dr) if dr else "—",
            "Credit": fmt_currency(cr) if cr else "—",
            "Narration": l.get("narration") or "",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    diff = abs(total_dr - total_cr)
    if diff < 0.01:
        st.success(f"✅ Balanced — DR: {fmt_currency(total_dr)} = CR: {fmt_currency(total_cr)}")
    else:
        st.error(f"⚠️ Out of balance by {fmt_currency(diff)}")

    # Delete button
    with st.expander("⚠️ Delete this entry"):
        st.warning("Deleting a journal entry will reverse account balances. This cannot be undone.")
        if st.button("🗑️ Confirm Delete Entry", type="primary", key=f"del_{entry['id']}"):
            _delete_entry(entry)


def _delete_entry(entry):
    sb = get_supabase()
    try:
        # Reverse account balances
        lines = sb.table("journal_lines").select("*,accounts(id,type,balance)").eq("entry_id", entry["id"]).execute().data or []
        for l in lines:
            acc = l.get("accounts") or {}
            if not acc.get("id"):
                continue
            dr = float(l.get("debit") or 0)
            cr = float(l.get("credit") or 0)
            curr_bal = float(acc.get("balance") or 0)
            if acc.get("type") in ("Asset", "Expense"):
                new_bal = curr_bal - dr + cr
            else:
                new_bal = curr_bal - cr + dr
            sb.table("accounts").update({"balance": new_bal}).eq("id", acc["id"]).execute()
        # Delete lines and entry
        sb.table("journal_lines").delete().eq("entry_id", entry["id"]).execute()
        sb.table("journal_entries").delete().eq("id", entry["id"]).execute()
        st.success(f"✅ Entry {entry.get('entry_no')} deleted.")
        st.rerun()
    except Exception as ex:
        st.error(f"Error: {ex}")


def _new_entry_form():
    accounts = get_accounts()
    acc_options = {f"{a['code']} — {a['name']} ({a['type']})": a["id"] for a in accounts}
    acc_list = list(acc_options.keys())

    with st.form("new_journal_entry"):
        col1, col2, col3 = st.columns(3)
        with col1:
            entry_no = st.text_input("Entry No *", value=next_entry_no())
        with col2:
            entry_date = st.date_input("Date *", value=date.today())
        with col3:
            reference = st.text_input("Reference", placeholder="Invoice no, cheque no...")

        description = st.text_input("Description *", placeholder="e.g. Sales to Customer ABC")

        section_header("JOURNAL LINES (minimum 2 lines — must balance)")

        # Up to 10 lines
        lines_data = []
        total_dr = total_cr = 0.0
        for i in range(1, 9):
            c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 2])
            with c1:
                acc = st.selectbox(f"Account {i}", ["— Select —"] + acc_list, key=f"je_acc_{i}")
            with c2:
                dr = st.number_input(f"Debit {i}", min_value=0.0, step=100.0, key=f"je_dr_{i}", label_visibility="collapsed" if i > 1 else "visible")
            with c3:
                cr = st.number_input(f"Credit {i}", min_value=0.0, step=100.0, key=f"je_cr_{i}", label_visibility="collapsed" if i > 1 else "visible")
            with c4:
                narr = st.text_input(f"Narration {i}", key=f"je_narr_{i}", placeholder="narration...", label_visibility="collapsed")

            if acc != "— Select —" and (dr > 0 or cr > 0):
                lines_data.append({"account_id": acc_options[acc], "debit": dr, "credit": cr, "narration": narr})
                total_dr += dr; total_cr += cr

        # Balance indicator
        diff = abs(total_dr - total_cr)
        if total_dr > 0 or total_cr > 0:
            if diff < 0.01:
                st.success(f"✅ Entry balanced — DR: {fmt_currency(total_dr)} = CR: {fmt_currency(total_cr)}")
            else:
                st.warning(f"⚠️ Out of balance — DR: {fmt_currency(total_dr)} | CR: {fmt_currency(total_cr)} | Diff: {fmt_currency(diff)}")

        submitted = st.form_submit_button("💾 Post Journal Entry", type="primary", use_container_width=True)

        if submitted:
            if not entry_no.strip():
                st.error("Entry number is required")
            elif not description.strip():
                st.error("Description is required")
            elif len(lines_data) < 2:
                st.error("Minimum 2 lines required")
            elif diff > 0.01:
                st.error(f"Entry must balance. Current difference: {fmt_currency(diff)}")
            else:
                try:
                    je_id = post_journal_entry(entry_no.strip(), description.strip(), reference, lines_data)
                    st.success(f"✅ Journal Entry {entry_no} posted successfully!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error posting entry: {ex}")
