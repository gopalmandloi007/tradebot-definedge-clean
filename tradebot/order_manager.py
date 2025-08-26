# core/order_manager.py

import logging
from core.api_client import APIClient

logger = logging.getLogger(__name__)

class OrderManager:
    """
    Handles placing, modifying and cancelling orders.
    """

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def place_order(self, order_data: dict):
        """
        Place an order via /placeorder API
        """
        try:
            response = self.api_client.post("/placeorder", json=order_data)
            return response
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"status": "FAILED", "message": str(e)}
