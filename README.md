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

## Current Status

The YOLO11 detection model has been trained and evaluated.  
The predicted bounding boxes are visually close to the manually annotated ground-truth boxes.

This indicates that the model can detect key receipt layout regions and can be used as a preprocessing step before OCR.

## Next Steps

- Crop detected regions from receipt images
- Apply OCR to each cropped region
- Extract store name, date, and total amount as structured fields
- Output items_area as raw OCR text
- Build a simple Streamlit demo