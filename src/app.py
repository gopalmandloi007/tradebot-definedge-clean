import os
import streamlit as st
from tradebot.session_manager import SessionManager, SessionError

st.set_page_config(page_title="TradeBot Login", layout="wide")
st.title("🔐 Definedge Auth (TOTP + OTP)")

with st.sidebar:
    st.subheader("Secrets / Env")
    st.caption("Prefer Streamlit Secrets on Cloud (Settings → Secrets)")
    api_token = st.text_input("API Token", value=st.secrets.get("api_token", os.getenv("DEFINEDGE_API_TOKEN", "")))
    api_secret = st.text_input("API Secret", value=st.secrets.get("api_secret", os.getenv("DEFINEDGE_API_SECRET", "")), type="password")
    totp_secret = st.text_input("TOTP Secret (optional)", value=st.secrets.get("totp_secret", os.getenv("DEFINEDGE_TOTP_SECRET", "")), type="password")

sm = SessionManager(api_token=api_token, api_secret=api_secret, totp_secret=totp_secret)

col1, col2 = st.columns(2)

with col1:
    if st.button("Login with TOTP (auto)"):
        try:
            data = sm.login(prefer_totp=True)
            st.success("Logged in with TOTP ✅")
            st.json({"uid": sm.uid, "api_session_key_present": bool(sm.api_session_key), "susertoken_present": bool(sm.susertoken)})
        except SessionError as e:
            st.error(str(e))

with col2:
    st.write("Manual OTP flow")
    if st.button("Step 1: Request OTP"):
        try:
            otp_token = sm.login_step1()
            st.session_state["otp_token"] = otp_token
            st.info(f"otp_token: {otp_token}")
        except SessionError as e:
            st.error(str(e))

    otp_code = st.text_input("Enter OTP (SMS/Email)")
    if st.button("Step 2: Verify OTP"):
        try:
            otp_token = st.session_state.get("otp_token")
            if not otp_token:
                st.warning("Please run Step 1 first.")
            else:
                data = sm.login_step2_with_otp(otp_token, otp_code)
                st.success("Logged in with manual OTP ✅")
                st.json({"uid": sm.uid, "api_session_key_present": bool(sm.api_session_key), "susertoken_present": bool(sm.susertoken)})
        except SessionError as e:
            st.error(str(e))

st.divider()
st.subheader("Session status")
st.write("Logged in:", sm.is_logged_in())
if sm.is_logged_in():
    st.code(sm.get_auth_headers())
