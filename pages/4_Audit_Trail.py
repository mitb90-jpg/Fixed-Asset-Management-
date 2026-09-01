import streamlit as st
import pandas as pd
from utils import auth
from utils.supabase_client import get_client

st.set_page_config(page_title="Audit Trail", page_icon="🕵️", layout="wide")
auth.require_login()

if not auth.is_admin():
    st.error("Only admins can view the audit trail.")
    st.stop()

client = get_client()
st.title("🕵️ Audit Trail")

col1, col2, col3 = st.columns(3)
table_filter = col1.selectbox("Table", ["All", "assets", "depreciation_entries"])
action_filter = col2.selectbox("Action", ["All", "INSERT", "UPDATE", "DELETE"])
limit = col3.number_input("Rows to show", min_value=10, max_value=1000, value=100, step=10)

query = client.table("audit_log").select("*")
if table_filter != "All":
    query = query.eq("table_name", table_filter)
if action_filter != "All":
    query = query.eq("action", action_filter)

logs = query.order("changed_at", desc=True).limit(int(limit)).execute().data or []

if not logs:
    st.info("No audit entries match these filters.")
else:
    df = pd.DataFrame(logs)
    display_df = df[["changed_at", "table_name", "action", "record_id", "changed_by"]].copy()
    display_df.columns = ["Changed At", "Table", "Action", "Record ID", "Changed By (user id)"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Inspect an Entry")
    idx = st.selectbox(
        "Select a log row to view before/after data",
        range(len(logs)),
        format_func=lambda i: f"{logs[i]['changed_at']} — {logs[i]['table_name']} — {logs[i]['action']}",
    )
    entry = logs[idx]
    col_old, col_new = st.columns(2)
    with col_old:
        st.caption("Old Data")
        st.json(entry.get("old_data") or {})
    with col_new:
        st.caption("New Data")
        st.json(entry.get("new_data") or {})
