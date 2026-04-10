
import os
import pandas as pd
import time
import random
import sys

# Windows에서 한국어 출력을 위해 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

try:
    import scraper
    import config
    import mapogu_fetcher
except ImportError:
    from . import scraper, config, mapogu_fetcher

def main():
    print("=== 네이버 부동산 실거래가 수집기 (5개년) ===")
    
    # config에 따라 단지 목록 가져오기
    if getattr(config, 'USE_DYNAMIC_COMPLEX_LIST', False):
        print("🔄 동적 단지 목록 수집 중...")
        complex_list = mapogu_fetcher.get_all_complex_ids()
    else:
        complex_list = config.COMPLEX_NUMBERS
        
    print(f"대상 단지 수: {len(complex_list)}개")

    all_data = []

    for complex_no in complex_list:
        print(f"\n[{complex_no}] 단지 정보 조회 중...")
        complex_info = scraper.fetch_complex_info(complex_no)
        detail = complex_info.get('detail', {})
        pyeong_list = complex_info.get('pyeongList', [])
        
        complex_name = detail.get('complexName', f"Complex_{complex_no}")
        print(f"🏢 단지명: {complex_name}")

        # pyeongNo -> pyeongName2(평수) 매핑 생성
        pyeong_map = {p.get('pyeongNo'): f"{p.get('pyeongName2')}평" for p in pyeong_list}
        
        if not pyeong_map:
             print("  ⚠️ 평형 정보가 없어 수집을 건너뜁니다.")
             continue

        # 매매(A1), 전세(B1) 모두 수집
        for trade_type, type_name in [('A1', '매매'), ('B1', '전세')]:
            print(f"  [{type_name}] 수집 시작...")
            for p_no, p_name in pyeong_map.items():
                print(f"    - {p_name} ({p_no}번) 데이터 수집 시도...", end=" ", flush=True)
                # 최근 데이터 수집 (년단위 조회 기간을 5년으로 확대)
                df_area = scraper.fetch_real_price_history(complex_no, p_no, trade_type=trade_type, year=5)
                
                if not df_area.empty:
                    df_area['아파트명'] = complex_name
                    df_area['단지번호'] = complex_no
                    df_area['면적번호'] = p_no
                    df_area['평형'] = p_name
                    df_area['거래구분'] = type_name
                    all_data.append(df_area)
                    print(f"✅ {len(df_area)}건 수집")
                else:
                    print("❌ 데이터 없음")
                    
                time.sleep(random.uniform(0.5, 1.2)) # 지연 시간 (많은 요청을 위해 적절히 유지)
            
            # 타입 간 지연
            time.sleep(random.uniform(1.0, 2.0))
        
        # 단지 간 지연
        time.sleep(random.uniform(1.0, 3.0))

    if not all_data:
        print("\n⚠️ 수집된 실거래가 데이터가 없습니다.")
        return

    final_df = pd.concat(all_data, ignore_index=True)
    
    # 데이터 저장
    history_file = "real_transaction_history.csv"
    file_path = os.path.join(config.DATA_DIR, history_file)
    
    # 기존 데이터와 병합 (중복 제거)
    if os.path.exists(file_path):
        try:
            old_df = pd.read_csv(file_path, encoding='utf-8-sig')
            final_df = pd.concat([old_df, final_df], ignore_index=True).drop_duplicates(
                subset=['날짜', '가격', '층', '아파트명'], keep='first'
            )
        except Exception as e:
            print(f"⚠️ 기존 파일 로드 중 오류 발생: {e}")

    final_df = final_df.sort_values(by=['아파트명', '날짜'], ascending=[True, False])
    final_df.to_csv(file_path, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ 수집 완료! 데이터가 '{history_file}'에 저장되었습니다. (총 {len(final_df)}건)")
    print("이제 'streamlit run app_visualizer.py'를 실행하여 시각화할 수 있습니다.")

if __name__ == "__main__":
    main()
