import logging
import requests
from tradebot.session_manager import SessionManager, SessionError

logger = logging.getLogger(__name__)

class OCOOrderManager:
    def __init__(self, session: SessionManager):
        if not session or not session.is_logged_in():
            raise SessionError("Session is not active. Please login first.")
        self.session = session
        self.base_url = "https://api.definedgesecurities.com"

    def place_oco_order(self, remarks, tradingsymbol, exchange, order_type,
                        target_quantity, stoploss_quantity, target_price,
                        stoploss_price, product_type="CNC"):
        """
        Place OCO order
        """
        url = f"{self.base_url}/ocoplaceorder"
        headers = self.session.get_auth_headers()
        payload = {
            "remarks": remarks,
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "order_type": order_type,
            "target_quantity": target_quantity,
            "stoploss_quantity": stoploss_quantity,
            "target_price": target_price,
            "stoploss_price": stoploss_price,
            "product_type": product_type
        }

        logger.info(f"Placing OCO order: {payload}")
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def place_multiple_oco(self, configs):
        """
        Place multiple OCOs (list of dict configs)
        Example:
        configs = [
          {"remarks":"Target1", "tradingsymbol":"NIFTY29MAR23F","exchange":"NFO",
           "order_type":"SELL","target_quantity":50,"stoploss_quantity":50,
           "target_price":17000,"stoploss_price":17300,"product_type":"NORMAL"},
          {"remarks":"Target2", "tradingsymbol":"NIFTY29MAR23F","exchange":"NFO",
           "order_type":"SELL","target_quantity":50,"stoploss_quantity":50,
           "target_price":17100,"stoploss_price":17350,"product_type":"NORMAL"}
        ]
        """
        results = []
        for cfg in configs:
            try:
                res = self.place_oco_order(**cfg)
                results.append(res)
            except Exception as e:
                logger.error(f"OCO order failed: {e}")
                results.append({"status":"FAILED","error":str(e)})
        return results
