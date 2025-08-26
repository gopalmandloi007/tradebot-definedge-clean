import logging
from tradebot.api_client import APIClient
from tradebot.historical_data import HistoricalDataManager

logger = logging.getLogger(__name__)

class HoldingsManager:
    def __init__(self, api_client: APIClient, historical_data_manager: HistoricalDataManager):
        self.api_client = api_client
        self.historical_data_manager = historical_data_manager

    def get_holdings(self):
        """Fetch holdings from API"""
        url = "/holdings"
        response = self.api_client.get(url)
        if response.get("status") != "SUCCESS":
            logger.error(f"Error fetching holdings: {response}")
            return []
        return response.get("data", [])

    def enrich_holdings(self, holdings):
        """Add LTP and Previous Close for each holding"""
        enriched = []
        for h in holdings:
            for symbol in h["tradingsymbol"]:
                exchange = symbol["exchange"]
                token = symbol["token"]

                # ✅ Get LTP from /quotes
                quote_url = f"/quotes/{exchange}/{token}"
                quote_data = self.api_client.get(quote_url)
                ltp = None
                if quote_data.get("status") == "SUCCESS":
                    ltp = quote_data.get("data", {}).get("ltp")

                # ✅ Get Previous Close from Historical Data
                prev_close = self.historical_data_manager.get_previous_close(exchange, token)

                enriched.append({
                    "exchange": exchange,
                    "symbol": symbol["tradingsymbol"],
                    "token": token,
                    "isin": symbol["isin"],
                    "avg_buy_price": h.get("avg_buy_price"),
                    "dp_qty": h.get("dp_qty"),
                    "t1_qty": h.get("t1_qty"),
                    "holding_used": h.get("holding_used"),
                    "trade_qty": h.get("trade_qty"),
                    "sell_amt": h.get("sell_amt"),
                    "ltp": ltp,
                    "previous_close": prev_close
                })
        return enriched

    def get_enriched_holdings(self):
        """Complete flow: holdings + LTP + prev_close"""
        raw_holdings = self.get_holdings()
        return self.enrich_holdings(raw_holdings)
