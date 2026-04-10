
import streamlit as st
import pandas as pd
import plotly.express as px
import os
try:
    from . import config
except ImportError:
    import config

# Page config
st.set_page_config(page_title="Real Estate Tracker", page_icon="🏠", layout="wide")


def load_data(mode="현재 매물"):
    if mode == "현재 매물":
        file_path = os.path.join(config.DATA_DIR, config.HISTORY_FILE_NAME)
    else:
        file_path = os.path.join(config.DATA_DIR, "real_transaction_history.csv")
        
    if not os.path.exists(file_path):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except Exception as e:
        try:
            df = pd.read_csv(file_path, encoding='cp949')
        except Exception as e:
            st.error(f"데이터 로드 실패 ({file_path}): {e}")
            return pd.DataFrame()
    
    if mode == "현재 매물":
        if '생성일시' in df.columns:
            df['Date'] = pd.to_datetime(df['생성일시'])
            df['Day'] = df['Date'].dt.strftime('%Y-%m-%d')
        else:
            st.error("데이터에 '생성일시' 컬럼이 없습니다.")
            return pd.DataFrame()
    else:
        if '날짜' in df.columns:
            df['Date'] = pd.to_datetime(df['날짜'])
            df['Day'] = df['Date'].dt.strftime('%Y-%m-%d')
        else:
            st.error("데이터에 '날짜' 컬럼이 없습니다.")
            return pd.DataFrame()
            
    return df

def main():
    st.title("🏠 Real Estate Price Tracker")
    
    # Mode Selection
    view_mode = st.radio("시각화 모드 선택", ["현재 매물 추이", "실거래가 이력 (5년)"], horizontal=True, key="view_mode_selector")
    
    # Internal mode mapping
    internal_mode = "현재 매물" if view_mode == "현재 매물 추이" else "실거래가"
    df = load_data(internal_mode)
    
    if df.empty:
        if view_mode == "현재 매물 추이":
            st.warning(f"매물 데이터 파일이 없습니다: {config.HISTORY_FILE_NAME}")
            st.info("스크립트를 먼저 실행하여 데이터를 수집해주세요.")
        else:
            st.warning("실거래가 데이터 파일이 없습니다: real_transaction_history.csv")
            st.info("'python fetch_real_estate.py'를 실행하여 거래 데이터를 먼저 수집하세요.")
        return

    # Sidebar Filters
    st.sidebar.header("Filter Options")
    
    # 1. Apartment Selection (Default: 대흥태영)
    apartments = sorted(df['아파트명'].unique().tolist())
    default_apt = [a for a in apartments if "대흥태영" in a]
    selected_apartments = st.sidebar.multiselect("아파트 선택", apartments, 
                                               default=default_apt if default_apt else apartments, 
                                               key="apt_select")
    filtered_df = df[df['아파트명'].isin(selected_apartments)]
    
    # 2. Trade Type Selection (Default: 매매)
    if '거래타입' in filtered_df.columns:
        cat_col = '거래타입'
    elif '거래구분' in filtered_df.columns:
        cat_col = '거래구분'
    else:
        cat_col = None

    if cat_col:
        trade_cats = sorted(filtered_df[cat_col].unique().tolist())
        default_trade = [t for t in trade_cats if t == "매매"]
        selected_trade_cats = st.sidebar.multiselect("거래구분 선택", trade_cats, 
                                                   default=default_trade if default_trade else trade_cats, 
                                                   key="trade_cat_select")
        filtered_df = filtered_df[filtered_df[cat_col].isin(selected_trade_cats)]

    # 3. Pyeong Selection (Default: 33평)
    if view_mode == "현재 매물 추이":
        # '공급면적(평수)'를 반올림하여 'XX평' 문자열로 변환
        filtered_df['평형_display'] = filtered_df['공급면적(평수)'].round(0).astype(int).astype(str) + "평"
        pyeong_list = sorted(filtered_df['평형_display'].unique().tolist(), key=lambda x: int(x.replace('평', '')))
    else:
        filtered_df['평형_display'] = filtered_df['평형']
        # 실거래가 평단 정렬 (숫자 추출 가능하면 숫자로, 아님 그대로)
        try:
            pyeong_list = sorted(filtered_df['평형_display'].unique().tolist(), 
                                 key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
        except:
            pyeong_list = sorted(filtered_df['평형_display'].unique().tolist())

    default_pyeong = [p for p in pyeong_list if "33" in p]
    selected_pyeong = st.sidebar.multiselect("평형 선택 (동시 적용)", pyeong_list, 
                                           default=default_pyeong if default_pyeong else pyeong_list, 
                                           key="pyeong_select")
    filtered_df = filtered_df[filtered_df['평형_display'].isin(selected_pyeong)]

    if filtered_df.empty:
        st.warning("선택한 조건에 맞는 데이터가 없습니다.")
        return

    # --- Metrics ---
    col1, col2, col3 = st.columns(3)
    latest_date = filtered_df['Date'].max()
    
    with col1:
        st.metric("최신 데이터 기준 날짜", latest_date.strftime('%Y-%m-%d'))
    with col2:
        st.metric("총 데이터 수", len(filtered_df))
    with col3:
        if view_mode == "현재 매물 추이":
            latest_df = filtered_df[filtered_df['Date'] == latest_date]
            min_price = latest_df['정렬용가격'].min() if not latest_df.empty else 0
            st.metric("현재 최저가", f"{min_price:,}만원")
        else:
            avg_price = filtered_df['정렬용가격'].mean()
            st.metric("평균 거래가 (필터 기준)", f"{int(avg_price):,}만원")

    # --- Charts ---
    st.subheader(f"📈 {view_mode} 그래프")
    filtered_df = filtered_df.sort_values(by='Date')

    if view_mode == "현재 매물 추이":
        filtered_df['Label'] = filtered_df['아파트명'] + " (" + filtered_df['평형_display'] + ")"
        fig = px.line(filtered_df, x='Day', y='정렬용가격', color='Label', markers=True,
                      title='일별 매물 가격 변화 (최저가 기준)',
                      labels={'정렬용가격': '가격 (만원)', 'Day': '날짜'})
    else:
        # Use '평형_display' and '거래구분' for Label
        filtered_df['Label'] = filtered_df['아파트명'] + " (" + filtered_df['평형_display'] + " - " + filtered_df['거래구분'] + ")"
        
        fig = px.scatter(filtered_df, x='Date', y='정렬용가격', color='Label', 
                         size='정렬용가격', hover_data=['가격', '층', '거래구분'] if '거래구분' in filtered_df.columns else ['가격', '층'],
                         title='최근 3년 실거래가 체결 이력',
                         labels={'정렬용가격': '거래가 (만원)', 'Date': '계약일'})
        fig.update_traces(marker=dict(opacity=0.6))
    
    st.plotly_chart(fig, use_container_width=True, key="main_chart")

    # --- Data Table ---
    st.subheader("📋 상세 데이터")
    display_cols = ['Date', '아파트명', '가격', '층', '평형_display']
    if cat_col and cat_col in filtered_df.columns:
        display_cols.append(cat_col)
    
    available_cols = [c for c in display_cols if c in filtered_df.columns]
    st.dataframe(filtered_df[available_cols].sort_values(by='Date', ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()
