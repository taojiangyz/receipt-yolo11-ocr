from pathlib import Path
import argparse
import json

from paddleocr import PaddleOCR


def run_ocr_on_image(ocr, image_path: Path):
    if not image_path.exists():
        return ""

    result = ocr.ocr(str(image_path))
    texts = []

    if not result:
        return ""

    # PaddleOCR 3.x format: result contains dict-like pages with rec_texts
    for page in result:
        if isinstance(page, dict):
            rec_texts = page.get("rec_texts", [])
            texts.extend([t for t in rec_texts if t])
            continue

        # Fallback for older PaddleOCR format
        if isinstance(page, list):
            for line in page:
                try:
                    text = line[1][0]
                    texts.append(text)
                except Exception:
                    continue

    return "\n".join(texts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop_dir", required=True)
    args = parser.parse_args()

    crop_dir = Path(args.crop_dir)
    image_id = crop_dir.name

    ocr = PaddleOCR(
        lang="japan",
        use_textline_orientation=True
    )

    fields = {
        "store_name": crop_dir / "store_name.jpg",
        "date": crop_dir / "date.jpg",
        "total_amount": crop_dir / "total_amount.jpg",
        "items_area": crop_dir / "items_area.jpg",
    }

    output = {
        "image_id": image_id,
        "ocr_engine": "PaddleOCR",
    }

    for field, path in fields.items():
        output[f"{field}_raw"] = run_ocr_on_image(ocr, path)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
