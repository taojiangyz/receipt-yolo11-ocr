from pathlib import Path
import argparse
import cv2
from ultralytics import YOLO


def expand_box(x1, y1, x2, y2, img_w, img_h, margin=0.05):
    box_w = x2 - x1
    box_h = y2 - y1

    dx = box_w * margin
    dy = box_h * margin

    x1 = max(0, int(x1 - dx))
    y1 = max(0, int(y1 - dy))
    x2 = min(img_w, int(x2 + dx))
    y2 = min(img_h, int(y2 + dy))

    return x1, y1, x2, y2


def predict_and_crop(model_path, image_path, output_dir, conf=0.25, imgsz=640):
    model_path = Path(model_path)
    image_path = Path(image_path)
    output_dir = Path(output_dir)

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    model = YOLO(str(model_path))

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")

    img_h, img_w = image.shape[:2]

    results = model.predict(
        source=str(image_path),
        imgsz=imgsz,
        conf=conf,
        save=True
    )

    result = results[0]
    names = result.names

    # Keep only the highest-confidence detection for each class
    best_by_class = {}

    for box in result.boxes:
        cls_id = int(box.cls[0])
        cls_name = names[cls_id]
        score = float(box.conf[0])

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        if cls_name not in best_by_class or score > best_by_class[cls_name]["confidence"]:
            best_by_class[cls_name] = {
                "class": cls_name,
                "confidence": score,
                "box": [x1, y1, x2, y2],
            }

    receipt_name = image_path.stem
    crop_dir = output_dir / receipt_name
    crop_dir.mkdir(parents=True, exist_ok=True)

    # Clean old crop images before saving new results
    for old_file in crop_dir.glob("*.jpg"):
        old_file.unlink()

    saved = []

    for cls_name, item in best_by_class.items():
        score = item["confidence"]
        x1, y1, x2, y2 = item["box"]
        x1, y1, x2, y2 = expand_box(x1, y1, x2, y2, img_w, img_h, margin=0.05)

        crop = image[y1:y2, x1:x2]

        if crop.size == 0:
            continue

        out_name = f"{cls_name}.jpg"
        out_path = crop_dir / out_name
        cv2.imwrite(str(out_path), crop)

        saved.append({
            "class": cls_name,
            "confidence": round(score, 4),
            "box": [x1, y1, x2, y2],
            "crop_path": str(out_path)
        })

    print("\nSaved best crops:")
    for item in saved:
        print(f"- {item['class']} | conf={item['confidence']} | {item['crop_path']}")

    missing = {"store_name", "date", "total_amount", "items_area"} - set(best_by_class.keys())
    if missing:
        print("\nMissing classes:")
        for cls in sorted(missing):
            print(f"- {cls}")

    print(f"\nCrop output directory: {crop_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to YOLO best.pt")
    parser.add_argument("--image", required=True, help="Path to receipt image")
    parser.add_argument("--output", default="outputs/crops", help="Output directory for cropped regions")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO input image size")
    args = parser.parse_args()

    predict_and_crop(
        model_path=args.model,
        image_path=args.image,
        output_dir=args.output,
        conf=args.conf,
        imgsz=args.imgsz
    )


if __name__ == "__main__":
    main()
