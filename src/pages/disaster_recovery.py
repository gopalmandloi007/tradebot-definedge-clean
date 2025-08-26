# pages/disaster_recovery.py

import streamlit as st
from tradebot.api_client import APIClient
from tradebot.disaster_recovery import DisasterRecoveryManager

st.set_page_config(page_title="🚨 Disaster Recovery", layout="wide")

st.title("🚨 Disaster Recovery Controls")

# --- API Client Setup ---
api_token = st.session_state.get("api_token")
api_secret = st.session_state.get("api_secret")

if not api_token or not api_secret:
    st.error("⚠️ Please login from main app.py first.")
    st.stop()

client = APIClient(api_token=api_token, api_secret=api_secret)
drm = DisasterRecoveryManager(client)

# --- Actions ---
tab1, tab2 = st.tabs(["❌ Cancel Orders", "🔄 Modify Orders"])

with tab1:
    st.subheader("Cancel Orders")
    cancel_type = st.radio("Choose Cancel Action", ["Cancel All Orders", "Cancel Selected Orders"])

    if cancel_type == "Cancel All Orders":
        if st.button("🚨 Cancel ALL Orders", type="primary"):
            res = drm.cancel_all_orders()
            st.success("All orders cancelled ✅")
            st.json(res)

    elif cancel_type == "Cancel Selected Orders":
        order_ids = st.text_area("Enter Order IDs (comma separated)")
        if st.button("🚨 Cancel Selected Orders"):
            if not order_ids.strip():
                st.warning("Please enter order IDs")
            else:
                ids = [oid.strip() for oid in order_ids.split(",")]
                res = drm.cancel_selected_orders(ids)
                st.success("Selected orders cancelled ✅")
                st.json(res)

with tab2:
    st.subheader("Modify Orders")
    modify_type = st.radio("Choose Modify Action", ["Modify All Orders → Market", "Modify Selected Orders → Market"])

    if modify_type == "Modify All Orders → Market":
        if st.button("🔄 Modify ALL Orders to Market", type="primary"):
            res = drm.modify_all_orders_to_market()
            st.success("All orders modified to MARKET ✅")
            st.json(res)

    elif modify_type == "Modify Selected Orders → Market":
        order_ids = st.text_area("Enter Order IDs (comma separated)")
        if st.button("🔄 Modify Selected Orders to Market"):
            if not order_ids.strip():
                st.warning("Please enter order IDs")
            else:
                ids = [oid.strip() for oid in order_ids.split(",")]
                res = drm.modify_selected_orders_to_market(ids)
                st.success("Selected orders modified to MARKET ✅")
                st.json(res)
