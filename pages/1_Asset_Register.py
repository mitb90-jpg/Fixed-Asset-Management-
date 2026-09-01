import streamlit as st
from datetime import date
from utils import auth
from utils.supabase_client import get_client

st.set_page_config(page_title="Asset Register", page_icon="📋", layout="wide")
auth.require_login()

client = get_client()
st.title("📋 Asset Register")

# ---------- Load categories for dropdowns ----------
categories_resp = client.table("categories").select("*").order("name").execute()
categories = categories_resp.data or []
category_map = {c["name"]: c for c in categories}

tab_view, tab_add, tab_manage = st.tabs(["View Assets", "Add Asset", "Edit / Dispose"])

# ============================================================
# VIEW
# ============================================================
with tab_view:
    status_filter = st.selectbox("Filter by status", ["All", "active", "under_maintenance", "disposed"])
    query = client.table("assets").select("*, categories(name)")
    if status_filter != "All":
        query = query.eq("status", status_filter)
    assets = query.order("created_at", desc=True).execute().data or []

    if assets:
        st.dataframe(
            [
                {
                    "Tag": a["asset_tag"],
                    "Name": a["name"],
                    "Category": (a.get("categories") or {}).get("name", "—"),
                    "Status": a["status"],
                    "Location": a.get("location") or "—",
                    "Assigned To": a.get("assigned_to") or "—",
                    "Purchase Date": a["purchase_date"],
                    "Cost": a["purchase_cost"],
                    "Salvage": a["salvage_value"],
                    "Useful Life (yrs)": a["useful_life_years"],
                    "Method": a["depreciation_method"],
                }
                for a in assets
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{len(assets)} asset(s)")
    else:
        st.info("No assets match this filter.")

# ============================================================
# ADD
# ============================================================
with tab_add:
    if not categories:
        st.warning("No categories found. Add categories in Supabase (`categories` table) first.")
    else:
        with st.form("add_asset_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                asset_tag = st.text_input("Asset Tag *", help="Unique identifier, e.g. FA-0001")
                name = st.text_input("Asset Name *")
                category_name = st.selectbox("Category *", list(category_map.keys()))
                location = st.text_input("Location")
                assigned_to = st.text_input("Assigned To")
            with col2:
                purchase_date = st.date_input("Purchase Date *", value=date.today())
                purchase_cost = st.number_input("Purchase Cost *", min_value=0.0, step=100.0, format="%.2f")
                salvage_value = st.number_input("Salvage Value", min_value=0.0, step=50.0, format="%.2f")
                cat_default = category_map[category_name]
                useful_life_years = st.number_input(
                    "Useful Life (years) *", min_value=1.0,
                    value=float(cat_default["default_useful_life_years"]), step=1.0
                )
                depreciation_method = st.selectbox(
                    "Depreciation Method",
                    ["straight_line", "declining_balance"],
                    index=0 if cat_default["default_depreciation_method"] == "straight_line" else 1,
                )
            description = st.text_area("Description")

            declining_rate = 0.4
            if depreciation_method == "declining_balance":
                declining_rate = st.slider("Declining Balance Rate", 0.05, 0.9, 0.4, 0.05)

            submitted = st.form_submit_button("Add Asset", use_container_width=True)
            if submitted:
                if not asset_tag or not name:
                    st.error("Asset Tag and Name are required.")
                else:
                    try:
                        client.table("assets").insert({
                            "asset_tag": asset_tag,
                            "name": name,
                            "category_id": category_map[category_name]["id"],
                            "description": description,
                            "location": location,
                            "assigned_to": assigned_to,
                            "purchase_date": str(purchase_date),
                            "purchase_cost": purchase_cost,
                            "salvage_value": salvage_value,
                            "useful_life_years": useful_life_years,
                            "depreciation_method": depreciation_method,
                            "declining_balance_rate": declining_rate,
                            "created_by": auth.current_user().id,
                        }).execute()
                        st.success(f"Asset '{name}' added.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add asset: {e}")

# ============================================================
# EDIT / DISPOSE
# ============================================================
with tab_manage:
    all_assets = client.table("assets").select("*").order("asset_tag").execute().data or []
    if not all_assets:
        st.info("No assets to manage yet.")
    else:
        labels = [f"{a['asset_tag']} — {a['name']}" for a in all_assets]
        selected_idx = st.selectbox("Select an asset", range(len(labels)), format_func=lambda i: labels[i])
        selected = all_assets[selected_idx]

        can_edit = auth.is_admin() or selected.get("created_by") == auth.current_user().id
        if not can_edit:
            st.warning("Only the creator or an admin can edit this asset.")
        else:
            with st.form("edit_asset_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Asset Name", value=selected["name"])
                    location = st.text_input("Location", value=selected.get("location") or "")
                    assigned_to = st.text_input("Assigned To", value=selected.get("assigned_to") or "")
                    status = st.selectbox(
                        "Status", ["active", "under_maintenance", "disposed"],
                        index=["active", "under_maintenance", "disposed"].index(selected["status"])
                    )
                with col2:
                    salvage_value = st.number_input(
                        "Salvage Value", min_value=0.0, value=float(selected["salvage_value"]), step=50.0
                    )
                    useful_life_years = st.number_input(
                        "Useful Life (years)", min_value=1.0, value=float(selected["useful_life_years"]), step=1.0
                    )
                    disposed_date = None
                    disposed_proceeds = None
                    if status == "disposed":
                        disposed_date = st.date_input("Disposal Date", value=date.today())
                        disposed_proceeds = st.number_input("Disposal Proceeds", min_value=0.0, step=50.0)
                description = st.text_area("Description", value=selected.get("description") or "")

                col_save, col_delete = st.columns(2)
                save = col_save.form_submit_button("Save Changes", use_container_width=True)
                delete = col_delete.form_submit_button(
                    "Delete Asset", use_container_width=True, type="secondary",
                    disabled=not auth.is_admin()
                )

                if save:
                    try:
                        update_payload = {
                            "name": name,
                            "location": location,
                            "assigned_to": assigned_to,
                            "status": status,
                            "salvage_value": salvage_value,
                            "useful_life_years": useful_life_years,
                            "description": description,
                        }
                        if status == "disposed":
                            update_payload["disposed_date"] = str(disposed_date)
                            update_payload["disposed_proceeds"] = disposed_proceeds
                        client.table("assets").update(update_payload).eq("id", selected["id"]).execute()
                        st.success("Asset updated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

                if delete:
                    try:
                        client.table("assets").delete().eq("id", selected["id"]).execute()
                        st.success("Asset deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
            if not auth.is_admin():
                st.caption("Only admins can delete assets.")
