import os
import pandas as pd

# Cache for master symbols
_symbol_df = None

def load_symbols(file_path: str = "data/symbol_master.csv") -> pd.DataFrame:
    """
    Load symbol master file into a DataFrame.
    Handles 14 or 15 columns automatically.
    Caches the result in memory for performance.
    """
    global _symbol_df
    if _symbol_df is not None:
        return _symbol_df

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Symbol master file not found: {file_path}")

    # Try loading with different column counts
    try:
        df = pd.read_csv(file_path, header=None, dtype=str)
    except Exception as e:
        raise RuntimeError(f"❌ Failed to read symbol file: {e}")

    # Normalize columns
    col_count = df.shape[1]
    if col_count == 14:
        df.columns = [
            "EXCH", "TOKEN", "SYMBOL", "NAME", "INSTRUMENT",
            "EXPIRY", "LOT_SIZE", "STRIKE", "OPTION_TYPE",
            "UNDERLYING", "TICK_SIZE", "MULTIPLIER",
            "ISIN", "EXTRA"
        ]
    elif col_count == 15:
        df.columns = [
            "EXCH", "TOKEN", "SYMBOL", "NAME", "INSTRUMENT",
            "EXPIRY", "LOT_SIZE", "STRIKE", "OPTION_TYPE",
            "UNDERLYING", "TICK_SIZE", "MULTIPLIER",
            "ISIN", "EXTRA", "DESCRIPTION"
        ]
    else:
        raise ValueError(f"❌ Unexpected column count in master file: {col_count}")

    _symbol_df = df
    print(f"✅ Loaded {len(df)} symbols with {col_count} columns")
    return _symbol_df


def search_symbols(query: str, max_results: int = 10) -> pd.DataFrame:
    """
    Search for symbols by keyword in SYMBOL, NAME, or DESCRIPTION.
    Returns top `max_results`.
    """
    df = load_symbols()

    query = str(query).upper()
    search_cols = [col for col in ["SYMBOL", "NAME", "DESCRIPTION"] if col in df.columns]

    if not search_cols:
        raise KeyError("❌ No searchable column (SYMBOL/NAME/DESCRIPTION) found in master file")

    mask = pd.Series(False, index=df.index)
    for col in search_cols:
        mask |= df[col].astype(str).str.contains(query, na=False, case=False)

    results = df[mask].head(max_results)
    if results.empty:
        print(f"⚠️ No results found for query: {query}")
    return results
