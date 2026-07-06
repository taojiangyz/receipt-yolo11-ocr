from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

IMAGE_DIR = Path("data/yolo_test/images")
LABEL_DIR = Path("data/yolo_test/labels")
OUT_DIR = Path("outputs/yolo_test_visualized")

CLASS_NAMES = {
    0: "store_name",
    1: "date",
    2: "total_amount",
    3: "items_area",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def find_image(stem: str):
    for ext in IMAGE_EXTS:
        p = IMAGE_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def yolo_to_xyxy(xc, yc, w, h, img_w, img_h):
    x1 = (xc - w / 2) * img_w
    y1 = (yc - h / 2) * img_h
    x2 = (xc + w / 2) * img_w
    y2 = (yc + h / 2) * img_h
    return int(x1), int(y1), int(x2), int(y2)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for label_path in sorted(LABEL_DIR.glob("*.txt")):
        image_path = find_image(label_path.stem)

        if image_path is None:
            print(f"Image not found for {label_path.name}")
            continue

        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        img_w, img_h = img.size

        lines = label_path.read_text().strip().splitlines()

        for line in lines:
            cls_id_str, xc_str, yc_str, w_str, h_str = line.split()
            cls_id = int(cls_id_str)
            xc, yc, w, h = map(float, [xc_str, yc_str, w_str, h_str])

            x1, y1, x2, y2 = yolo_to_xyxy(xc, yc, w, h, img_w, img_h)
            label = CLASS_NAMES.get(cls_id, str(cls_id))

            draw.rectangle([x1, y1, x2, y2], outline="red", width=8)
            draw.text((x1, max(0, y1 - 35)), label, fill="red")

        out_path = OUT_DIR / f"{label_path.stem}_vis.jpg"
        img.save(out_path, quality=95)
        print(f"Saved {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
