import streamlit as st
from utils import auth
from utils.supabase_client import get_client

st.set_page_config(page_title="Fixed Asset Register", page_icon="🗂️", layout="wide")


def login_form():
    st.title("🗂️ Fixed Asset Register")
    st.caption("Sign in to continue")

    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
            if submitted:
                try:
                    auth.sign_in(email, password)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab_signup:
        with st.form("signup_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                try:
                    auth.sign_up(email, password, full_name)
                    st.success("Account created! Check your email to confirm, then log in.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")


def dashboard():
    profile = auth.current_profile()
    user = auth.current_user()

    with st.sidebar:
        st.markdown(f"**{profile.get('full_name') if profile else user.email}**")
        st.caption(f"Role: {profile.get('role', 'user') if profile else 'user'}")
        if st.button("Log Out", use_container_width=True):
            auth.sign_out()
            st.rerun()

    st.title("🗂️ Fixed Asset Register — Dashboard")

    client = get_client()

    assets_resp = client.table("assets").select("*").execute()
    assets = assets_resp.data or []

    total_assets = len(assets)
    active_assets = len([a for a in assets if a["status"] == "active"])
    disposed_assets = len([a for a in assets if a["status"] == "disposed"])
    total_cost = sum(float(a["purchase_cost"]) for a in assets)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Assets", total_assets)
    col2.metric("Active", active_assets)
    col3.metric("Disposed", disposed_assets)
    col4.metric("Total Purchase Cost", f"${total_cost:,.2f}")

    st.divider()
    st.subheader("Recent Assets")
    if assets:
        recent = sorted(assets, key=lambda a: a["created_at"], reverse=True)[:10]
        st.dataframe(
            [
                {
                    "Tag": a["asset_tag"],
                    "Name": a["name"],
                    "Status": a["status"],
                    "Purchase Date": a["purchase_date"],
                    "Cost": a["purchase_cost"],
                }
                for a in recent
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No assets yet. Head to **Asset Register** in the sidebar to add your first one.")

    st.divider()
    st.page_link("pages/1_Asset_Register.py", label="➡️ Go to Asset Register")
    st.page_link("pages/2_Depreciation.py", label="➡️ Go to Depreciation")
    st.page_link("pages/3_Reports.py", label="➡️ Go to Reports")
    if auth.is_admin():
        st.page_link("pages/4_Audit_Trail.py", label="➡️ Go to Audit Trail (admin)")


def main():
    if not st.session_state.get("session"):
        login_form()
    else:
        if "profile" not in st.session_state:
            auth._load_profile()
        dashboard()


if __name__ == "__main__":
    main()
