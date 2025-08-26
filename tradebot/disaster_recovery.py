# src/tradebot/disaster_recovery.py

from .api_client import APIClient

class DisasterRecoveryManager:
    def __init__(self, client: APIClient):
        self.client = client

    # Cancel all open orders
    def cancel_all_orders(self):
        return self.client.delete("/orders")

    # Cancel selected orders
    def cancel_selected_orders(self, order_ids: list[str]):
        results = []
        for oid in order_ids:
            results.append(self.client.delete(f"/orders/{oid}"))
        return results

    # Modify all open orders to market
    def modify_all_orders_to_market(self):
        orders = self.client.get("/orders")
        results = []
        for order in orders:
            if order.get("status") in ["open", "pending"]:
                oid = order["order_id"]
                payload = {
                    "order_id": oid,
                    "price_type": "MARKET"
                }
                results.append(self.client.put(f"/orders/{oid}", payload))
        return results

    # Modify selected orders to market
    def modify_selected_orders_to_market(self, order_ids: list[str]):
        results = []
        for oid in order_ids:
            payload = {
                "order_id": oid,
                "price_type": "MARKET"
            }
            results.append(self.client.put(f"/orders/{oid}", payload))
        return results
