import pandas as pd

def clean_orderbook(data):
    """Clean orderbook data for display."""
    df = pd.DataFrame(data)
    if not df.empty:
        df = df[["order_id", "tradingsymbol", "order_type", "quantity", "price", "order_status"]]
    return df

def clean_positions(data):
    """Clean positions data."""
    df = pd.DataFrame(data)
    if not df.empty:
        df = df[["tradingsymbol", "net_qty", "avg_price", "last_price", "pnl"]]
    return df

def clean_holdings(data):
    """Clean holdings data."""
    df = pd.DataFrame(data)
    if not df.empty:
        df = df[["tradingsymbol", "quantity", "avg_price", "last_price", "pnl"]]
    return df
