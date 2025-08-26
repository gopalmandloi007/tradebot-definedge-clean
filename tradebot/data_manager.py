import os
import json

class DataManager:
    """
    Handles saving/loading of data in data/ folder.
    """

    BASE_DIR = "data"

    def __init__(self):
        self.historical_dir = os.path.join(self.BASE_DIR, "historical")
        self.symbol_dir = os.path.join(self.BASE_DIR, "symbol")
        os.makedirs(self.historical_dir, exist_ok=True)
        os.makedirs(self.symbol_dir, exist_ok=True)

    def save_json(self, filepath, data):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_json(self, filepath, default=None):
        if not os.path.exists(filepath):
            return default
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_symbol_list(self, name, data):
        path = os.path.join(self.symbol_dir, f"{name}.json")
        self.save_json(path, data)

    def load_symbol_list(self, name):
        path = os.path.join(self.symbol_dir, f"{name}.json")
        return self.load_json(path, default=[])
