import requests
from tradebot.session_manager import SessionManager, SessionError

class GTTModifyManager:
    def __init__(self, session: SessionManager):
        if not session or not session.is_logged_in():
            raise SessionError("Session not active. Login first.")
        self.session = session
        self.base_url = "https://api.definedgesecurities.com"

    def modify_gtt(self, exchange, alert_id, tradingsymbol, condition,
                   alert_price, order_type, price, quantity, product_type="CNC"):
        """
        Modify GTT Order
        """
        url = f"{self.base_url}/gttmodify"
        headers = self.session.get_auth_headers()
        payload = {
            "exchange": exchange,
            "alert_id": alert_id,
            "tradingsymbol": tradingsymbol,
            "condition": condition,
            "alert_price": alert_price,
            "order_type": order_type,
            "price": price,
            "quantity": quantity,
            "product_type": product_type
        }
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def cancel_gtt(self, alert_id):
        url = f"{self.base_url}/gttcancel/{alert_id}"
        headers = self.session.get_auth_headers()
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
