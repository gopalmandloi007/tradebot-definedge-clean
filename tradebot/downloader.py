import os
from datetime import datetime
from .data_manager import DataManager

class Downloader:
    """
    Downloader for historical data.
    Ensures incremental download (no duplicate data).
    """

    def __init__(self, client, data_manager=None):
        self.client = client
        self.dm = data_manager or DataManager()

    def download_historical(self, symbol, segment="EQ"):
        """
        Download incremental historical data for given symbol.
        """
        folder = os.path.join(self.dm.historical_dir, segment)
        os.makedirs(folder, exist_ok=True)

        file_path = os.path.join(folder, f"{symbol}.json")
        existing = self.dm.load_json(file_path, default=[])

        last_date = None
        if existing:
            last_date = existing[-1].get("date")

        # call API (placeholder)
        new_data = self.client.get_historical(symbol, segment, from_date=last_date)

        if not new_data:
            return existing

        updated = existing + new_data
        self.dm.save_json(file_path, updated)
        return updated
