from curl_cffi import requests
import json
import pandas as pd
import time
import random
try:
    from . import config
except ImportError:
    import config

def get_session():
    from scraper import get_session
    return get_session()

def fetch_mapogu_neighborhoods():
    """
    마포구의 법정동 리스트를 가져와서 특정 동의 cortarNo를 반환
    """
    url = "https://new.land.naver.com/api/regions/list?cortarNo=1144000000"
    session = get_session()
    
    target_dong_names = [
        "창전동", "신수동", "대흥동", "용강동", "염리동", 
        "공덕동", "구수동", "현석동", "도화동", "신공덕동"
    ]
    
    try:
        response = session.get(url, cookies=config.COOKIES, headers=config.HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        neighborhoods = data.get('regionList', [])
        target_neighborhoods = []
        
        for n in neighborhoods:
            if n.get('cortarName') in target_dong_names:
                target_neighborhoods.append({
                    'cortarNo': n.get('cortarNo'),
                    'cortarName': n.get('cortarName')
                })
        
        return target_neighborhoods
    except Exception as e:
        print(f"Error fetching neighborhoods: {e}")
        return []

def fetch_complexes_by_neighborhood(cortar_no):
    """
    특정 동(cortarNo)에 속한 모든 단지 정보를 가져옴
    """
    url = f"https://new.land.naver.com/api/regions/complexes?cortarNo={cortar_no}&realEstateType=APT%3AABYG%3AJGC%3APRE&order="
    session = get_session()
    
    try:
        response = session.get(url, cookies=config.COOKIES, headers=config.HEADERS, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        complex_list = data.get('complexList', [])
        return complex_list
    except Exception as e:
        print(f"Error fetching complexes for cortarNo {cortar_no}: {e}")
        return []

def get_all_complex_ids(with_details=False):
    """
    마포구 10개 동의 모든 아파트 단지 ID 리스트(및 정보)를 반환
    config.MIN_HOUSEHOLD_COUNT 이상인 단지만 포함
    """
    neighborhoods = fetch_mapogu_neighborhoods()
    if not neighborhoods:
        return [] if not with_details else {}

    min_households = getattr(config, 'MIN_HOUSEHOLD_COUNT', 0)
    
    if with_details:
        complex_details = {}
        for dong in neighborhoods:
            complexes = fetch_complexes_by_neighborhood(dong['cortarNo'])
            for cp in complexes:
                household_count = cp.get('totalHouseholdCount', 0)
                if household_count >= min_households:
                    complex_ids = str(cp.get('complexNo'))
                    complex_details[complex_ids] = {
                        'totalHouseholdCount': household_count,
                        'useApproveYmd': cp.get('useApproveYmd')
                    }
            time.sleep(random.uniform(0.5, 1))
        return complex_details
    else:
        complex_ids = []
        for dong in neighborhoods:
            complexes = fetch_complexes_by_neighborhood(dong['cortarNo'])
            for cp in complexes:
                if cp.get('totalHouseholdCount', 0) >= min_households:
                    complex_ids.append(str(cp.get('complexNo')))
            time.sleep(random.uniform(0.5, 1))
        return list(set(complex_ids))

def main():
    print("--- 마포구 특정 동 정보 수집 시작 ---")
    neighborhoods = fetch_mapogu_neighborhoods()
    
    if not neighborhoods:
        print("동 정보를 가져오는데 실패했습니다.")
        return

    all_complexes = []
    min_households = getattr(config, 'MIN_HOUSEHOLD_COUNT', 0)
    print(f"필터 기준: {min_households}세대 이상")
    
    for dong in neighborhoods:
        print(f"[{dong['cortarName']}({dong['cortarNo']})] 단지 정보 수집 중...")
        complexes = fetch_complexes_by_neighborhood(dong['cortarNo'])
        
        for cp in complexes:
            household_count = cp.get('totalHouseholdCount', 0)
            if household_count >= min_households:
                all_complexes.append({
                    'dongName': dong['cortarName'],
                    'complexNo': cp.get('complexNo'),
                    'complexName': cp.get('complexName'),
                    'totalHouseholdCount': household_count,
                    'useApproveYmd': cp.get('useApproveYmd')
                })
        
        # API 과부하 방지를 위한 랜덤 딜레이
        time.sleep(random.uniform(1, 2))

    if all_complexes:
        df = pd.DataFrame(all_complexes)
        filename = "mapogu_complexes.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"\n--- 수집 완료 (총 {len(all_complexes)}개 단지) ---")
        print(f"결과가 {filename}에 저장되었습니다.\n")
        
        print("--- 단지 리스트 ---")
        for idx, row in df.iterrows():
            print(f"[{row['dongName']}] {row['complexName']} (ID: {row['complexNo']}, 세대수: {row['totalHouseholdCount']})")
    else:
        print("수집된 단지 정보가 없습니다.")

if __name__ == "__main__":
    main()
