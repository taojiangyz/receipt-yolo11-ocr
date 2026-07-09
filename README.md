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
## OCRとJSON出力

The project has been extended from YOLO11 detection-only to an end-to-end receipt OCR pipeline.

本プロジェクトは、YOLO11による領域検出だけでなく、OCRとJSON出力まで含むエンドツーエンドのレシート認識パイプラインに拡張されています。

After YOLO11 detects key receipt regions, each region is cropped and passed to OCR separately.  
The current MVP uses PaddleOCR as the main OCR engine for Japanese receipt text.

YOLO11で重要領域を検出した後、それぞれの領域を切り出して個別にOCRを適用します。  
現在のMVPでは、日本語レシート文字認識の主OCRエンジンとしてPaddleOCRを使用しています。

Current OCR pipeline:

現在のOCRパイプライン：

```text
Receipt image
→ YOLO11 region detection
→ Cropped receipt fields
→ PaddleOCR text extraction
→ Post-processing
→ Structured JSON output
```

The OCR pipeline extracts the following fields:

OCRパイプラインでは、以下のフィールドを抽出します。

- `store_name`
- `date`
- `total_amount`
- `items_text`

The `items_area` region is currently exported as raw OCR text.  
Item-level structured parsing, such as separating each product name, price, quantity, discount, and tax category, is not included in the MVP version.

現在、`items_area` 領域はOCR結果の生テキストとして出力します。  
商品名、価格、数量、割引、税区分などを商品ごとに構造化する処理は、MVP版には含めていません。

## Why PaddleOCR?  
## PaddleOCRを選択した理由

EasyOCR was first used as the baseline OCR engine to build the initial end-to-end pipeline.

最初はEasyOCRをベースラインOCRエンジンとして使用し、検出、切り出し、OCR、JSON出力までの初期パイプラインを構築しました。

However, after error analysis, EasyOCR was found to be unstable for Japanese receipt amounts and store logos.  
The `total_amount` field was especially difficult, with missing or incorrect values.

しかし、エラー分析の結果、EasyOCRは日本語レシートの金額欄や店舗ロゴの認識が不安定であることが分かりました。  
特に `total_amount` は、読み落としや誤認識が発生しやすいフィールドでした。

PaddleOCR was then tested on the same YOLO-cropped receipt regions.  
It produced better results for store name, date, total amount, and item text.

その後、同じYOLO切り出し領域に対してPaddleOCRをテストしました。  
その結果、店舗名、日付、合計金額、商品明細テキストにおいて、PaddleOCRの方がより良い結果を示しました。

Therefore, PaddleOCR was selected as the main OCR engine for the MVP, while EasyOCR and Tesseract are kept as baseline experiments for comparison and error analysis.

そのため、MVPではPaddleOCRを主OCRエンジンとして採用し、EasyOCRとTesseractは比較実験およびエラー分析用のベースラインとして残しています。

## Example OCR Command  
## OCR実行例

Run PaddleOCR on cropped receipt regions:

切り出されたレシート領域に対してPaddleOCRを実行します。

```bash
python3 src/ocr_receipt_paddle.py --crop_dir outputs/crops/family_002_c
```

Example JSON output:

JSON出力例：

```json
{
  "image_id": "family_002_c",
  "ocr_engine": "PaddleOCR",
  "store_name_raw": "FamilyMart",
  "store_name_candidate": "FamilyMart",
  "date_raw": "2026年6月23日（火）19:16",
  "date_candidate": "2026-06-23",
  "total_amount_raw": "¥610\n合計",
  "total_amount_candidate": "610",
  "items_text": "海鮮スティック明太マ\n¥180軽\nサラダチキンロール\n¥430軽"
}
```

## Demo Samples  
## デモサンプル

The final demo samples cover multiple Japanese convenience store chains:

最終デモサンプルは、複数の日本のコンビニチェーンを対象としています。

- FamilyMart
- 7-Eleven
- LAWSON
- MyBasket

Selected demo samples:

選定したデモサンプル：

- `family_002_c`
- `family_011_c`
- `seven_006_b`
- `lawson_016_a`
- `mybasket_009_a`

These samples demonstrate field detection, region cropping, OCR extraction, and JSON output across different receipt layouts.

これらのサンプルにより、異なるレシートレイアウトに対して、領域検出、切り出し、OCR抽出、JSON出力までの流れを確認できます。

## Current Status  
## 現在の状況

The project currently includes:

現在のプロジェクトには以下が含まれています。

- YOLO11 receipt region detection
- Region cropping for key receipt fields
- PaddleOCR-based text extraction
- Store name normalization
- Date extraction
- Total amount extraction
- JSON export
- Demo samples covering multiple convenience store chains
- OCR engine comparison between EasyOCR, Tesseract, and PaddleOCR

- YOLO11によるレシート領域検出
- 重要フィールドごとの領域切り出し
- PaddleOCRによる文字認識
- 店舗名の正規化
- 日付抽出
- 合計金額抽出
- JSON出力
- 複数コンビニチェーンのデモサンプル
- EasyOCR、Tesseract、PaddleOCRのOCRエンジン比較

The current MVP can detect and crop receipt regions, apply OCR to each cropped field, and export structured JSON results.

現在のMVPでは、レシート領域を検出・切り出し、各フィールドにOCRを適用し、構造化JSONとして出力できます。

## Current Limitation  
## 現在の制限

The current version focuses on field-level receipt extraction.

現在のバージョンは、フィールド単位のレシート情報抽出に重点を置いています。

The `items_area` field is exported as raw OCR text.  
It does not yet perform item-level structured parsing, such as extracting each product name, quantity, unit price, discount, and tax category.

`items_area` はOCRの生テキストとして出力しています。  
現時点では、商品名、数量、単価、割引、税区分などを商品ごとに構造化する処理は行っていません。

Some difficult cases still remain, especially when:

特に以下のようなケースでは、まだ課題が残っています。

- The receipt image is tilted or blurred
- The amount field is close to surrounding text or dashed lines
- The OCR engine returns a partial amount
- Store logos are stylized or partially cropped

- レシート画像が傾いている、またはぼやけている場合
- 金額欄が周辺の文字や罫線に近い場合
- OCRが金額の一部だけを返す場合
- 店舗ロゴが特殊なデザイン、または一部だけ切り出されている場合

For high-risk fields such as `total_amount`, returning an incorrect value is worse than leaving the field empty.  
Future versions should include stronger confidence checking and validation.

`total_amount` のような重要フィールドでは、誤った値を返すことは空欄にするよりもリスクが高いです。  
今後は、より強い信頼度チェックと検証処理を追加する必要があります。

## Future Work  
## 今後の改善

- Add item-level parsing for `items_area`
- Add stronger amount validation and confidence checks
- Improve date and time normalization
- Add receipt deskew preprocessing for tilted images
- Add more demo samples and evaluation metrics for OCR accuracy
- Build a simple Streamlit demo
- Add tests for JSON output format

- `items_area` の商品単位の構造化解析を追加
- 金額の検証と信頼度チェックを強化
- 日付・時刻の正規化を改善
- 傾いたレシート画像に対する傾き補正を追加
- OCR精度評価用のデモサンプルと評価指標を追加
- 簡単なStreamlitデモを作成
- JSON出力形式のテストを追加
