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
    st.error(f"데이터 파일 로드 중 오류가 발생했습니다: {e}")
    st.stop()

# --- 3. 사이드바 - 조건 선택 필터 ---
st.sidebar.header("🔍 검색 조건 설정")

house_type_selection = st.sidebar.radio("주택 유형", ["전체", "연립다세대", "오피스텔"]) # '전체' 옵션 추가
spatial_unit = st.sidebar.radio("시각화 단위", ["법정동별", "격자별"])
selected_year = st.sidebar.selectbox("연도", [2023, 2024, 2025])

deposit_options = {
    "1000만원 미만": (0, 1000, 500),
    "1000~3000만원 미만": (1000, 3000, 1000),
    "3000~5000만원 미만": (3000, 5000, 3000),
    "5000만원~1억원": (5000, 10000, 5000)
}
selected_deposit_label = st.sidebar.selectbox("보증금 구간", list(deposit_options.keys()))
dep_min, dep_max, base_deposit = deposit_options[selected_deposit_label]

area_options = {
    "15 미만": (0, 15),
    "15~25": (15, 25),
    "25 이상": (25, 9999)
}
selected_area_label = st.sidebar.selectbox("면적대 (㎡)", list(area_options.keys()))
area_min, area_max = area_options[selected_area_label]

selected_age = st.sidebar.selectbox("건물 연식", ["전체", "신축 (2020년 이후)", "구축 (2000년 이전)"])
selected_floor = st.sidebar.selectbox("층수", ["전체", "저층 (1층 이하)"])

submit_button = st.sidebar.button("시각화 실행", type="primary")

