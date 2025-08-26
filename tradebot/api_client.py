"""
DRY HTTP client for Definedge Trading API
Usage:
  client = APIClient(session_mgr)
  r = client.get("/positions")
"""

from __future__ import annotations
import requests
from typing import Optional, Dict, Any

BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"
TIMEOUT = 20


class APIClientError(Exception):
    pass


class APIClient:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    def _url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return BASE_URL.rstrip("/") + "/" + path.lstrip("/")

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        h.update(self.session_manager.get_auth_headers())
        if extra:
            h.update(extra)
        return h

    def get(self, path: str, params: Optional[Dict[str, Any]] = None):
        url = self._url(path)
        r = requests.get(url, headers=self._headers(), params=params, timeout=TIMEOUT)
        self._raise_for_status(r, f"GET {path} failed")
        return r.json()

    def post(self, path: str, json: Optional[Dict[str, Any]] = None):
        url = self._url(path)
        r = requests.post(url, headers=self._headers(), json=json, timeout=TIMEOUT)
        self._raise_for_status(r, f"POST {path} failed")
        return r.json()

    @staticmethod
    def _raise_for_status(resp: requests.Response, msg: str):
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            body = ""
            try:
                body = f" | body={resp.text[:500]}"
            except Exception:
                pass
            raise APIClientError(f"{msg}: {e}{body}") from e
