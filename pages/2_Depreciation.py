import streamlit as st
from datetime import date, datetime
from utils import auth
from utils.supabase_client import get_client
from utils.depreciation import get_schedule

st.set_page_config(page_title="Depreciation", page_icon="📉", layout="wide")
auth.require_login()

client = get_client()
st.title("📉 Depreciation")

assets = client.table("assets").select("*").neq("status", "disposed").order("asset_tag").execute().data or []

if not assets:
    st.info("No active assets to depreciate. Add one in the Asset Register.")
    st.stop()

labels = [f"{a['asset_tag']} — {a['name']}" for a in assets]
selected_idx = st.selectbox("Select an asset", range(len(labels)), format_func=lambda i: labels[i])
asset = assets[selected_idx]

purchase_date = datetime.strptime(asset["purchase_date"], "%Y-%m-%d").date()

schedule = get_schedule(
    method=asset["depreciation_method"],
    purchase_cost=float(asset["purchase_cost"]),
    salvage_value=float(asset["salvage_value"]),
    useful_life_years=float(asset["useful_life_years"]),
    purchase_date=purchase_date,
    declining_balance_rate=float(asset.get("declining_balance_rate") or 0.4),
)

col1, col2, col3 = st.columns(3)
col1.metric("Purchase Cost", f"${float(asset['purchase_cost']):,.2f}")
col2.metric("Method", asset["depreciation_method"].replace("_", " ").title())
col3.metric("Useful Life", f"{asset['useful_life_years']} yrs")

st.subheader("Projected Schedule")
st.dataframe(
    [
        {
            "Period": p.period_date.isoformat(),
            "Depreciation": p.depreciation_amount,
            "Accumulated": p.accumulated_depreciation,
            "Book Value": p.book_value,
        }
        for p in schedule
    ],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Posted Ledger Entries")

posted = (
    client.table("depreciation_entries")
    .select("*")
    .eq("asset_id", asset["id"])
    .order("period_date")
    .execute()
    .data or []
)

if posted:
    st.dataframe(
        [
            {
                "Period": e["period_date"],
                "Depreciation": e["depreciation_amount"],
                "Accumulated": e["accumulated_depreciation"],
                "Book Value": e["book_value"],
            }
            for e in posted
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("No periods posted yet.")

st.divider()
st.subheader("Post a Period")

already_posted_dates = {e["period_date"] for e in posted}
next_unposted = next((p for p in schedule if p.period_date.isoformat() not in already_posted_dates), None)

if next_unposted is None:
    st.success("All scheduled periods for this asset have been posted.")
else:
    st.write(
        f"Next period to post: **{next_unposted.period_date.isoformat()}** — "
        f"Depreciation: **${next_unposted.depreciation_amount:,.2f}**, "
        f"Book Value after: **${next_unposted.book_value:,.2f}**"
    )
    if st.button("Post This Period to Ledger", type="primary"):
        try:
            client.table("depreciation_entries").insert({
                "asset_id": asset["id"],
                "period_date": next_unposted.period_date.isoformat(),
                "depreciation_amount": next_unposted.depreciation_amount,
                "accumulated_depreciation": next_unposted.accumulated_depreciation,
                "book_value": next_unposted.book_value,
                "posted_by": auth.current_user().id,
            }).execute()
            st.success("Period posted.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not post period: {e}")
