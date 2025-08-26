# core/positions_manager.py

import logging
from core.api_client import APIClient

logger = logging.getLogger(__name__)

class PositionsManager:
    """
    Manages fetching and handling of Position Book data.
    """

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def get_positions(self):
        """
        Fetch today's positions using /positions API.
        """
        try:
            response = self.api_client.get("/positions")
            if response.get("status") == "SUCCESS":
                return response.get("positions", [])
            else:
                logger.warning(f"Positions fetch failed: {response.get('message')}")
                return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_net_positions_summary(self):
        """
        Returns summary of net positions (PnL, net qty, etc.)
        """
        positions = self.get_positions()
        summary = {
            "total_net_qty": 0,
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
        }

        for pos in positions:
            try:
                net_qty = int(pos.get("net_quantity", 0))
                realized = float(pos.get("realized_pnl", 0))
                unrealized = float(pos.get("unrealized_pnl", 0))

                summary["total_net_qty"] += net_qty
                summary["total_realized_pnl"] += realized
                summary["total_unrealized_pnl"] += unrealized
            except Exception as e:
                logger.error(f"Error parsing position row: {e}")

        return summary
