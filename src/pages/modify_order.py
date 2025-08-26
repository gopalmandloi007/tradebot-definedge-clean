import requests
from tradebot.session_manager import SessionManager, SessionError

class NormalOrderManager:
    def __init__(self, session: SessionManager):
        if not session or not session.is_logged_in():
            raise SessionError("Session not active. Login first.")
        self.session = session
        self.base_url = "https://api.definedgesecurities.com"

    def modify_order(self, exchange, order_id, tradingsymbol, quantity,
                     price, product_type, order_type, price_type,
                     disclosed_quantity=0, remarks=None, trigger_price=None,
                     validity="DAY"):
        """
        Modify existing Normal Order
        """
        url = f"{self.base_url}/modify"
        headers = self.session.get_auth_headers()
        payload = {
            "exchange": exchange,
            "order_id": order_id,
            "tradingsymbol": tradingsymbol,
            "quantity": quantity,
            "price": price,
            "product_type": product_type,
            "order_type": order_type,
            "price_type": price_type,
            "validity": validity
        }
        if remarks:
            payload["remarks"] = remarks
        if trigger_price:
            payload["trigger_price"] = trigger_price
        if disclosed_quantity:
            payload["disclosed_quantity"] = disclosed_quantity

        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def cancel_order(self, order_id):
        """
        Cancel existing Normal Order
        """
        url = f"{self.base_url}/cancel/{order_id}"
        headers = self.session.get_auth_headers()
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

