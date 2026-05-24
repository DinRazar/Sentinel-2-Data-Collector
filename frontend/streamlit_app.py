from datetime import date
from urllib.parse import urljoin

import folium
import requests
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Sentinel-2 Collector", layout="wide")
st.title("Sentinel-2 Data Collector")
st.caption("Выбери область и даты, приложение само найдёт и скачает сцены, а затем может собрать GIF")


def build_map():
    fmap = folium.Map(location=[55.75, 37.62], zoom_start=4, tiles="CartoDB positron")
    Draw(
        draw_options={
            "polyline": False,
            "polygon": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "rectangle": True,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(fmap)
    return fmap


def extract_bbox(map_result):
    drawing = map_result.get("last_active_drawing") if map_result else None
    if not drawing:
        return None

    geometry = drawing.get("geometry", {})
    if geometry.get("type") != "Polygon":
        return None

    coords = geometry.get("coordinates", [])
    if not coords or not coords[0]:
        return None

    ring = coords[0]
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return [min(lons), min(lats), max(lons), max(lats)]


with st.sidebar:
    st.header("Параметры")
    start_date = st.date_input("Дата начала", value=date(2025, 1, 1))
    end_date = st.date_input("Дата конца", value=date(2025, 1, 31))
    cloud_cover_lte = st.slider("Облачность <=", 0, 100, 20, 5)
    max_items = st.slider("Максимум сцен", 1, 20, 8, 1)
    duration_ms = st.slider("Задержка между кадрами, мс", 100, 1500, 500, 100)
    resize_width = st.slider("Ширина GIF", 256, 1024, 512, 64)

col1, col2 = st.columns([1.15, 0.85])

with col1:
    st.subheader("Выбор области")
    st.write("Нарисуй прямоугольник на карте.")
    map_result = st_folium(build_map(), height=540, width=None, use_container_width=True, key="map")

with col2:
    st.subheader("Управление")
    bbox = extract_bbox(map_result)

    if bbox:
        st.success("Область выбрана")
        st.json({
            "min_lon": round(bbox[0], 6),
            "min_lat": round(bbox[1], 6),
            "max_lon": round(bbox[2], 6),
            "max_lat": round(bbox[3], 6),
        })
    else:
        st.info("Пока не выбрана область")

    payload = None
    if bbox and start_date <= end_date:
        payload = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "bbox": bbox,
            "cloud_cover_lte": cloud_cover_lte,
            "max_items": max_items,
            "duration_ms": duration_ms,
            "resize_width": resize_width,
        }

    if st.button("Скачать сцены", use_container_width=True):
        if not bbox:
            st.error("Сначала выбери область")
        elif start_date > end_date:
            st.error("Некорректный диапазон дат")
        else:
            try:
                response = requests.post(f"{API_BASE}/collect-sentinel2", json=payload, timeout=180)
                if response.status_code != 200:
                    st.error(response.json().get("detail", "Ошибка backend"))
                else:
                    result = response.json()
                    st.success(f"Скачано сцен: {result['count']}")
                    for item in result["items"]:
                        st.markdown(f"- **{item['date']}** | cloud: {item['cloud_cover']} | `{item['id']}`")
            except requests.RequestException as exc:
                st.error(f"Ошибка подключения: {exc}")

    if st.button("Скачать сцены и собрать GIF", type="primary", use_container_width=True):
        if not bbox:
            st.error("Сначала выбери область")
        elif start_date > end_date:
            st.error("Некорректный диапазон дат")
        else:
            try:
                response = requests.post(f"{API_BASE}/collect-and-generate-gif", json=payload, timeout=300)
                if response.status_code != 200:
                    st.error(response.json().get("detail", "Ошибка backend"))
                else:
                    result = response.json()
                    file_url = urljoin(API_BASE, result["file_url"])
                    download_url = f"{API_BASE}/download/{result['file_name']}"

                    st.success(f"Готово. Скачано сцен: {result['frames_used']}")
                    st.image(file_url, caption=result["file_name"])

                    file_response = requests.get(download_url, timeout=180)
                    st.download_button(
                        label="Скачать GIF",
                        data=file_response.content,
                        file_name=result["file_name"],
                        mime="image/gif",
                        use_container_width=True,
                    )

                    st.subheader("Скачанные сцены")
                    for item in result["items"]:
                        st.markdown(f"- **{item['date']}** | cloud: {item['cloud_cover']} | `{item['id']}`")
                        st.image(item["preview_url"], caption=item["id"])
            except requests.RequestException as exc:
                st.error(f"Ошибка подключения: {exc}")