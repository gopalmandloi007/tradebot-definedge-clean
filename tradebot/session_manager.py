"""
Auth / Session Manager for Definedge (OTP + TOTP)
- Step 1: GET login -> otp_token (header: api_secret)
- Step 2: POST token -> api_session_key + susertoken
- Persists session to data/.session.json
- DRY access: get_auth_headers()
"""

from __future__ import annotations
import json
import os
import time
from typing import Optional, Dict, Any

import requests
import pyotp

LOGIN_STEP1_URL = "https://signin.definedgesecurities.com/auth/realms/debroking/dsbpkc/login/{api_token}"
LOGIN_STEP2_URL = "https://signin.definedgesecurities.com/auth/realms/debroking/dsbpkc/token"

SESSION_PATH = os.path.join("data", ".session.json")
TIMEOUT = 20


class SessionError(Exception):
    pass


class SessionManager:
    def __init__(
        self,
        api_token: Optional[str] = None,
        api_secret: Optional[str] = None,
        totp_secret: Optional[str] = None,
        persist_path: str = SESSION_PATH,
    ):
        """
        api_token, api_secret, totp_secret can be provided directly OR via env/Streamlit secrets.
        """
        self.api_token = api_token or os.getenv("DEFINEDGE_API_TOKEN")
        self.api_secret = api_secret or os.getenv("DEFINEDGE_API_SECRET")
        self.totp_secret = totp_secret or os.getenv("DEFINEDGE_TOTP_SECRET")

        self.persist_path = persist_path

        self.api_session_key: Optional[str] = None
        self.susertoken: Optional[str] = None
        self.uid: Optional[str] = None
        self.last_login_ts: Optional[int] = None

        # Load previously saved session if available
        self._ensure_dirs()
        self._load_session()

    # ---------- Public API ----------

    def login_step1(self) -> str:
        """
        Initiates login, returns otp_token.
        Requires: self.api_token, self.api_secret
        """
        self._require(self.api_token, "api_token not provided")
        self._require(self.api_secret, "api_secret not provided")

        url = LOGIN_STEP1_URL.format(api_token=self.api_token)
        headers = {"api_secret": self.api_secret}

        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        self._raise_for_status(r, "Login step 1 failed")

        data = r.json()
        otp_token = data.get("otp_token")
        if not otp_token:
            raise SessionError(f"otp_token missing in response: {data}")

        return otp_token

    def login_step2_with_totp(self, otp_token: str) -> Dict[str, Any]:
        """
        Completes login using TOTP (Google Authenticator style).
        """
        self._require(self.totp_secret, "TOTP secret not provided")

        # Generate current TOTP code (6-digit)
        totp = pyotp.TOTP(self.totp_secret)
        otp_code = totp.now()
        return self.login_step2_with_otp(otp_token, otp_code)

    def login_step2_with_otp(self, otp_token: str, otp_code: str) -> Dict[str, Any]:
        """
        Completes login using OTP (manual input).
        Returns response dict, and stores api_session_key & susertoken.
        """
        payload = {"otp_token": otp_token, "otp": otp_code}
        r = requests.post(LOGIN_STEP2_URL, json=payload, timeout=TIMEOUT)
        self._raise_for_status(r, "Login step 2 failed")

        data = r.json()
        if str(data.get("stat", "")).lower() != "ok":
            raise SessionError(f"Login step 2 not OK: {data}")

        self.api_session_key = data.get("api_session_key")
        self.susertoken = data.get("susertoken")
        self.uid = data.get("uid") or data.get("actid")
        self.last_login_ts = int(time.time())

        if not self.api_session_key or not self.susertoken:
            raise SessionError("Missing api_session_key or susertoken in token response")

        self._save_session()

        return data

    def login(self, prefer_totp: bool = True) -> Dict[str, Any]:
        """
        One-shot login helper:
        - Step1 → get otp_token
        - Step2 → verify via TOTP (if available & prefer_totp) else expects manual OTP (raise)
        """
        otp_token = self.login_step1()
        if prefer_totp and self.totp_secret:
            return self.login_step2_with_totp(otp_token)
        else:
            # For manual OTP flow, caller should call login_step2_with_otp(otp_token, otp_code)
            return {"otp_token": otp_token, "message": "Provide OTP via login_step2_with_otp()"}

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Headers for all trading endpoints (orders/positions/holdings/etc.)
        """
        self._require(self.api_session_key, "No api_session_key — please login first")
        return {"Authorization": self.api_session_key}

    def get_ws_token(self) -> str:
        """
        Returns susertoken for WebSocket subscription.
        """
        self._require(self.susertoken, "No susertoken — please login first")
        return self.susertoken

    def is_logged_in(self) -> bool:
        return bool(self.api_session_key and self.susertoken)

    def logout(self) -> None:
        self.api_session_key = None
        self.susertoken = None
        self.uid = None
        self.last_login_ts = None
        if os.path.exists(self.persist_path):
            os.remove(self.persist_path)

    # ---------- Internals ----------

    def _ensure_dirs(self):
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)

    def _save_session(self):
        blob = {
            "api_session_key": self.api_session_key,
            "susertoken": self.susertoken,
            "uid": self.uid,
            "last_login_ts": self.last_login_ts,
        }
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(blob, f)

    def _load_session(self):
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                blob = json.load(f)
            self.api_session_key = blob.get("api_session_key")
            self.susertoken = blob.get("susertoken")
            self.uid = blob.get("uid")
            self.last_login_ts = blob.get("last_login_ts")
        except Exception:
            # If corrupted, ignore
            pass

    @staticmethod
    def _raise_for_status(resp: requests.Response, msg: str):
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            detail = ""
            try:
                detail = f" | body={resp.text[:500]}"
            except Exception:
                pass
            raise SessionError(f"{msg}: {e}{detail}") from e

    @staticmethod
    def _require(value, err: str):
        if not value:
            raise SessionError(err)
