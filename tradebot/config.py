# Centralized config for local development. Use Streamlit secrets or env vars in production.
import os
BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"
HISTORY_URL_TEMPLATE = "https://data.definedgesecurities.com/sds/history/{segment}/{token}/{timeframe}/{from_ts}/{to_ts}"
MASTER_URLS = {
    "nsecash": "https://app.definedgesecurities.com/public/nsecash.zip",
    "nsefno": "https://app.definedgesecurities.com/public/nsefno.zip",
    "mcxfno": "https://app.definedgesecurities.com/public/mcxfno.zip",
    "all": "https://app.definedgesecurities.com/public/allmaster.zip"
}
