# Receipt YOLO11 OCR Project  
# レシートYOLO11 OCRプロジェクト

This project detects key layout regions from Japanese convenience store receipts using YOLO11.  
The goal is to improve receipt OCR by first detecting important regions, instead of applying OCR to the entire receipt image directly.

本プロジェクトは、YOLO11を用いて日本のコンビニレシート画像から重要なレイアウト領域を検出するプロジェクトです。  
レシート画像全体に直接OCRを適用するのではなく、先に重要領域を検出することで、OCR精度の改善を目指しています。

---

## Project Overview  
## プロジェクト概要

Receipt images often contain many small text lines, different layouts, background noise, and tilted photos.  
Direct OCR on the whole receipt can be unstable.

レシート画像には、小さな文字、店舗ごとの異なるレイアウト、背景ノイズ、傾きなどが含まれます。  
そのため、画像全体に直接OCRをかけると、認識結果が不安定になることがあります。

Therefore, this project uses object detection as a preprocessing step before OCR.

そのため、本プロジェクトではOCRの前処理として物体検出を使用しています。

The model detects the following receipt regions:

検出対象のレシート領域は以下の通りです。

- `store_name`
- `date`
- `total_amount`
- `items_area`

After these regions are detected, each region can be cropped and passed to OCR separately.

これらの領域を検出した後、それぞれの領域を切り出し、個別にOCRへ入力します。

---

### Streamlit Upload Demo  
### Streamlitアップロードデモ

The following GIF shows the Streamlit demo. After uploading a receipt image, the app runs YOLO11 detection, crops key fields, applies PaddleOCR, and outputs structured JSON.

以下のGIFでは、レシート画像をアップロードした後、YOLO11による領域検出、切り出し、PaddleOCRによるOCR、構造化JSON出力までの流れを確認できます。

![Streamlit Upload Demo](assets/demo/streamlit_upload_demo.gif)

These samples demonstrate field detection, region cropping, OCR extraction, and JSON output across different receipt layouts.

これらのサンプルにより、異なるレシートレイアウトに対して、領域検出、切り出し、OCR抽出、JSON出力までの流れを確認できます。

---

---

## Pipeline  
## パイプライン

1. Collect Japanese convenience store receipt images  
   日本のコンビニレシート画像を収集

2. Annotate key receipt regions with bounding boxes  
   重要領域にバウンディングボックスを付与

3. Train a YOLO11 object detection model  
   YOLO11物体検出モデルを学習

4. Evaluate the model using validation images  
   検証画像でモデルを評価

5. Compare predicted bounding boxes with manual labels  
   予測されたバウンディングボックスと手動ラベルを比較

6. Crop detected regions  
   検出領域を切り出し

7. Apply OCR to extract text  
   OCRを適用して文字情報を抽出

8. Output structured receipt information  
   構造化されたレシート情報を出力

---

## Model  
## モデル

- Model: YOLO11  
- Task: Object Detection  
- Input image size: 640  
- Classes:
  - `store_name`
  - `date`
  - `total_amount`
  - `items_area`

- モデル：YOLO11  
- タスク：物体検出  
- 入力画像サイズ：640  
- クラス：
  - `store_name`
  - `date`
  - `total_amount`
  - `items_area`

---

## Dataset Summary  
## データセット概要

The dataset was created from Japanese convenience store receipts collected and photographed for this project.

本プロジェクトでは、日本のコンビニレシートを収集・撮影し、独自データセットを作成しました。

| Item | Details |
|---|---|
| Original receipts | 65 |
| Total images | 195 |
| Images per receipt | 3 shooting angles |
| Convenience store chains | 4 |
| Detection classes | 4 |
| Annotation method | Manual bounding-box annotation |

| 項目 | 内容 |
|---|---|
| 元のレシート数 | 65枚 |
| 画像総数 | 195枚 |
| 各レシートの撮影枚数 | 3つの角度 |
| 対象コンビニチェーン | 4社 |
| 検出クラス数 | 4クラス |
| アノテーション方法 | 手動によるバウンディングボックス付与 |

### Image Distribution by Store  
### 店舗別画像数

