from pathlib import Path

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None


def geo_crop_box(image_width: int, image_height: int, bbox: list[float]):
    min_lon, min_lat, max_lon, max_lat = bbox

    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))
    min_lat = max(-90.0, min(90.0, min_lat))
    max_lat = max(-90.0, min(90.0, max_lat))

    if min_lon >= max_lon or min_lat >= max_lat:
        return None

    left = int(((min_lon + 180.0) / 360.0) * image_width)
    right = int(((max_lon + 180.0) / 360.0) * image_width)
    top = int(((90.0 - max_lat) / 180.0) * image_height)
    bottom = int(((90.0 - min_lat) / 180.0) * image_height)

    left = max(0, min(image_width - 1, left))
    right = max(left + 1, min(image_width, right))
    top = max(0, min(image_height - 1, top))
    bottom = max(top + 1, min(image_height, bottom))

    return (left, top, right, bottom)


def add_caption(image: Image.Image, caption: str):
    canvas = image.copy()
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((10, 10, 260, 42), radius=8, fill=(0, 0, 0))
    draw.text((20, 18), caption, fill=(255, 255, 255))
    return canvas


def resize_keep_ratio(img: Image.Image, target_width: int):
    ratio = target_width / img.width
    target_height = int(img.height * ratio)
    return img.resize((target_width, target_height))


def safe_open_image(path: str):
    try:
        img = Image.open(path)
        img.load()
        return img.convert("RGB")
    except Exception as e:
        print(f"SKIP broken image: {path} | error: {e}")
        return None


def build_gif(
    frame_items: list[dict],
    bbox: list[float],
    output_path: Path,
    duration_ms: int = 500,
    resize_width: int = 512,
):
    prepared = []

    for item in frame_items:
        img = safe_open_image(item["path"])
        if img is None:
            continue

        crop_box = geo_crop_box(img.width, img.height, bbox)
        if crop_box:
            img = img.crop(crop_box)

        img.thumbnail((resize_width, resize_width * 4))
        img = resize_keep_ratio(img, resize_width)
        img = add_caption(img, item["date"])
        prepared.append(img)

    if not prepared:
        raise ValueError("Нет валидных кадров для GIF")

    first, *rest = prepared
    first.save(
        output_path,
        save_all=True,
        append_images=rest,
        duration=duration_ms,
        loop=0,
        optimize=False,
    )