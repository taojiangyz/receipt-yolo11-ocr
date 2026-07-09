from pathlib import Path
import json
import re
import uuid

import numpy as np
import streamlit as st
from PIL import Image
from ultralytics import YOLO


MODEL_PATH = Path("runs/detect/receipt_yolo11_640-2/weights/best.pt")
RUNTIME_DIR = Path(".streamlit_runtime")
RUNTIME_DIR.mkdir(exist_ok=True)

FIELDS = ["store_name", "date", "total_amount", "items_area"]


st.set_page_config(
    page_title="Receipt YOLO11 OCR Demo",
    page_icon="🧾",
    layout="wide",
)


@st.cache_resource
def load_yolo_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"YOLO model not found: {MODEL_PATH}")
    return YOLO(str(MODEL_PATH))


@st.cache_resource
def load_paddle_ocr():
    # Import PaddleOCR lazily after YOLO detection.
    # This avoids loading PaddlePaddle before PyTorch/YOLO inference in the same Streamlit process.
    from paddleocr import PaddleOCR

    return PaddleOCR(
        lang="japan",
        use_textline_orientation=True
    )


def expand_box_custom(x1, y1, x2, y2, img_w, img_h, left=0.05, right=0.05, top=0.05, bottom=0.05):
    box_w = x2 - x1
    box_h = y2 - y1

    x1 = max(0, int(x1 - box_w * left))
    y1 = max(0, int(y1 - box_h * top))
    x2 = min(img_w, int(x2 + box_w * right))
    y2 = min(img_h, int(y2 + box_h * bottom))

    return x1, y1, x2, y2


def run_ocr_on_image(ocr, image_path: Path) -> str:
    if not image_path.exists():
        return ""

    result = ocr.ocr(str(image_path))
    texts = []

    if not result:
        return ""

    for page in result:
        if isinstance(page, dict):
            rec_texts = page.get("rec_texts", [])
            texts.extend([t for t in rec_texts if t])
            continue

        if isinstance(page, list):
            for line in page:
                try:
                    text = line[1][0]
                    texts.append(text)
                except Exception:
                    continue

    return "\n".join(texts)


def normalize_store_name(text: str) -> str:
    t = text.replace("\n", " ").strip()
    lower = t.lower()

    if "family" in lower or "famima" in lower or "ファミ" in t:
        return "FamilyMart"

    if "lawson" in lower or "ローソン" in t:
        return "LAWSON"

    if "7-eleven" in lower or "seven" in lower or "セブン" in t or "イレブン" in t:
        return "7-Eleven"

    if "mybasket" in lower or "まいばす" in t or "まいはす" in t or "まいほす" in t:
        return "MyBasket"

    return ""


