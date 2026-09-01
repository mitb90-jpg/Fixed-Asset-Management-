import streamlit as st
import pandas as pd
from utils import auth
from utils.supabase_client import get_client

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
auth.require_login()

client = get_client()
st.title("📊 Reports")

assets = client.table("assets").select("*, categories(name)").execute().data or []
depr_entries = client.table("depreciation_entries").select("*").execute().data or []

if not assets:
    st.info("No data yet to report on.")
    st.stop()

df_assets = pd.DataFrame(assets)
df_assets["category_name"] = df_assets["categories"].apply(lambda c: (c or {}).get("name", "—"))
df_assets = df_assets.drop(columns=["categories"])

df_depr = pd.DataFrame(depr_entries)

tab_summary, tab_register, tab_depr, tab_disposal = st.tabs(
    ["Summary", "Full Register Export", "Depreciation Export", "Disposal Report"]
)

# ============================================================
# SUMMARY
# ============================================================
with tab_summary:
    st.subheader("By Category")
    by_cat = df_assets.groupby("category_name").agg(
        count=("id", "count"),
        total_cost=("purchase_cost", "sum"),
    ).reset_index().rename(columns={"category_name": "Category", "count": "Count", "total_cost": "Total Cost"})
    st.dataframe(by_cat, use_container_width=True, hide_index=True)

    st.subheader("By Status")
    by_status = df_assets.groupby("status").agg(
        count=("id", "count"),
        total_cost=("purchase_cost", "sum"),
    ).reset_index().rename(columns={"status": "Status", "count": "Count", "total_cost": "Total Cost"})
    st.dataframe(by_status, use_container_width=True, hide_index=True)

    total_accumulated = df_depr["depreciation_amount"].sum() if not df_depr.empty else 0
    total_cost = df_assets["purchase_cost"].astype(float).sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Purchase Cost", f"${total_cost:,.2f}")
    col2.metric("Total Depreciation Posted", f"${float(total_accumulated):,.2f}")
    col3.metric("Net Book Value (est.)", f"${total_cost - float(total_accumulated):,.2f}")

# ============================================================
# FULL REGISTER EXPORT
# ============================================================
with tab_register:
    st.dataframe(df_assets, use_container_width=True, hide_index=True)
    csv = df_assets.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Full Register (CSV)", csv, "asset_register.csv", "text/csv", use_container_width=True
    )

# ============================================================
# DEPRECIATION EXPORT
# ============================================================
with tab_depr:
    if df_depr.empty:
        st.info("No depreciation entries posted yet.")
    else:
        # join asset tag/name for readability
        tag_map = {a["id"]: (a["asset_tag"], a["name"]) for a in assets}
        df_depr["asset_tag"] = df_depr["asset_id"].map(lambda i: tag_map.get(i, ("—", "—"))[0])
        df_depr["asset_name"] = df_depr["asset_id"].map(lambda i: tag_map.get(i, ("—", "—"))[1])
        display_cols = ["asset_tag", "asset_name", "period_date", "depreciation_amount",
                         "accumulated_depreciation", "book_value"]
        st.dataframe(df_depr[display_cols], use_container_width=True, hide_index=True)
        csv = df_depr[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Depreciation Ledger (CSV)", csv, "depreciation_ledger.csv", "text/csv",
            use_container_width=True
        )

# ============================================================
# DISPOSAL REPORT
# ============================================================
with tab_disposal:
    disposed = df_assets[df_assets["status"] == "disposed"].copy()
    if disposed.empty:
        st.info("No disposed assets.")
    else:
        disposed["gain_loss"] = disposed["disposed_proceeds"].astype(float) - (
            disposed["purchase_cost"].astype(float) - disposed["salvage_value"].astype(float)
        )
        cols = ["asset_tag", "name", "purchase_date", "purchase_cost",
                "disposed_date", "disposed_proceeds", "gain_loss"]
        st.dataframe(disposed[cols], use_container_width=True, hide_index=True)
        csv = disposed[cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Disposal Report (CSV)", csv, "disposal_report.csv", "text/csv",
            use_container_width=True
        )
