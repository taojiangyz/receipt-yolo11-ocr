# 日本語レシート解析 — YOLO11 + PaddleOCR

[English](README.md) | [日本語](README.ja.md)

日本のコンビニレシートから重要フィールドを検出し、検出領域だけに OCR を適用して、構造化 JSON を返すエンドツーエンドの Document AI プロトタイプです。

## 2.0 — ローカルレシート管理（開発版）

サイドバーに「1.0 · 识别实验室」と「2.0 · 票据管理」の2画面を用意しました。
既存の検出・切り出し・OCR・JSON表示を残し、確認・修正・保存・検索・CSV出力を追加しています。
画面操作時はセッション内の認識結果を再利用し、OCRを繰り返し実行しません。

画像、元のOCR結果、修正後の値、変更履歴は `.receipt_library/receipts.sqlite3` に保存します。
このディレクトリはGit管理対象外です。`RECEIPT_LIBRARY_DIR` で保存先を変更できます。
金額は整数の日本円です。現在はローカル・単一ユーザー向けで、クラウド同期は未実装です。
以下の評価指標・デモは1.0の成果として保持しています。起動コマンドは変更ありません。


## プロダクトデモ

![アップロードから JSON 出力までの Streamlit デモ](assets/demo/streamlit_upload_demo.gif)

レシートのアップロード、領域検出、切り出し、日本語 OCR、値の正規化、JSON 出力までを確認できます。

## システム構成

レシート全体への OCR は、小さい文字、店舗ごとのレイアウト差、傾き、撮影ノイズの影響を受けやすいため、本システムは業務上重要な領域を先に検出します。

```mermaid
flowchart LR
    A["レシート画像"] --> B["YOLO11 フィールド検出"]
    B --> C["領域別の切り出し・余白調整"]
    C --> D["PaddleOCR 日本語認識"]
    D --> E["正規化・検証"]
    E --> F["構造化 JSON"]
```

検出対象は `store_name`、`date`、`total_amount`、`items_area` の4領域です。

## 評価結果

独自データセットを用い、画像サイズ 640、80 Epoch で学習しました。同一レシートの画像は必ず同じ Split に保持し、類似画像によるデータリークを防止しています。掲載指標の Validation Split は、元レシート8枚・画像23枚です。

| 指標 | Validation 結果 |
|---|---:|
| Precision | 0.903 |
| Recall | 0.913 |
| mAP50 | 0.892 |
| mAP50–95 | 0.523 |

mAP50 と mAP50–95 の差から、対象領域の検出は比較的安定している一方、厳しい IoU 条件での Box 位置精度には改善余地があります。OCR は正解ラベルが未整備のため、現時点では定量精度を主張していません。

![正規化 Confusion Matrix](assets/evaluation/confusion_matrix_normalized.png)

## データセット

| 項目 | 値 |
|---|---:|
| 元レシート | 65 枚 |
| 画像 | 193 枚 |
| 1レシートあたり | 最大3方向 |
| 店舗チェーン | 4社 |
| 検出クラス | 4 |
| Annotation | 手動 Bounding Box |

FamilyMart、LAWSON、7-Eleven、MyBasket を対象としています。`src/split_yolo_dataset_by_receipt.py` は元レシート単位で Grouping し、店舗別に Train / Validation / Test を作成します。個人情報・購買情報を含む可能性があるため、レシート原画像は GitHub に公開していません。

## 実行方法

Python 3.11 または 3.12 を推奨します。

```bash
git clone https://github.com/taojiangyz/receipt-yolo11-ocr.git
cd receipt-yolo11-ocr
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python download_model.py
streamlit run streamlit_app.py
```

Weight は SHA256 を確認した上で `models/best.pt` に保存されます。別の Weight は `RECEIPT_MODEL_PATH` で指定できます。

## 実装上の判断

| 課題 | 対応 |
|---|---|
| 類似画像のリーク | 画像単位ではなく元レシート単位で分割 |
| 合計金額の切り欠け | `total_amount` の右・下 Padding を拡大 |
| 日本語 OCR の不安定さ | EasyOCR / Tesseract / PaddleOCR を比較し PaddleOCR を採用 |
| PyTorch / Paddle の競合 | YOLO を先に実行し PaddleOCR を遅延初期化 |
| 誤った合計金額のリスク | 未検証値を無理に返さず空値を優先 |
| 再現性 | 依存関係、Weight、Split Code、指標、Demo を公開 |

## 現在の制約

- 元レシートは65枚であり、店舗・端末・照明・レイアウトの多様性を増やす必要があります。
- OCR の Field Exact Match や Character Error Rate はまだ計測していません。
- 合計金額には Confidence Calibration と強い Validation が必要です。
- 傾き補正と商品単位の構造化解析は未実装です。
- Streamlit はローカル MVP であり、認証・監視・Cloud Deployment は未実装です。

次の評価では、レシート単位の Hold-out Test に対して Field Exact Match、Character Error Rate、合計金額精度、End-to-End Latency を測定します。

## ライセンス

Source Code は [MIT License](LICENSE) で公開しています。モデル Weight は Portfolio / Research Demo 用です。レシート原画像と第三者 Trademark は Software License の対象外です。
