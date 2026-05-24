from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from pystac_client import Client

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"


def choose_asset(item):
    for key in ["visual", "rendered_preview", "thumbnail", "preview"]:
        asset = item.assets.get(key)
        if asset and asset.href:
            return key, asset.href
    return None, None


def safe_name(item_id: str, dt: str, ext: str):
    date_part = dt[:10]
    return f"{date_part}_{item_id}.{ext}"


def download_file(url: str, target_path: Path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def search_and_download_sentinel2(
    bbox: list[float],
    start_date: str,
    end_date: str,
    cloud_cover_lte: int,
    max_items: int,
    download_dir: Path,
):
    catalog = Client.open(STAC_URL)
    search = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        query={"eo:cloud_cover": {"lte": cloud_cover_lte}},
        limit=max_items,
    )

    results = []
    for item in search.items():
        asset_key, asset_url = choose_asset(item)
        if not asset_url:
            continue

        parsed = urlparse(asset_url)
        suffix = Path(parsed.path).suffix.lower().replace(".", "") or "jpg"
        dt = item.datetime.isoformat() if item.datetime else datetime.utcnow().isoformat()
        file_name = safe_name(item.id.replace("/", "_"), dt, suffix)
        local_path = download_dir / file_name

        if not local_path.exists():
            download_file(asset_url, local_path)

        results.append(
            {
                "id": item.id,
                "date": dt[:10],
                "cloud_cover": item.properties.get("eo:cloud_cover"),
                "asset_key": asset_key,
                "asset_url": asset_url,
                "path": str(local_path),
                "preview_url": asset_url,
            }
        )

    results.sort(key=lambda x: x["date"])
    return results