| Store | Number of Images |
|---|---:|
| FamilyMart | 48 |
| LAWSON | 48 |
| 7-Eleven | 48 |
| MyBasket | 51 |
| **Total** | **195** |

Each original receipt was photographed from three different angles to include variations in tilt and position.

各レシートを3つの角度から撮影し、傾きや位置の違いをデータに含めました。

The following four regions were manually annotated:

以下の4領域を手動でアノテーションしました。

- `store_name`
- `date`
- `total_amount`
- `items_area`

Because multiple images can originate from the same physical receipt, receipt-level grouped splitting is important to prevent similar images from appearing across training and validation sets. This is an important point for future eva luation revisions.

同じレシートから複数の画像を作成しているため、類似画像が学習用と検証用の両方に入らないよう、元のレシート単位でデータを分割することが重要です。今後の評価改善では、この点を特に重視します。

---

## Data Collection  
## データ収集

This project uses a small custom dataset of Japanese convenience store receipt images collected by myself.

本プロジェクトでは、自分で収集した日本のコンビニレシート画像の小規模カスタムデータセットを使用しています。

The dataset includes receipts from multiple Japanese convenience store chains, such as FamilyMart, LAWSON, 7-Eleven, and MyBasket.

データセットには、FamilyMart、LAWSON、7-Eleven、MyBasketなど、複数の日本のコンビニチェーンのレシートが含まれています。

Receipt photos were taken under different conditions, including different angles, distances, lighting conditions, and receipt layouts.

レシート画像は、異なる角度、距離、照明条件、レイアウトを含む複数の条件で撮影しました。

The following key regions were manually annotated with bounding boxes:

以下の重要領域に対して、手動でバウンディングボックスを付与しました。

- `store_name`
- `date`
- `total_amount`
- `items_area`

The annotations were converted into YOLO format for object detection training.

アノテーションは、物体検出モデルの学習に使用するため、YOLO形式に変換しました。

---

## Why YOLO11?  
## YOLO11を選択した理由

YOLO11 was selected because it provides a practical balance between detection accuracy, inference speed, and implementation cost.

YOLO11は、検出精度、推論速度、実装コストのバランスが良いため採用しました。

The Ultralytics ecosystem provides an integrated workflow for training, validation, inference, visualization, and model export. This was suitable for building an MVP and a Streamlit demo within a limited development period.

Ultralyticsには、学習、検証、推論、可視化、モデル出力までの統合環境があります。そのため、限られた開発期間でMVPとStreamlitデモを構築する目的に適していました。

YOLO is a one-stage detector, so it is generally suitable for applications that require relatively fast inference.

YOLOは一段階検出器であり、比較的高速な推論が必要なアプリケーションに適しています。

YOLO11 also uses an anchor-free detection approach. Unlike traditional anchor-based detectors, it does not require manually designing predefined anchor-box sizes and aspect ratios.

また、YOLO11はAnchor-free方式を採用しています。従来のAnchor-based検出器とは異なり、事前にAnchor Boxのサイズやアスペクト比を細かく設計する必要がありません。

A controlled comparison with every alternative model, such as YOLOv8, SSD, and Faster R-CNN, was not performed. Therefore, this project does not claim that YOLO11 is universally the best model.

YOLOv8、SSD、Faster R-CNNなど、すべての候補モデルとの比較実験は行っていません。そのため、YOLO11が常に最良のモデルであるとは主張していません。

---

## Training and Inference
## 学習と推論

After training, the YOLO11 model detects the four receipt fields. The detected regions are then passed to PaddleOCR for text recognition and structured JSON generation.

学習済みYOLO11モデルでレシート内の4つの領域を検出し、その結果をPaddleOCRへ入力して文字認識を行い、構造化されたJSONとして出力します。

## Model Evaluation  
## モデル評価

The YOLO11 model was evaluated using validation images.

YOLO11モデルは検証用画像を用いて評価しました。

The following validation metrics were recorded from the completed YOLO11 training run:

完了したYOLO11学習実験では、以下の検証指標が記録されました。

| Metric | Value |
|---|---:|
| Precision | 0.903 |
| Recall | 0.913 |
| mAP50 | 0.892 |
| mAP50-95 | 0.523 |

