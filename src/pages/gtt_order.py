import logging
import requests
from tradebot.session_manager import SessionManager, SessionError

logger = logging.getLogger(__name__)

class GTTOrderManager:
    def __init__(self, session: SessionManager):
        if not session or not session.is_logged_in():
            raise SessionError("Session is not active. Please login first.")
        self.session = session
        self.base_url = "https://api.definedgesecurities.com"

    def place_gtt_order(self, exchange, tradingsymbol, order_type, condition,
                        alert_price, price, quantity, product_type="CNC"):
        """
        Place GTT order
        """
        url = f"{self.base_url}/gttplaceorder"
        headers = self.session.get_auth_headers()
        payload = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "condition": condition,       # LTP_ABOVE / LTP_BELOW
            "alert_price": alert_price,   # Trigger price
            "order_type": order_type,     # BUY / SELL
            "price": price,               # Actual order price
            "quantity": quantity,
            "product_type": product_type
        }

        logger.info(f"Placing GTT order: {payload}")
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def place_multiple_gtt(self, configs):
        """
        Place multiple GTTs (list of dict configs)
        Example:
        configs = [
          {"exchange":"NSE", "tradingsymbol":"INFY", "order_type":"BUY", "condition":"LTP_ABOVE",
           "alert_price":1500, "price":1505, "quantity":10, "product_type":"CNC"},
          {"exchange":"NSE", "tradingsymbol":"INFY", "order_type":"SELL", "condition":"LTP_BELOW",
           "alert_price":1400, "price":1395, "quantity":10, "product_type":"CNC"}
        ]
        """
        results = []
        for cfg in configs:
            try:
                res = self.place_gtt_order(**cfg)
                results.append(res)
            except Exception as e:
                logger.error(f"GTT order failed: {e}")
                results.append({"status":"FAILED","error":str(e)})
        return results