def extract_date(text: str) -> str:
    t = text.replace(" ", "")

    m = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", t)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

    m = re.search(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", t)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

    return ""


def extract_amount(text: str) -> str:
    t = text.replace(" ", "").replace(",", "")
    t = t.replace("￥", "¥")

    yen_matches = re.findall(r"¥\d{3,6}", t)
    if yen_matches:
        values = [int(m.replace("¥", "")) for m in yen_matches]
        return str(max(values))

    # fallback: only accept 3-6 digit numbers near common total words
    if any(word in t for word in ["合計", "総計", "計"]):
        nums = re.findall(r"\d{3,6}", t)
        if nums:
            return str(max(int(n) for n in nums))

    return ""


def crop_detected_fields(image: Image.Image, result, run_dir: Path):
    img_w, img_h = image.size
    names = result.names

    best_boxes = {}

    if result.boxes is None:
        return {}

    for box in result.boxes:
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        cls_name = names.get(cls_id, str(cls_id))

        if cls_name not in FIELDS:
            continue

        if cls_name not in best_boxes or conf > best_boxes[cls_name]["conf"]:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            best_boxes[cls_name] = {
                "conf": conf,
                "box": (x1, y1, x2, y2),
            }

    crops = {}

    for field in FIELDS:
        if field not in best_boxes:
            continue

        x1, y1, x2, y2 = best_boxes[field]["box"]

        if field == "total_amount":
            x1, y1, x2, y2 = expand_box_custom(
                x1, y1, x2, y2,
                img_w, img_h,
                left=0.10,
                right=0.35,
                top=0.15,
                bottom=0.30,
            )
        else:
            x1, y1, x2, y2 = expand_box_custom(
                x1, y1, x2, y2,
                img_w, img_h,
                left=0.05,
                right=0.05,
                top=0.05,
                bottom=0.05,
            )

        crop = image.crop((x1, y1, x2, y2))
        crop_path = run_dir / f"{field}.jpg"
        crop.save(crop_path)

        crops[field] = {
            "image": crop,
            "path": crop_path,
            "confidence": best_boxes[field]["conf"],
        }

    return crops


def build_json_result(image_id: str, raw_texts: dict) -> dict:
    store_raw = raw_texts.get("store_name", "")
    date_raw = raw_texts.get("date", "")
    total_raw = raw_texts.get("total_amount", "")
    items_raw = raw_texts.get("items_area", "")

    return {
        "image_id": image_id,
        "ocr_engine": "PaddleOCR",
        "store_name_raw": store_raw,
        "store_name_candidate": normalize_store_name(store_raw),
        "date_raw": date_raw,
        "date_candidate": extract_date(date_raw),
        "total_amount_raw": total_raw,
        "total_amount_candidate": extract_amount(total_raw),
        "items_text": items_raw,
    }


def main():
    st.title("Receipt YOLO11 OCR Demo")
    st.caption("レシートYOLO11 OCRデモ")

    st.markdown(
        """
Upload a Japanese convenience store receipt image.  
The app runs YOLO11 field detection, crops key receipt regions, applies PaddleOCR, and outputs structured JSON.

日本のコンビニレシート画像をアップロードすると、YOLO11で重要領域を検出し、切り出し、PaddleOCRで文字認識し、JSONとして出力します。
"""
    )

    st.info(
        "Model: YOLO11 field detector | OCR Engine: PaddleOCR | Output: structured receipt JSON"
    )

    uploaded_file = st.file_uploader(
        "Upload receipt image / レシート画像をアップロード",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is None:
        st.warning("Please upload a receipt image to start. / レシート画像をアップロードしてください。")
        return

    run_id = uuid.uuid4().hex[:8]
    run_dir = RUNTIME_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(uploaded_file).convert("RGB")
    input_path = run_dir / "input.jpg"
    image.save(input_path)

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Uploaded Receipt / アップロード画像")
        st.image(image, use_container_width=True)

    with st.spinner("Loading YOLO11 model..."):
        model = load_yolo_model()

    with st.spinner("Running YOLO11 detection..."):
        results = model.predict(str(input_path), imgsz=640, conf=0.25, device="cpu", verbose=False)
        result = results[0]

    plotted = result.plot()
    plotted_rgb = Image.fromarray(np.asarray(plotted)[..., ::-1])

    with right:
        st.subheader("YOLO11 Detection Result / YOLO11検出結果")
        st.image(plotted_rgb, use_container_width=True)

    crops = crop_detected_fields(image, result, run_dir)

    st.divider()
    st.subheader("Cropped Fields / 切り出し領域")

    crop_cols = st.columns(4)

    for col, field in zip(crop_cols, FIELDS):
        with col:
            st.markdown(f"**{field}**")
            if field in crops:
                st.image(crops[field]["image"], use_container_width=True)
                st.caption(f"confidence: {crops[field]['confidence']:.3f}")
            else:
                st.error("Not detected")

    raw_texts = {}

    with st.spinner("Loading PaddleOCR model..."):
        ocr = load_paddle_ocr()

    with st.spinner("Running PaddleOCR..."):
        for field in FIELDS:
            if field in crops:
                raw_texts[field] = run_ocr_on_image(ocr, crops[field]["path"])
            else:
                raw_texts[field] = ""

    json_result = build_json_result(input_path.stem, raw_texts)

    json_path = run_dir / "result.json"
    json_path.write_text(
        json.dumps(json_result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    st.divider()
    st.subheader("OCR Result / OCR結果")

    result_left, result_right = st.columns([1, 1])

    with result_left:
        st.markdown("### Structured Fields / 構造化フィールド")
        st.write(f"**Store Name / 店舗名:** {json_result['store_name_candidate']}")
        st.write(f"**Date / 日付:** {json_result['date_candidate']}")
        st.write(f"**Total Amount / 合計金額:** {json_result['total_amount_candidate']}")

        st.markdown("### Items Text / 商品明細テキスト")
        st.text(json_result["items_text"])

    with result_right:
        st.markdown("### JSON Output / JSON出力")
        st.json(json_result)

    st.download_button(
        label="Download JSON / JSONをダウンロード",
        data=json.dumps(json_result, ensure_ascii=False, indent=2),
        file_name="receipt_ocr_result.json",
        mime="application/json",
    )

    st.divider()
    st.markdown(
        """
### Notes / 補足

- YOLO11 is used for receipt field detection.
- PaddleOCR is used for OCR after cropping.
- `items_area` is currently exported as raw OCR text.
- Item-level structured parsing is future work.

- YOLO11でレシート領域を検出しています。
- 切り出し後のOCRにはPaddleOCRを使用しています。
- `items_area` は現在、生テキストとして出力しています。
- 商品単位の構造化解析は今後の改善項目です。
"""
    )


if __name__ == "__main__":
    main()