The relatively high mAP50 indicates that the model generally detects the target receipt regions successfully. The lower mAP50-95 indicates that bounding-box localization still has room for improvement under stricter IoU thresholds.

mAP50が比較的高いことから、対象領域自体は概ね検出できています。一方、mAP50-95はmAP50より低いため、より厳しいIoU条件ではバウンディングボックス位置に改善の余地があります。


These results show that the model can detect key receipt regions with reasonably high precision and recall.

これらの結果から、モデルはレシート内の重要領域を比較的高い適合率と再現率で検出できていることが分かります。

In addition to numerical metrics, qualitative evaluation was also performed by comparing predicted bounding boxes with manual annotations.

数値指標に加えて、予測されたバウンディングボックスと手動アノテーションを比較する定性的評価も行いました。

For this project, detection quality is especially important because OCR accuracy depends heavily on whether the correct receipt regions are cropped.

本プロジェクトでは、OCR精度が正しい領域切り出しに大きく依存するため、検出品質が特に重要です。

---

## Technical Notes
## 技術補足

| Concept | Role in This Project |
|---|---|
| Ground Truth | Manually annotated bounding boxes used as training targets |
| Backbone / Neck | Extract and combine multi-scale visual features |
| Detection Head | Predicts receipt-field classes and bounding boxes |
| NMS | Removes duplicated overlapping predictions during inference |
| Anchor Strategy | YOLO11 uses an anchor-free detection approach |

本プロジェクトでは、手動アノテーションをGround Truthとして使用し、YOLO11のAnchor-free検出とNMSによって最終的な領域を出力します。

## Qualitative Evaluation Examples  
## 定性的評価例

The following examples show YOLO11 predictions on Japanese convenience store receipt images.  
The model detects key receipt regions such as store name, date, total amount, and item area.

### FamilyMart Example

![FamilyMart Prediction](assets/evaluation/family_002_a.jpg)

### Lawson Example

![Lawson Prediction](assets/evaluation/lawson_002_b.jpg)

### MyBasket Example

![MyBasket Prediction](assets/evaluation/mybasket_001_b.jpg)

## Evaluation Results  
## 評価結果

### Normalized Confusion Matrix

![Normalized Confusion Matrix](assets/evaluation/confusion_matrix_normalized.png)

### Precision-Recall Curve

![PR Curve](assets/evaluation/BoxPR_curve.png)

### F1 Curve

![F1 Curve](assets/evaluation/BoxF1_curve.png)

## Error Analysis and Improvements  
## エラー分析と改善

The failure cases were analyzed by separating the pipeline into detection, cropping, OCR, and post-processing stages.

失敗ケースについては、検出、切り出し、OCR、後処理の各段階に分けて原因を確認しました。

### Case 1: Incomplete Total Amount Crops  
### ケース1：合計金額の切り出し不足

Some total amount values were close to the right or lower edge of the detected bounding box. A uniform crop margin sometimes removed part of the amount.

一部のレシートでは、合計金額が検出ボックスの右端または下側に近く、通常の余白では金額の一部が欠ける場合がありました。

**Improvement / 改善**

Field-specific padding was added to `total_amount`. The right and lower margins were expanded more than those of the other fields.

`total_amount`専用のパディングを追加し、他のフィールドよりも右側と下側の余白を大きくしました。

### Case 2: Unstable OCR Results  
### ケース2：OCR結果の不安定さ

EasyOCR was initially used as the baseline OCR engine. Error analysis showed that it was unstable for Japanese store logos and total amounts.

最初はEasyOCRをベースラインとして使用しましたが、エラー分析の結果、日本語の店舗ロゴや合計金額で認識が不安定であることが分かりました。

**Improvement / 改善**

EasyOCR, Tesseract, and PaddleOCR were tested on the same YOLO-cropped regions. PaddleOCR produced more stable results for store name, date, total amount, and item text, so it was selected as the main OCR engine for the MVP.

同じYOLO切り出し領域に対してEasyOCR、Tesseract、PaddleOCRを比較しました。店舗名、日付、合計金額、商品明細でPaddleOCRの結果がより安定していたため、MVPの主OCRエンジンとして採用しました。

### Case 3: Runtime Conflict in the Streamlit Demo  
### ケース3：Streamlitデモの実行時競合