# --- 4. 데이터 필터링 및 환산 로직 ---
if submit_button:
    df = df_raw.copy()

    # 주택 유형 필터
    if house_type_selection != "전체":
        df = df[df["건물용도"] == house_type_selection]

    # 연도 필터 (컬럼명 '접수년도' 사용)
    if "접수년도" in df.columns:
        df = df[df["접수년도"] == selected_year]

    # 보증금 필터 (컬럼명 '보증금(만원)' 사용)
    if "보증금(만원)" in df.columns:
        df = df[(df["보증금(만원)"] >= dep_min) & (df["보증금(만원)"] < dep_max)]

    # 면적 필터 (컬럼명 '임대면적' 사용)
    if "임대면적" in df.columns:
        df = df[(df["임대면적"] >= area_min) & (df["임대면적"] < area_max)]

    # 건물 연식 필터 (컬럼명 '건축년도' 사용)
    if "건축년도" in df.columns:
        if selected_age == "신축 (2020년 이후)":
            df = df[df["건축년도"] >= 2020]
        elif selected_age == "구축 (2000년 이전)":
            df = df[df["건축년도"] < 2000]

    # 층수 필터 (컬럼명 '층' 사용)
    if "층" in df.columns:
        if selected_floor == "저층 (1층 이하)":
            df = df[df["층"] <= 1]

    # 환산 임대료 계산 (컬럼명 '보증금(만원)', '임대료(만원)' 사용)
    if not df.empty and "보증금(만원)" in df.columns and "임대료(만원)" in df.columns:
        df["adjusted_rent"] = df["임대료(만원)"] - (df["보증금(만원)"] - base_deposit) * 0.005

        # 법정동 또는 격자 기준으로 집계
        if spatial_unit == "법정동별":
            df['unique_map_key'] = df['자치구코드'].astype(str) + '_' + df['법정동코드'].astype(str)
            group_col = "unique_map_key"
            target_geojson = geojson_dong
        else: # 격자별
            group_col = "grid_id"
            target_geojson = geojson_grid

        # `group_col`이 `df`에 있는지 확인하고 타입 통일
        if group_col in df.columns:
            df[group_col] = df[group_col].astype(str)
            # `target_geojson`의 해당 ID 컬럼도 문자열로 통일
            if group_col in target_geojson.columns:
                target_geojson[group_col] = target_geojson[group_col].astype(str)

        # Aggregate statistics
        aggregated_df = df.groupby(group_col)["adjusted_rent"].agg(
            count_거래건수='count',
            avg_환산임대료='mean',
            min_환산임대료='min',
            max_환산임대료='max',
            median_환산임대료='median'
        ).reset_index()

        # Merge with GeoJSON for plotting
        plot_gdf = target_geojson.merge(
            aggregated_df,
            left_on=group_col,
            right_on=group_col,
            how='left'
        )
        plot_gdf['avg_환산임대료'] = plot_gdf['avg_환산임대료'].fillna(np.nan) # 데이터 없는 지역은 NaN

        if spatial_unit == "법정동별":
            # NEW: Merge with geojson_gu to get SIG_KOR_NM (자치구명)
            plot_gdf = plot_gdf.merge(
                geojson_gu[['SIG_CD', 'SIG_KOR_NM']],
                left_on='자치구코드', # geojson_dong's district code
                right_on='SIG_CD', # geojson_gu's district code
                how='left'
            )
            # Drop the redundant SIG_CD column from the merge
            plot_gdf.drop(columns=['SIG_CD'], inplace=True, errors='ignore')

            hover_fields = ['EMD_NM', 'count_거래건수', 'min_환산임대료', 'max_환산임대료', 'median_환산임대료', 'avg_환산임대료']
            hover_aliases = ['법정동명:', '거래건수:', '최저 환산임대료(만원):', '최고 환산임대료(만원):', '중앙 환산임대료(만원):', '평균 환산임대료(만원):']
        else: # 격자별
            hover_fields = ['grid_id', 'count_거래건수', 'min_환산임대료', 'max_환산임대료', 'median_환산임대료', 'avg_환산임대료']
            hover_aliases = ['격자 ID:', '거래건수:', '최저 환산임대료(만원):', '최고 환산임대료(만원):', '중앙 환산임대료(만원):', '평균 환산임대료(만원):']

        # 5. 지도 시각화 (Folium)
        st.subheader(f"📊 {selected_year}년 {house_type_selection} {spatial_unit} 평균 환산 임대료")

        # 서울 중심 좌표
        seoul_center = [37.5665, 126.9780]
        m = folium.Map(location=seoul_center, zoom_start=11, tiles="cartodbpositron") # Plotly와 유사한 스타일의 타일 사용

        # Folium Choropleth 레이어 추가
        # avg_환산임대료가 NaN이 아닌 데이터만 시각화
        folium.Choropleth(
            geo_data=plot_gdf.dropna(subset=['avg_환산임대료']),
            name=f'{spatial_unit} 평균 환산월세',
            data=plot_gdf.dropna(subset=['avg_환산임대료']),
            columns=[group_col, 'avg_환산임대료'], # Key column and value column
            key_on=f'feature.properties.{group_col}', # Column in geo_data to match with data columns key
            fill_color='RdBu_r', # Color scheme: Blue (low) to Red (high) - 'r' reverses the default RdBu
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='평균 환산 임대료 (만원)',
            highlight=True,
            # 툴팁 설정
            tooltip=folium.features.GeoJsonTooltip(
                fields=hover_fields,
                aliases=hover_aliases,
                localize=True,
                sticky=False
            )
        ).add_to(m)

        # 자치구 경계 오버레이 추가
        folium.GeoJson(
            geojson_gu,
            name='자치구 경계',
            style_function=lambda x: {
                'color': 'black',
                'weight': 1.5,
                'fillOpacity': 0
            },
            tooltip=folium.features.GeoJsonTooltip(
                fields=['SIG_KOR_NM'],
                aliases=['자치구명:'],
                localize=True,
                sticky=True
            )
        ).add_to(m)

        # 자치구 이름 텍스트 마커 추가 (흐리게)
        for idx, row in geojson_gu.iterrows():
            centroid = row.geometry.centroid
            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=folium.DivIcon(
                    icon_size=(150, 36),
                    icon_anchor=(75, 18),
                    html=f"<div style=\"font-size: 10pt; color: gray; opacity: 0.7; text-align: center; font-weight: bold;\">{row['SIG_KOR_NM']}</div>"
                )
            ).add_to(m)

        # --- 지하철 노선 보기 설정 ---
        st.subheader("🚉 지하철 노선 보기")
        if geojson_subway is not None and not geojson_subway.empty:
            all_hoseon = geojson_subway['hoseon'].unique().tolist()
            selected_hoseon_list = st.multiselect(
                "표시할 지하철 노선을 선택하세요:",
                options=all_hoseon,
                default=[]
            )

            # 지하철 노선 색상 매핑
            subway_line_colors = {
                '1호선': '#003DA5', '2호선': '#009D3E', '3호선': '#EF7C1C', '4호선': '#00A5DE',
                '5호선': '#996CAC', '6호선': '#CD7C2F', '7호선': '#747F00', '8호선': '#EA545D',
                '9호선': '#BB8E00', '수인분당선': '#FABE00', '신분당선': '#D4003B', '경의중앙선': '#77C4A3',
                '경춘선': '#0C9482', '공항철도': '#0070C0', '우이신설선': '#B0CE33', '서해선': '#8FD6D5',
                '김포골드라인': '#A17800', '에버라인': '#55B098', '의정부경전철': '#B0CE33', '인천1호선': '#7C93C7',
                '인천2호선': '#F2B134', '신림선': '#6C7EBF'
            }

            if selected_hoseon_list:
                st.write(f"선택된 노선: {', '.join(selected_hoseon_list)}")
                # 선택된 노선에 해당하는 지하철 역 필터링
                filtered_subway_stations = geojson_subway[geojson_subway['hoseon'].isin(selected_hoseon_list)].copy()

                # 지하철 역을 위한 FeatureGroup 생성
                subway_group = folium.FeatureGroup(name='선택된 지하철 역', show=True)

                for idx, row in filtered_subway_stations.iterrows():
                    station_name = row['SWST_NM']
                    hoseon_name = row['hoseon']
                    line_color = subway_line_colors.get(hoseon_name, '#000000') # 기본값은 검은색

                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=4, # 마커 크기 조정
                        color=line_color,
                        fill=True,
                        fill_color=line_color,
                        fill_opacity=0.9,
                        tooltip=f"<b>{station_name}</b><br>{hoseon_name}"
                    ).add_to(subway_group)
                subway_group.add_to(m)
        else:
            st.warning("지하철 데이터가 로드되지 않았거나 비어 있습니다.")

        folium.LayerControl().add_to(m)

        # Streamlit에 Folium 맵 표시
        folium_static(m, width=900, height=600)

        st.write(f"총 거래 건수: **{len(df):,}** 건")

        # Display the aggregated data in a dataframe as requested by the user
        if spatial_unit == "법정동별":
            display_cols = ['SIG_KOR_NM', 'EMD_NM', 'count_거래건수', 'avg_환산임대료', 'min_환산임대료', 'max_환산임대료', 'median_환산임대료']
            st.dataframe(plot_gdf[display_cols].dropna(subset=['avg_환산임대료']).rename(columns={
                'SIG_KOR_NM': '자치구',
                'EMD_NM': '법정동',
                'count_거래건수': '거래건수',
                'avg_환산임대료': '평균 환산 임대료 (만원)',
                'min_환산임대료': '최소 환산 임대료 (만원)',
                'max_환산임대료': '최고 환산 임대료 (만원)',
                'median_환산임대료': '중앙 환산 임대료 (만원)'
            }))
        else: # 격자별
            st.dataframe(aggregated_df.rename(columns={
                'count_거래건수': '거래건수',
                'avg_환산임대료': '평균 환산 임대료 (만원)',
                'min_환산임대료': '최소 환산 임대료 (만원)',
                'max_환산임대료': '최고 환산 임대료 (만원)',
                'median_환산임대료': '중앙 환산 임대료 (만원)'
            }))

    else:
        st.warning("선택한 조건에 해당하는 데이터가 없거나, 필요한 컬럼이 누락되었습니다.")
else:
    st.info("왼쪽 사이드바에서 필터 조건을 선택한 후 '시각화 실행' 버튼을 눌러주세요.")
