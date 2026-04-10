import scraper
import config
import os

# Override complex numbers for quick test
config.COMPLEX_NUMBERS = config.COMPLEX_NUMBERS[:1]

try:
    print("Testing scraper with a single complex...")
    df = scraper.fetch_all_data()
    if not df.empty:
        print(f"Success! Fetched {len(df)} records from 1 complex.")
    else:
        print("Scraper returned empty dataframe.")
except Exception as e:
    print(f"Scraper failed: {e}")
