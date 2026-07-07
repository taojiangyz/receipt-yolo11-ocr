# Receipt YOLO11 OCR Project

This project detects key layout regions from Japanese convenience store receipts using YOLO11.

The goal is to improve receipt OCR by first detecting important regions, instead of applying OCR to the entire receipt image directly.

## Project Overview

Receipt images often contain many small text lines, different layouts, background noise, and tilted photos.  
Direct OCR on the whole receipt can be unstable.

Therefore, this project uses object detection as a preprocessing step.

The model detects the following receipt regions:

- store_name
- date
- total_amount
- items_area

After these regions are detected, each region can be cropped and passed to OCR separately.

## Pipeline

1. Collect Japanese convenience store receipt images
2. Annotate key receipt regions with bounding boxes
3. Train a YOLO11 object detection model
4. Evaluate the model using validation images
5. Compare predicted bounding boxes with manual labels
6. Crop detected regions
7. Apply OCR to extract text
8. Output structured receipt information

## Model

- Model: YOLO11
- Task: Object Detection
- Input image size: 640
- Classes:
  - store_name
  - date
  - total_amount
  - items_area

## Qualitative Evaluation Examples

The following examples show YOLO11 predictions on Japanese convenience store receipt images.  
The model detects key receipt regions such as store name, date, total amount, and item area.

### FamilyMart Example

![FamilyMart Prediction](assets/evaluation/family_002_a.jpg)

### Lawson Example

![Lawson Prediction](assets/evaluation/lawson_002_b.jpg)

### MyBasket Example

![MyBasket Prediction](assets/evaluation/mybasket_001_b.jpg)

## Evaluation Results

### Normalized Confusion Matrix

![Normalized Confusion Matrix](assets/evaluation/confusion_matrix_normalized.png)

### Precision-Recall Curve

![PR Curve](assets/evaluation/BoxPR_curve.png)

### F1 Curve

![F1 Curve](assets/evaluation/BoxF1_curve.png)

## OCR and JSON Output

The project has been extended from YOLO11 detection-only to an end-to-end receipt OCR pipeline.

After YOLO11 detects the key receipt regions, each region is cropped and passed to OCR separately.

Current OCR pipeline:

Receipt image
→ YOLO11 region detection
→ Cropped receipt fields
→ EasyOCR text extraction
→ JSON output

The OCR script reads the cropped regions and exports the result as JSON.

Example OCR command:

    python3 src/ocr_receipt.py --crop_dir outputs/crops/family_002_c

Example JSON output:

    {
      "image_id": "family_002_c",
      "store_name_raw": "Familylart",
      "store_name_candidate": "FamilyMart",
      "date_raw": "2026年 6月23日 (火) 19.16",
      "total_amount_raw": "令 言十\n半日1ロ",
      "total_amount_candidate": "",
      "items_text": "海鮮スティック明太マ サラダチキンロール\n半180軽 判3軽"
    }

## Current Status

The YOLO11 detection model has been trained and evaluated.

The model can detect key receipt layout regions such as store name, date, total amount, and item area. The detection results are visually close to the manually annotated ground-truth boxes.

The project now includes:

- YOLO11 receipt region detection
- Region cropping
- EasyOCR-based OCR extraction
- Store name normalization
- JSON export
- Batch processing workflow

## Current Limitation

EasyOCR is used as the first OCR baseline.

The pipeline can generate JSON outputs from cropped receipt regions, but total amount recognition is still unstable in the current version.

In a small preliminary test, `total_amount_candidate` was extracted in 4 out of 35 tested receipts. This suggests that amount-specific preprocessing or another OCR engine should be evaluated in the next version.

When no reliable amount is detected, the current version keeps `total_amount_candidate` empty instead of returning an incorrect value.

## Next Steps

- Improve total amount recognition with amount-specific preprocessing
- Compare EasyOCR with Tesseract and PaddleOCR
- Add date normalization
- Improve store name normalization for FamilyMart, LAWSON, 7-Eleven, and MyBasket
- Add OCR error analysis
- Build a simple Streamlit demo
- Add tests for JSON output format
