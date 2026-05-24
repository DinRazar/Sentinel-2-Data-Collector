# Geo Timelapse App

Простое учебное приложение для **сбора спутниковых данных** и сборки GIF-анимации по выбранной области и диапазону дат.

Проект состоит из двух частей:
- **FastAPI backend** — ищет сцены, скачивает preview-изображения и собирает GIF.
- **Streamlit frontend** — показывает карту, позволяет выбрать область, даты и скачать результат.

Источник данных в текущем MVP — поиск сцен Sentinel-2 через STAC API Earth Search, а для GIF используются preview/visual изображения вместо тяжёлых GeoTIFF. Это упрощает запуск и снижает вероятность ошибок при обработке больших TIFF-файлов.

## Что умеет

- Выбор прямоугольной области на карте через Streamlit + Folium.
- Выбор диапазона дат и фильтра по облачности.
- Поиск сцен Sentinel-2 через STAC API.
- Скачивание preview-кадров локально.
- Генерация GIF-анимации по найденным кадрам через Pillow.

## Структура проекта

```text
geo-timelapse-app/
├── backend/
│   ├── app.py
│   ├── services/
│   │   ├── downloaders.py
│   │   └── gif_maker.py
│   ├── data/
│   │   └── raw/
│   │       └── sentinel2/
│   └── output/
├── frontend/
│   └── streamlit_app.py
└── requirements.txt
```

## Установка

Создать виртуальное окружение:

```bash
python -m venv .venv
source .venv/bin/activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Если каких-то библиотек не хватает, проекту нужны как минимум `fastapi`, `uvicorn`, `streamlit`, `folium`, `streamlit-folium`, `pillow`, `requests`, `pystac-client`.

## Запуск backend

Находясь в папке `backend`, запустить:

```bash
uvicorn app:app --reload
```

FastAPI поднимет локальный сервер на `http://127.0.0.1:8000`, а Swagger UI будет доступен по `/docs`.

Проверка, что backend жив:

```bash
curl http://127.0.0.1:8000/health
```

## Запуск frontend

Во втором терминале:

```bash
cd frontend
streamlit run streamlit_app.py
```
<img width="1440" height="654" alt="Снимок экрана 2026-05-24 в 3 22 43 PM" src="https://github.com/user-attachments/assets/1cabd17e-e9e7-42fc-88c1-b22afadfbfa8" />

## Как использовать

1. Открыть Streamlit-приложение в браузере.
2. Нарисовать прямоугольник на карте.
3. Выбрать диапазон дат.
4. Задать порог облачности.
5. Нажать `Скачать сцены` или `Скачать сцены и собрать GIF`.
6. Дождаться завершения обработки.

Для первых тестов лучше использовать не слишком маленькую область, летний период и облачность `<= 60`, потому что жёсткие фильтры часто оставляют пустую выборку.

## Где лежат результаты

Скачанные preview-кадры сохраняются в:

```text
backend/data/raw/sentinel2/
```

Готовые GIF-файлы сохраняются в:

```text
backend/output/
```

FastAPI также раздаёт их через статические маршруты и endpoint скачивания.

## Ограничения MVP

- Используются preview/visual изображения, а не исходные многоканальные GeoTIFF.
- Реальная геопривязка и точная обрезка пока не реализованы.
- Пока поддерживается только Sentinel-2.
