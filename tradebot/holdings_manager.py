import logging
from .api_client import APIClient
from .historical_data import HistoricalDataManager

logger = logging.getLogger(__name__)

class HoldingsManager:
    def __init__(self, api_client: APIClient, historical_manager: HistoricalDataManager):
        self.api_client = api_client
        self.historical_manager = historical_manager

    def get_holdings(self):
        """
        Fetch holdings from API and enrich with LTP & Previous Close.
        """
        url = "/holdings"
        response = self.api_client.get(url)

        if response.get("status") != "SUCCESS":
            logger.error("Failed to fetch holdings: %s", response)
            return []

        final_holdings = []

        for h in response.get("data", []):
            for sym in h.get("tradingsymbol", []):
                exchange = sym.get("exchange")
                token = sym.get("token")
                symbol_name = sym.get("tradingsymbol")

                # Step 1: Get LTP (Quotes API)
                quote_resp = self.api_client.get(f"/quotes/{exchange}/{token}")
                ltp = None
                if quote_resp.get("status") == "SUCCESS":
                    ltp = quote_resp["data"].get("ltp")

                # Step 2: Get Previous Close (Historical API)
                prev_close = self.historical_manager.get_previous_close(exchange, token)

                # Step 3: Append processed holding
                holding = {
                    "exchange": exchange,
                    "symbol": symbol_name,
                    "token": token,
                    "isin": sym.get("isin"),
                    "avg_buy_price": float(h.get("avg_buy_price", 0)),
                    "dp_qty": int(h.get("dp_qty", 0)),
                    "t1_qty": int(h.get("t1_qty", 0)),
                    "ltp": ltp,
                    "prev_close": prev_close
                }

                final_holdings.append(holding)

        logger.info("Processed %d holdings", len(final_holdings))
        return final_holdings
