from pathlib import Path
import argparse
import json
import re

from paddleocr import PaddleOCR


def run_ocr_on_image(ocr, image_path: Path) -> str:
    if not image_path.exists():
        return ""

    result = ocr.ocr(str(image_path))
    texts = []

    if not result:
        return ""

    # PaddleOCR 3.x format
    for page in result:
        if isinstance(page, dict):
            rec_texts = page.get("rec_texts", [])
            texts.extend([t for t in rec_texts if t])
            continue

        # Fallback for old PaddleOCR format
        if isinstance(page, list):
            for line in page:
                try:
                    text = line[1][0]
                    texts.append(text)
                except Exception:
                    continue

    return "\n".join(texts)


def normalize_store_name(text: str) -> str:
    if not text:
        return ""

    raw = text.replace(" ", "").replace("\n", "")
    lower = raw.lower()

    if "familymart" in lower or "family" in lower:
        return "FamilyMart"

    if "lawson" in lower or "ローソン" in raw:
        return "LAWSON"

    if (
        "セブン" in raw
        or "イレブン" in raw
        or "7-eleven" in lower
        or "seven" in lower
    ):
        return "7-Eleven"

    if (
        "mybasket" in lower
        or "mybasket" in lower
        or "まいばす" in raw
        or "まいはす" in raw
        or "まいほす" in raw
    ):
        return "MyBasket"

    return text


def extract_amount(text: str) -> str:
    if not text:
        return ""

    # Normalize symbols and spaces
    t = text.replace("￥", "¥")
    t = t.replace(" ", "").replace("\n", "")

    # Strong pattern: ¥1,020 / ¥610 / ¥181
    yen_matches = re.findall(r"¥\d{1,3}(?:,\d{3})*|¥\d{3,6}", t)
    if yen_matches:
        # Prefer the longest candidate
        cand = sorted(yen_matches, key=len, reverse=True)[0]
        return cand.replace("¥", "").replace(",", "")

    # Weak fallback: plain 3-6 digit number
    nums = re.findall(r"\d{3,6}", t)
    if nums:
        return sorted(nums, key=len, reverse=True)[0].replace(",", "")

    return ""


def extract_date(text: str) -> str:
    if not text:
        return ""

    t = text.replace(" ", "").replace("\n", "")

    # Pattern 1: 2026年6月23日
    m = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", t)
    if m:
        year, month, day = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Pattern 2: 2026/6/16
    m = re.search(r"(20\d{2})/(\d{1,2})/(\d{1,2})", t)
    if m:
        year, month, day = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop_dir", required=True)
    parser.add_argument("--output_dir", default="outputs/json_paddle")
    args = parser.parse_args()

    crop_dir = Path(args.crop_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_id = crop_dir.name

    ocr = PaddleOCR(
        lang="japan",
        use_textline_orientation=True
    )

    store_name_raw = run_ocr_on_image(ocr, crop_dir / "store_name.jpg")
    date_raw = run_ocr_on_image(ocr, crop_dir / "date.jpg")
    total_amount_raw = run_ocr_on_image(ocr, crop_dir / "total_amount.jpg")
    items_text = run_ocr_on_image(ocr, crop_dir / "items_area.jpg")

    output = {
        "image_id": image_id,
        "ocr_engine": "PaddleOCR",
        "store_name_raw": store_name_raw,
        "store_name_candidate": normalize_store_name(store_name_raw),
        "date_raw": date_raw,
        "date_candidate": extract_date(date_raw),
        "total_amount_raw": total_amount_raw,
        "total_amount_candidate": extract_amount(total_amount_raw),
        "items_text": items_text,
    }

    out_path = output_dir / f"{image_id}.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(output, ensure_ascii=False, indent=2))
    print()
    print(f"Saved JSON: {out_path}")


if __name__ == "__main__":
    main()
