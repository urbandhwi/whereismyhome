import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static # Streamlit에 Folium 맵을 표시하기 위한 라이브러리
import urllib.parse # URL 인코딩을 위해 추가
import numpy as np # np.nan을 사용하기 위해 추가

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="연립다세대/오피스텔 임대료 시각화 (Folium)",
    layout="wide"
)

st.title("🏢 연립다세대·오피스텔 조건별 연도별 임대료 시각화 (Folium)")

# --- GitHub raw content URL 설정 ---
github_base_url = 'https://raw.githubusercontent.com/urbandhwi/whereismyhome/main/' # 이곳을 사용자님의 GitHub URL로 변경해주세요!

# --- 2. 데이터 로드 함수 정의 ---
@st.cache_data
def load_data(base_url):
    # GitHub에서 파일을 직접 로드합니다.
    try:
        # 최적화된 Parquet 파일 로드
        encoded_rental_filename = urllib.parse.quote('seoul_rent.parquet')
        rental_data_url = base_url + encoded_rental_filename
        df = pd.read_parquet(rental_data_url)
        st.success(f"전월세 거래 데이터 로드 완료: {rental_data_url}")

        # geometry 컬럼 복원 (parquet 저장 시 제거되었을 수 있으므로)
        if 'geometry' not in df.columns:
            df = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df.longitude, df.latitude),
                crs="EPSG:4326"
            )

        # GeoJSON 파일 로드 (법정동)
        encoded_dong_filename = urllib.parse.quote('seoul_dong.geojson')
        dong_url = base_url + encoded_dong_filename
        geojson_dong = gpd.read_file(dong_url)
        geojson_dong = geojson_dong.to_crs(epsg=4326) # CRS 통일
        st.success(f"법정동 경계 데이터 로드 완료: {dong_url}")

        # GeoJSON 파일 로드 (500m 격자)
        encoded_grid_filename = urllib.parse.quote('seoul_500m_grid.geojson')
        grid_url = base_url + encoded_grid_filename
        geojson_grid = gpd.read_file(grid_url)
        geojson_grid = geojson_grid.to_crs(epsg=4326) # CRS 통일
        st.success(f"500m 격자 데이터 로드 완료: {grid_url}")

        # GeoJSON 파일 로드 (자치구)
        encoded_gu_filename = urllib.parse.quote('seoul_gu.geojson')
        gu_url = base_url + encoded_gu_filename
        geojson_gu = gpd.read_file(gu_url)
        geojson_gu = geojson_gu.to_crs(epsg=4326) # CRS 통일
        st.success(f"자치구 경계 데이터 로드 완료: {gu_url}")

        # GeoJSON 파일 로드 (지하철) - NEW
        encoded_subway_filename = urllib.parse.quote('seoul_subway.geojson')
        subway_url = base_url + encoded_subway_filename
        geojson_subway = gpd.read_file(subway_url)
        geojson_subway = geojson_subway.to_crs(epsg=4326) # CRS 통일
        st.success(f"지하철 경계 데이터 로드 완료: {subway_url}")

        # `seoul_dong.geojson`에는 '법정동코드'가 문자열로 저장되어 있습니다. (Cell zjRgA_OzBjYC 참고)
        # plotly.express의 featureidkey가 `feature.properties.법정동코드`를 사용하려면
        # geojson_dong의 '법정동코드' 컬럼이 있어야 합니다.
        if '법정동코드' not in geojson_dong.columns:
            # `EMD_CD` 컬럼이 있다면 이를 이용해 '법정동코드' 생성
            if 'EMD_CD' in geojson_dong.columns:
                # `df_raw`의 '법정동코드'가 5자리 법정동코드이므로, `EMD_CD`의 마지막 3자리 + '00' 형태로 추출
                geojson_dong['법정동코드'] = geojson_dong['EMD_CD'].astype(str).str[-3:] + '00'
            else:
                st.warning("geojson_dong에 'EMD_CD' 또는 '법정동코드' 컬럼이 없어 법정동 시각화에 문제가 있을 수 있습니다.")

        # Ensure `자치구코드` in `geojson_dong` and `SIG_CD` in `geojson_gu` are string for merging
        if '자치구코드' not in geojson_dong.columns and 'EMD_CD' in geojson_dong.columns:
            geojson_dong['자치구코드'] = geojson_dong['EMD_CD'].astype(str).str[0:5]

        if '자치구코드' in geojson_dong.columns:
            geojson_dong['자치구코드'] = geojson_dong['자치구코드'].astype(str)
        if 'SIG_CD' in geojson_gu.columns:
            geojson_gu['SIG_CD'] = geojson_gu['SIG_CD'].astype(str)

        # 지도 시각화의 고유 ID로 사용할 unique_map_key 생성 (자치구코드 + 법정동코드)
        if '자치구코드' in geojson_dong.columns and '법정동코드' in geojson_dong.columns:
            geojson_dong['unique_map_key'] = geojson_dong['자치구코드'].astype(str) + '_' + geojson_dong['법정동코드'].astype(str)
        else:
            st.warning("geojson_dong에 '자치구코드' 또는 '법정동코드' 컬럼이 없어 unique_map_key를 생성할 수 없습니다.")

        return df, geojson_dong, geojson_grid, geojson_gu, geojson_subway # geojson_subway 추가
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        st.info("GitHub URL 또는 파일 경로를 확인하거나, 파일이 public repository에 있는지 확인 바랍니다.")
        return None, None, None, None, None # None for geojson_subway 추가

try:
    df_raw, geojson_dong, geojson_grid, geojson_gu, geojson_subway = load_data(github_base_url)
except Exception as e:
    st.error(f
