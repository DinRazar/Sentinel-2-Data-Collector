from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from services.downloaders import search_and_download_sentinel2
from services.gif_maker import build_gif

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "sentinel2"
OUTPUT_DIR = BASE_DIR / "output"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Geo Timelapse API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/raw", StaticFiles(directory=str(DATA_DIR / "raw")), name="raw")


class CollectRequest(BaseModel):
    start_date: str
    end_date: str
    bbox: list[float] = Field(
        description="[min_lon, min_lat, max_lon, max_lat]",
        min_length=4,
        max_length=4,
    )
    cloud_cover_lte: int = Field(default=20, ge=0, le=100)
    max_items: int = Field(default=12, ge=1, le=50)


class GifRequest(CollectRequest):
    duration_ms: int = 500
    resize_width: int = 512


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/collect-sentinel2")
def collect_sentinel2(payload: CollectRequest):
    items = search_and_download_sentinel2(
        bbox=payload.bbox,
        start_date=payload.start_date,
        end_date=payload.end_date,
        cloud_cover_lte=payload.cloud_cover_lte,
        max_items=payload.max_items,
        download_dir=RAW_DIR,
    )

    if not items:
        raise HTTPException(status_code=404, detail="Сцены Sentinel-2 не найдены")

    return {
        "message": "Сцены скачаны",
        "count": len(items),
        "items": items,
    }


@app.post("/collect-and-generate-gif")
def collect_and_generate_gif(payload: GifRequest):
    items = search_and_download_sentinel2(
        bbox=payload.bbox,
        start_date=payload.start_date,
        end_date=payload.end_date,
        cloud_cover_lte=payload.cloud_cover_lte,
        max_items=payload.max_items,
        download_dir=RAW_DIR,
    )

    if not items:
        raise HTTPException(status_code=404, detail="Сцены Sentinel-2 не найдены")

    output_name = f"sentinel2_{payload.start_date}_{payload.end_date}_{uuid4().hex[:8]}.gif"
    output_path = OUTPUT_DIR / output_name

    build_gif(
        frame_items=items,
        bbox=payload.bbox,
        output_path=output_path,
        duration_ms=payload.duration_ms,
        resize_width=payload.resize_width,
    )

    return {
        "message": "Данные скачаны и GIF создан",
        "frames_used": len(items),
        "file_name": output_name,
        "file_url": f"/output/{output_name}",
        "items": items,
    }


@app.get("/download/{file_name}")
def download_file(file_name: str):
    file_path = OUTPUT_DIR / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(path=file_path, filename=file_name, media_type="image/gif")