In the local macOS environment, initializing PaddlePaddle before YOLO inference caused a runtime conflict during the YOLO NMS stage.

ローカルのmacOS環境では、YOLO推論前にPaddlePaddleを初期化すると、YOLOのNMS処理時に実行環境の競合が発生しました。

**Improvement / 改善**

The execution order was changed so that YOLO detection and cropping run first. PaddleOCR is then imported and initialized lazily after detection is complete.

YOLOによる検出と切り出しを先に実行し、その完了後にPaddleOCRを遅延読み込みする構成へ変更しました。

---

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

## Example JSON Output
## JSON出力例

The final pipeline exports raw OCR text and normalized candidate values as structured JSON.

最終パイプラインでは、OCRの生テキストと正規化した候補値を構造化JSONとして出力します。

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

The final demo samples cover multiple Japanese convenience store chains and different receipt layouts.

最終デモサンプルは、複数の日本のコンビニチェーンと異なるレシートレイアウトを対象としています。

| Store | Sample ID | Detection | OCR / JSON Output |
|---|---|---|---|
| FamilyMart | `family_002_c` | Success | Success |
| FamilyMart | `family_011_c` | Success | Success |
| 7-Eleven | `seven_006_b` | Success | Success |
| LAWSON | `lawson_016_a` | Success | Success |
| MyBasket | `mybasket_009_a` | Success | Success |

| 店舗 | サンプルID | 領域検出 | OCR / JSON出力 |
|---|---|---|---|
| FamilyMart | `family_002_c` | 成功 | 成功 |
| FamilyMart | `family_011_c` | 成功 | 成功 |
| 7-Eleven | `seven_006_b` | 成功 | 成功 |
| LAWSON | `lawson_016_a` | 成功 | 成功 |
| MyBasket | `mybasket_009_a` | 成功 | 成功 |

The following overview image shows cropped receipt fields used in the OCR pipeline.

以下の画像は、OCRパイプラインで使用する切り出し済みレシート領域の概要です。

![Demo Samples Overview](assets/demo/demo_samples_overview.png)

## Run the Streamlit Demo
## Streamlitデモの実行

Launch the local Streamlit application:

ローカルでStreamlitデモを起動します。

```bash
streamlit run streamlit_app.py
```
---

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

## Design Trade-offs  
## 設計上のトレードオフ

This MVP was designed by considering accuracy, inference speed, development cost, and reliability.

本MVPでは、精度、推論速度、開発コスト、信頼性のバランスを考慮しました。

| Factor | Design Decision |
|---|---|
| Accuracy | Detect only the four fields required for the MVP and apply OCR separately |
| Speed | Apply OCR to cropped regions instead of the entire receipt image |
| Development Cost | Use Ultralytics and PaddleOCR instead of training an OCR model from scratch |
| Reliability | Prefer an empty value over an unreliable value for high-risk fields |
| Maintainability | Separate detection, cropping, OCR, and post-processing stages |

| 観点 | 設計方針 |
|---|---|
| 精度 | MVPに必要な4領域を検出し、それぞれにOCRを適用 |
| 速度 | 画像全体ではなく、切り出した領域だけをOCR処理 |
| 開発コスト | OCRモデルを一から学習せず、UltralyticsとPaddleOCRを活用 |
| 信頼性 | 重要項目では、不確かな値より空欄を優先 |
| 保守性 | 検出、切り出し、OCR、後処理を段階ごとに分離 |

For `total_amount`, an incorrect value can be more harmful than a missing value. A production system should therefore use confidence thresholds, validation rules, and human review for uncertain results.

`total_amount`では、値が空欄になることよりも、誤った金額を返すことの方が大きな問題になる可能性があります。実運用では、信頼度閾値、検証ルール、人による確認が必要です。

---

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

- Increase the number and diversity of receipt images
- Build OCR ground truth and calculate field-level accuracy
- Add stronger total amount validation and confidence checks
- Add receipt deskew preprocessing for tilted images

- レシート画像の件数と多様性を拡大
- OCR正解データを作成し、フィールド単位の精度を評価
- 合計金額の検証と信頼度チェックを強化
- 傾いたレシート画像の補正を追加
