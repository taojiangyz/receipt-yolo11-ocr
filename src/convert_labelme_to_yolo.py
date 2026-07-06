from pathlib import Path
import json
import shutil
from PIL import Image

SOURCE_DIR = Path("data/label_test_20")
OUT_IMAGE_DIR = Path("data/yolo_test/images")
OUT_LABEL_DIR = Path("data/yolo_test/labels")

CLASS_MAP = {
    "store_name": 0,
    "date": 1,
    "total_amount": 2,
    "items_area": 3,
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def labelme_rectangle_to_yolo(points, img_w, img_h):
    """
    Convert Labelme rectangle points to YOLO format.

    Labelme rectangle points:
        [[x1, y1], [x2, y2]]

    YOLO format:
        x_center y_center width height
    normalized to 0-1.
    """
    (x1, y1), (x2, y2) = points

    x_min = min(x1, x2)
    x_max = max(x1, x2)
    y_min = min(y1, y2)
    y_max = max(y1, y2)

    x_center = ((x_min + x_max) / 2) / img_w
    y_center = ((y_min + y_max) / 2) / img_h
    width = (x_max - x_min) / img_w
    height = (y_max - y_min) / img_h

    return x_center, y_center, width, height


def main():
    OUT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_LABEL_DIR.mkdir(parents=True, exist_ok=True)

    json_files = sorted(SOURCE_DIR.glob("*.json"))

    print(f"Found JSON files: {len(json_files)}")

    converted = 0
    errors = []

    for json_path in json_files:
        data = json.loads(json_path.read_text(encoding="utf-8"))

        image_name = data.get("imagePath")
        if not image_name:
            image_name = json_path.with_suffix(".jpeg").name

        image_path = SOURCE_DIR / image_name

        if not image_path.exists():
            # Try to find image by same stem
            candidates = [
                p for p in SOURCE_DIR.iterdir()
                if p.is_file()
                and p.stem == json_path.stem
                and p.suffix.lower() in IMAGE_EXTS
            ]
            if candidates:
                image_path = candidates[0]
            else:
                errors.append(f"Image not found for {json_path.name}")
                continue

        with Image.open(image_path) as img:
            img_w, img_h = img.size

        yolo_lines = []

        for shape in data.get("shapes", []):
            label = shape.get("label")
            shape_type = shape.get("shape_type")
            points = shape.get("points")

            if label not in CLASS_MAP:
                errors.append(f"{json_path.name}: unknown label {label}")
                continue

            if shape_type != "rectangle":
                errors.append(f"{json_path.name}: non-rectangle shape {shape_type}")
                continue

            if not points or len(points) != 2:
                errors.append(f"{json_path.name}: invalid rectangle points")
                continue

            class_id = CLASS_MAP[label]
            x_center, y_center, width, height = labelme_rectangle_to_yolo(
                points, img_w, img_h
            )

            values = [x_center, y_center, width, height]

            if not all(0 <= v <= 1 for v in values):
                errors.append(f"{json_path.name}: YOLO values out of range {values}")
                continue

            yolo_lines.append(
                f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
            )

        if len(yolo_lines) != 4:
            errors.append(f"{json_path.name}: expected 4 boxes, got {len(yolo_lines)}")

        label_out_path = OUT_LABEL_DIR / f"{json_path.stem}.txt"
        label_out_path.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")

        image_out_path = OUT_IMAGE_DIR / image_path.name
        shutil.copy2(image_path, image_out_path)

        converted += 1
        print(f"Converted: {json_path.name} -> {label_out_path.name}")

    print("\nDone.")
    print(f"Converted files: {converted}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nError details:")
        for e in errors:
            print("-", e)


if __name__ == "__main__":
    main()
