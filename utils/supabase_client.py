"""Supabase client factory, shared across all pages.

IMPORTANT: We deliberately do NOT use st.cache_resource here. cache_resource
is shared across ALL users of the running app process, and this app carries
a per-user auth token on the client -- caching it globally would leak one
user's session/token into another user's requests. Instead we build a
lightweight client per Streamlit session and stash it in st.session_state.
"""
import streamlit as st
from supabase import create_client, Client


def _new_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


def get_client() -> Client:
    """
    Returns a Supabase client scoped to this browser session. If the user is
    logged in, attaches their access token so PostgREST requests carry the
    user's JWT (required for Row Level Security to identify auth.uid()).
    """
    if "supabase_client" not in st.session_state:
        st.session_state["supabase_client"] = _new_client()

    client: Client = st.session_state["supabase_client"]

    session = st.session_state.get("session")
    if session:
        client.postgrest.auth(session.access_token)

    return client
