from pathlib import Path
import os
from src.receipt_fields import normalize_store_name, extract_date, extract_amount
import io
import hashlib
import uuid

import numpy as np
import streamlit as st
from PIL import Image


MODEL_PATH = Path(
    os.getenv("RECEIPT_MODEL_PATH", "models/best.pt")
)
LEGACY_MODEL_PATH = Path(
    "runs/detect/receipt_yolo11_640-2/weights/best.pt"
)
RUNTIME_DIR = Path(".streamlit_runtime")
RUNTIME_DIR.mkdir(exist_ok=True)

FIELDS = ["store_name", "date", "total_amount", "items_area"]


@st.cache_resource
def load_yolo_model():
    from ultralytics import YOLO
    model_path = (
        MODEL_PATH if MODEL_PATH.exists() else LEGACY_MODEL_PATH
    )
    if not model_path.exists():
        raise FileNotFoundError(
            "YOLO model not found. Run `python download_model.py` "
            "or set RECEIPT_MODEL_PATH."
        )
    return YOLO(str(model_path))


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



def analyze_image(payload: bytes, filename: str) -> dict:
    """One inference per upload per session; edits and navigation reuse results."""
    from PIL import ImageOps
    digest = hashlib.sha256(payload).hexdigest()
    cached = st.session_state.get("receipt_analysis")
    if cached and cached["digest"] == digest:
        return cached
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(payload))).convert("RGB")
    run_dir = RUNTIME_DIR / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    input_path = run_dir / "input.png"
    image.save(input_path)
    result = load_yolo_model().predict(str(input_path), imgsz=640, conf=0.25,
                                      device="cpu", verbose=False)[0]
    crops = crop_detected_fields(image, result, run_dir)
    ocr = load_paddle_ocr()
    raw = {field: run_ocr_on_image(ocr, crop["path"]) for field, crop in crops.items()}
    output = {
        "digest": digest, "filename": filename, "payload": payload, "image": image,
        "detection": Image.fromarray(np.asarray(result.plot())[..., ::-1]),
        "crops": crops, "result": build_json_result(Path(filename).stem, raw),
    }
    st.session_state["receipt_analysis"] = output
    return output
