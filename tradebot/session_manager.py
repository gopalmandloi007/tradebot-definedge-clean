# session_manager: login, store api_session_key & susertoken
import requests
from .config import BASE_URL
class SessionManager:
    def __init__(self, api_secret):
        self.api_secret = api_secret
        self.api_session_key = None
        self.susertoken = None

    def login(self, api_token):
        # Implement login call to token endpoint and set api_session_key & susertoken
        raise NotImplementedError
