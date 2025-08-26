import pandas as pd
import os
from datetime import datetime

def save_to_csv(data, filename_prefix="data"):
    """Save any list/dict data to CSV file."""
    df = pd.DataFrame(data)
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    return filename

def save_to_excel(data, filename_prefix="data"):
    """Save data to Excel file."""
    df = pd.DataFrame(data)
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(filename, index=False)
    return filename
