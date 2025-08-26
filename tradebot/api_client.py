# api_client: thin REST wrapper (attach headers, retries)
import requests
from .session_manager import SessionManager
class APIClient:
    def __init__(self, session_manager: SessionManager):
        self.session = session_manager

    def _headers(self):
        return {"Authorization": self.session.api_session_key} if self.session.api_session_key else {}

    def get(self, path, params=None):
        # implement GET
        raise NotImplementedError

    def post(self, path, json=None):
        # implement POST
        raise NotImplementedError
