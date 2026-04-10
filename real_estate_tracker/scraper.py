
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import random
import pandas as pd
try:
    from . import config
except ImportError:
    import config

def get_session():
    session = requests.Session()
    retry = Retry(
        total=10,
        read=10,
        connect=10,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def fetch_all_data():
    """
    네이버 부동산에서 모든 매물 데이터를 수집하여 원시 데이터프레임을 반환
    """
    all_articles_data = []
    session = get_session()

    for complex_no in config.COMPLEX_NUMBERS:
        page = 1
        while True:
            # URL Construction
            url = f'https://new.land.naver.com/api/articles/complex/{complex_no}?realEstateType=APT%3AABYG%3AJGC%3APRE&tradeType=A1%3AB1&tag=%3A%3A%3A%3A%3A%3A%3A%3A&rentPriceMin=0&rentPriceMax=900000000&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&oldBuildYears&recentlyBuildYears&minHouseHoldCount=1000&maxHouseHoldCount&showArticle=false&sameAddressGroup=false&minMaintenanceCost&maxMaintenanceCost&priceType=RETAIL&directions=&page={page}&complexNo={complex_no}&buildingNos=&areaNos=&type=list&order=rank'
            
            try:
                # Making the request
                response = session.get(url, cookies=config.COOKIES, headers=config.HEADERS, verify=False, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'articleList' in data and data['articleList']:
                    for article in data['articleList']:
                        extracted_data = {key: article.get(key) for key in config.API_COLUMNS}
                        all_articles_data.append(extracted_data)
                    page += 1
                else:
                    break
            except requests.exceptions.RequestException as e:
                print(f"Error scraping complex {complex_no} page {page}: {e}")
                break
            
            # Randomized delay to mimic human behavior and avoid rate limits
            sleep_time = random.uniform(2, 5)
            time.sleep(sleep_time)
            
    return pd.DataFrame(all_articles_data)


def fetch_complex_info(complex_no):
    """
    단지 번호를 이용해 단지 기본 정보(이름, 면적 정보 등)를 가져옴
    """
    session = get_session()
    url = f'https://new.land.naver.com/api/complexes/{complex_no}'
    
    try:
        response = session.get(url, cookies=config.COOKIES, headers=config.HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'detail': data.get('complexDetail', {}),
            'pyeongList': data.get('complexPyeongDetailList', [])
        }
    except Exception as e:
        print(f"Error fetching complex info for {complex_no}: {e}")
        return {'detail': {}, 'pyeongList': []}

def fetch_real_price_history(complex_no, area_no, trade_type='A1', year=5):
    """
    네이버 부동산에서 해당 단지, 특정 면적의 실거래가 데이터를 수집 (페이징 처리)
    trade_type: 'A1'(매매), 'B1'(전세)
    year: 조회 기간 (년)
    """
    session = get_session()
    all_formatted_data = []
    added_row_count = 0
    max_pages = 10 # 무한 루프 방지
    
    for _ in range(max_pages):
        url = f'https://new.land.naver.com/api/complexes/{complex_no}/prices/real?complexNo={complex_no}&tradeType={trade_type}&year={year}&priceChartChange=false&areaNo={area_no}&addedRowCount={added_row_count}&type=table'
        
        try:
            response = session.get(url, cookies=config.COOKIES, headers=config.HEADERS, verify=False, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            month_list = data.get('realPriceOnMonthList', [])
            if not month_list:
                break
                
            batch_data = []
            batch_count = 0
            for month_data in month_list:
                transactions = month_data.get('realPriceList', [])
                for tx in transactions:
                    # 전세의 경우 dealPrice가 0이고 leasePrice에 값이 들어있음
                    price_val = tx.get('dealPrice', 0)
                    if price_val == 0:
                        price_val = tx.get('leasePrice', 0)
                    
                    price_str = ""
                    if price_val >= 10000:
                        억 = price_val // 10000
                        만 = price_val % 10000
                        price_str = f"{억}억" + (f" {만}만" if 만 > 0 else "")
                    else:
                        price_str = f"{price_val}만"
                    
                    year_val = str(tx.get('tradeYear', ''))
                    month = str(tx.get('tradeMonth', '')).zfill(2)
                    day = str(tx.get('tradeDate', '')).zfill(2)
                    date_str = f"{year_val}-{month}-{day}"
                    
                    batch_data.append({
                        '날짜': date_str,
                        '가격': price_str,
                        '정렬용가격': price_val,
                        '층': tx.get('floor'),
                        '거래타입': '매매' if trade_type == 'A1' else '전세'
                    })
                    batch_count += 1
            
            if not batch_data:
                break
                
            all_formatted_data.extend(batch_data)
            
            # 다음 페이지를 위해 오프셋 업데이트 (보통 한 페이지에 12-15건 정도인 듯함)
            # Naver API는 addedRowCount가 '지금까지 보여준 행 수'를 의미함
            added_row_count += batch_count
            
            # 데이터가 12개 미만으로 오면 다음 페이지가 없을 가능성이 높음
            if batch_count < 5: 
                break
                
            # 너무 옛날 데이터까지 갈 필요 없는 경우 체크 (year 파라미터가 이미 서버측에서 처리해주긴 함)
            
        except Exception as e:
            print(f"Error fetching real transactions batch for {complex_no} (offset {added_row_count}): {e}")
            break
            
    return pd.DataFrame(all_formatted_data)
