from scraper import fetch_all_data
import config

print(f"USE_DYNAMIC_COMPLEX_LIST: {getattr(config, 'USE_DYNAMIC_COMPLEX_LIST', False)}")

# We don't want to actually scrape everything (it would take too long), 
# so we'll just verify the initial part of fetch_all_data.
# I'll monkeypatch time.sleep to make it faster if needed, 
# but for now I just want to see if the "단지 리스트 동적 수집 중" message appears.

try:
    print("Starting fetch_all_data test...")
    # Just run it for a bit and then interrupt if it's working
    df = fetch_all_data()
    print(f"Scraped {len(df)} articles.")
except Exception as e:
    print(f"Test encountered an error (this might be expected if we interrupt): {e}")

print("Test complete.")
