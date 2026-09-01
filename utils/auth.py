"""Authentication helpers built on Supabase Auth."""
import streamlit as st
from utils.supabase_client import get_client


def sign_up(email: str, password: str, full_name: str):
    client = get_client()
    return client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": full_name}},
    })


def sign_in(email: str, password: str):
    client = get_client()
    result = client.auth.sign_in_with_password({"email": email, "password": password})
    st.session_state["session"] = result.session
    st.session_state["user"] = result.user
    _load_profile()
    return result


def sign_out():
    client = get_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    for key in ("session", "user", "profile", "supabase_client"):
        st.session_state.pop(key, None)


def _load_profile():
    """Fetch role/full_name from public.profiles for the logged-in user."""
    client = get_client()
    user = st.session_state.get("user")
    if not user:
        return
    resp = client.table("profiles").select("*").eq("id", user.id).single().execute()
    st.session_state["profile"] = resp.data


def current_user():
    return st.session_state.get("user")


def current_profile() -> dict | None:
    return st.session_state.get("profile")


def is_admin() -> bool:
    profile = current_profile()
    return bool(profile and profile.get("role") == "admin")


def require_login():
    """Call at the top of every page. Stops rendering if not logged in."""
    if not st.session_state.get("session"):
        st.warning("Please log in from the Home page to continue.")
        st.stop()
    # Keep profile in sync (e.g. if role changed) without extra calls every rerun
    if "profile" not in st.session_state:
        _load_profile()
