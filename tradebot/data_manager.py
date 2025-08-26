# data_manager: read/write history/trades/orders to disk (parquet/csv)
import os
def ensure_dirs():
    os.makedirs('data/master', exist_ok=True)
    os.makedirs('data/history', exist_ok=True)
    os.makedirs('data/trades', exist_ok=True)
    os.makedirs('data/orders', exist_ok=True)
ensure_dirs()
