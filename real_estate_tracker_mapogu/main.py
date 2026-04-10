
import schedule
import time
import os
import pandas as pd
from datetime import datetime
import scraper
import processor
import notifier
import config

def job():
    current_time = datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')
    new_raw_file_name = f"{current_time.strftime('%Y%m%d_%H%M')}_raw.csv"
    new_min_file_name = f"{current_time.strftime('%Y%m%d_%H%M')}.csv"
    
    # Use paths from config
    previous_file_path = os.path.join(config.DATA_DIR, config.PREVIOUS_FILE_NAME)
    history_file_path = os.path.join(config.DATA_DIR, config.HISTORY_FILE_NAME)
    price_drops_path = os.path.join(config.DATA_DIR, config.PRICE_DROPS_FILE)
    
    print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 최저가 매물 데이터 수집 및 비교 시작...")
    
    try:
        if os.path.exists(previous_file_path):
            last_df = pd.read_csv(previous_file_path, encoding='utf-8-sig', dtype={'매물번호': str}) 
        else:
            last_df = pd.DataFrame()
            
        raw_df = scraper.fetch_all_data()

        # Save raw data if needed, maybe move to a raw/ folder later
        raw_file_path = os.path.join(config.DATA_DIR, new_raw_file_name)
        raw_df.to_csv(raw_file_path, index=False, encoding='utf-8-sig')
        print(f"✅ 원시 데이터가 '{new_raw_file_name}' 파일에 저장되었습니다.")

        current_df = processor.process_data(raw_df) 
        if current_df.empty:
            print("⚠️ 가공된 데이터가 없습니다.")
            return

        min_file_path = os.path.join(config.DATA_DIR, new_min_file_name)
        current_df.to_csv(min_file_path, index=False, encoding='utf-8-sig')
        print(f"🎉 최저가 데이터가 '{new_min_file_name}' 파일에 저장되었습니다.")
        
        # Save current to previous file for next run
        current_df.to_csv(previous_file_path, index=False, encoding='utf-8-sig')
        
        # Add '생성일시'
        current_df['생성일시'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Update history file
        if os.path.exists(history_file_path):
            history_df = pd.read_csv(history_file_path, encoding='utf-8-sig', dtype={'매물번호': str})
            # Filter out today's data to overwrite
            history_df['날짜'] = pd.to_datetime(history_df['생성일시']).dt.strftime('%Y-%m-%d')
            history_df = history_df[history_df['날짜'] != current_date]
            history_df = pd.concat([history_df, current_df], ignore_index=True)
            history_df = history_df.drop(columns=['날짜']) 
            
            history_df.to_csv(history_file_path, index=False, encoding='utf-8-sig')
            print(f"🎉 누적 파일 '{config.HISTORY_FILE_NAME}'에 오늘 데이터로 대체 완료.")
        else:
            history_df = current_df.copy()
            history_df.to_csv(history_file_path, index=False, encoding='utf-8-sig')
            print(f"🎉 누적 파일 '{config.HISTORY_FILE_NAME}' 생성 완료.")

        # --- Dual Save Logic ---
        # User requested to also save to 'real_estate_tracker' folder (where this script likely resides)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        secondary_history_path = os.path.join(script_dir, config.HISTORY_FILE_NAME)
        
        # Check if the primary save path is different from the script directory path
        if os.path.abspath(history_file_path) != secondary_history_path:
            try:
                history_df.to_csv(secondary_history_path, index=False, encoding='utf-8-sig')
                print(f"🎉 [Dual Save] 누적 파일이 '{secondary_history_path}' 에도 저장되었습니다.")
            except Exception as e:
                print(f"⚠️ [Dual Save] 추가 저장 실패: {e}")
        # -----------------------

        # Compare for price drops
        if not last_df.empty:
            price_drop_df = processor.detect_price_drops(last_df, current_df)
            
            if not price_drop_df.empty:
                print("👍 가격이 하락한 매물이 발견되었습니다!")
                
                # 실거래 히스토리 로드 (통계 계산용)
                # 1. config.DATA_DIR 확인
                real_history_file = os.path.join(config.DATA_DIR, "real_transaction_history.csv")
                
                # 2. 파일이 없으면 스크립트 디렉토리 확인
                if not os.path.exists(real_history_file):
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    real_history_file = os.path.join(script_dir, "real_transaction_history.csv")
                
                history_df_real = pd.DataFrame()
                if os.path.exists(real_history_file):
                    try:
                        history_df_real = pd.read_csv(real_history_file, encoding='utf-8-sig')
                        history_df_real['날짜'] = pd.to_datetime(history_df_real['날짜'])
                        print(f"📖 실거래 히스토리 로드 완료: {real_history_file} ({len(history_df_real)}건)")
                    except Exception as e:
                        print(f"⚠️ 실거래 히스토리 로드 실패: {e}")
                else:
                    print(f"⚠️ 실거래 히스토리 파일을 찾을 수 없습니다: {real_history_file}")
                    print(f"   (현재 경로: {os.getcwd()}, 스크립트 경로: {os.path.dirname(os.path.abspath(__file__))})")

                notification_message = f"🏠 네이버 부동산 가격 하락 알림! ({current_time.strftime('%Y-%m-%d %H:%M:%S')})\n\n"

                with open(price_drops_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n======== 가격 하락 발견: {current_time.strftime('%Y-%m-%d %H:%M:%S')} ========\n")
                    for _, row in price_drop_df.iterrows():
                        # 통계 계산
                        stats = None
                        if not history_df_real.empty:
                            try:
                                # 아파트명, 거래타입, 평형(공급평형 기준)으로 필터링
                                apt_name = str(row['아파트명']).replace(' ', '').strip()
                                trade_type = str(row['거래타입']).replace(' ', '').strip()
                                pyeong_val = int(round(row['공급면적(평수)_현재']))
                                pyeong_str = f"{pyeong_val}평"
                                
                                # 데이터프레임 값들도 정리 (매칭률 향상을 위해)
                                # 아파트명과 거래타입에서 공백을 모두 제거하고 비교
                                mask = (
                                    (history_df_real['아파트명'].str.replace(' ', '', regex=False) == apt_name) &
                                    (history_df_real['거래구분'].str.replace(' ', '', regex=False) == trade_type) &
                                    (history_df_real['평형'].str.contains(pyeong_str, na=False))
                                )
                                prop_history = history_df_real[mask].sort_values('날짜', ascending=False)
                                
                                if not prop_history.empty:
                                    stats = {}
                                    latest = prop_history.iloc[0]
                                    stats['recent_price'] = int(latest['정렬용가격'])
                                    stats['recent_date'] = latest['날짜'].strftime('%Y-%m-%d')
                                    
                                    one_year_ago = pd.Timestamp.now() - pd.Timedelta(days=365)
                                    last_1y = prop_history[prop_history['날짜'] >= one_year_ago]
                                    if not last_1y.empty:
                                        stats['avg_1y'] = int(last_1y['정렬용가격'].mean())
                                    
                                    print(f"✅ '{apt_name}' {pyeong_str} 매칭 성공 (실거래 {len(prop_history)}건)")
                                else:
                                    print(f"❌ 매칭 실패 상세:")
                                    print(f"  - 검색 조건: 아파트='{apt_name}', 거래='{trade_type}', 평형='{pyeong_str}'")
                                    # 근접한 데이터가 있는지 확인
                                    unique_apts = history_df_real['아파트명'].unique().tolist()
                                    unique_types = history_df_real['거래구분'].unique().tolist()
                                    print(f"  - 히스토리 내 아파트 목록(일부): {unique_apts[:5]}")
                                    print(f"  - 히스토리 내 거래타입 목록: {unique_types}")
                                    
                                    # 아파트명만이라도 맞는지 확인
                                    apt_only_mask = (history_df_real['아파트명'].str.replace(' ', '', regex=False) == apt_name)
                                    if any(apt_only_mask):
                                        apt_match = history_df_real[apt_only_mask]
                                        print(f"  - 아파트명은 일치함. 해당 아파트의 평형들: {apt_match['평형'].unique().tolist()}")
                                        print(f"  - 해당 아파트의 거래구분들: {apt_match['거래구분'].unique().tolist()}")
                                    else:
                                        print("  - 아파트명부터 일치하지 않습니다.")
                            except Exception as e:
                                print(f"⚠️ 통계 계산 중 오류 발생: {e}")
                                import traceback
                                traceback.print_exc()

                        record = notifier.format_price_drop_message(row, stats=stats)
                        print(record, end='') 
                        f.write(record)
                        notification_message += record

                notifier.send_all_notifications(notification_message)
            else:
                print("👍 가격이 하락한 매물이 없습니다.")
        else:
            print("ℹ️ 이전 데이터가 없어 가격 비교를 할 수 없습니다. 다음 실행부터 비교가 시작됩니다.")
            
    except Exception as e:
        print(f"❌ 작업 중 치명적인 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def run_scheduler():
    job() 
    schedule.every(60).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()