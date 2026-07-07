from pathlib import Path
import argparse
import json
import re
import cv2
import easyocr


def preprocess_image(image, scale=3, padding=30):
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    image = cv2.copyMakeBorder(
        image,
        top=padding,
        bottom=padding,
        left=padding,
        right=padding,
        borderType=cv2.BORDER_CONSTANT,
        value=[255, 255, 255]
    )

    return image


def read_text(reader, image_path):
    image_path = Path(image_path)

    if not image_path.exists():
        return ""

    image = cv2.imread(str(image_path))

    if image is None:
        return ""

    image = preprocess_image(image, scale=3, padding=30)

    results = reader.readtext(image, detail=0, paragraph=True)
    return "\n".join(results).strip()


def clean_total_amount(text):
    """
    Extract a likely total amount from OCR text.
    This is a simple first-version rule.
    """
    if not text:
        return ""

    candidates = re.findall(r"[¥￥]?\s?[0-9,]{2,6}", text)

    if not candidates:
        return ""

    cleaned = []
    for c in candidates:
        num = re.sub(r"[^0-9]", "", c)
        if num:
            cleaned.append((int(num), c.strip()))

    if not cleaned:
        return ""

    cleaned.sort(reverse=True)
    return cleaned[0][1]


def normalize_store_name(text):
    """
    Simple first-version store name normalization.
    """
    if not text:
        return ""

    t = text.lower()

    if "family" in t or "fam" in t:
        return "FamilyMart"

    if "lawson" in t:
        return "LAWSON"

    if "seven" in t or "7" in t:
        return "7-Eleven"

    return text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop_dir", required=True, help="Directory containing cropped receipt regions")
    parser.add_argument("--output", default="outputs/json", help="Output directory for JSON result")
    args = parser.parse_args()

    crop_dir = Path(args.crop_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not crop_dir.exists():
        raise FileNotFoundError(f"Crop directory not found: {crop_dir}")

    reader = easyocr.Reader(["ja", "en"], gpu=False)

    store_name_text = read_text(reader, crop_dir / "store_name.jpg")
    date_text = read_text(reader, crop_dir / "date.jpg")
    total_amount_text = read_text(reader, crop_dir / "total_amount.jpg")
    items_text = read_text(reader, crop_dir / "items_area.jpg")

    result = {
        "image_id": crop_dir.name,
        "store_name_raw": store_name_text,
        "store_name_candidate": normalize_store_name(store_name_text),
        "date_raw": date_text,
        "total_amount_raw": total_amount_text,
        "total_amount_candidate": clean_total_amount(total_amount_text),
        "items_text": items_text
    }

    out_path = output_dir / f"{crop_dir.name}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nSaved JSON: {out_path}")


if __name__ == "__main__":
    main()
