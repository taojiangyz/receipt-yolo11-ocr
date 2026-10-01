# Date crop configuration diagnostic — 2026-10-01

## Scope and method

The selected failure set contains 39 saved date crops from 23 physical receipts.
These are the archived missing-date cases still unresolved after separator parsing
was improved. Codex read each crop visually; these reference labels have not been
independently adjudicated. This is a development diagnostic, not a representative
held-out benchmark. The separate 39-image detector test split is a different set.

The bounded comparison used the same crop files, date parser and local Japanese
PaddleOCR models. The baseline ran the existing default document preprocessing.
The comparison disabled `use_doc_orientation_classify` and `use_doc_unwarping`,
while keeping `use_textline_orientation=True`. Both original crops and previously
prepared contrast-enhanced/upscaled crops were processed. No date digits were guessed.

| Configuration | Matches visual reference | Wrong nonempty date | Empty candidate |
|---|---:|---:|---:|
| Original crop, prior defaults | 0 | 0 | 39 |
| Enhanced crop, prior defaults | 3 | 1 | 35 |
| Original crop, document preprocessing disabled | 39 | 0 | 0 |
| Enhanced crop, document preprocessing disabled | 37 | 0 | 2 |

Nine additional crops with pre-existing nonempty date candidates were sampled
(up to three per chain, four chains represented). Eight candidates were unchanged.
One changed from 2020 to 2026; inspecting that crop confirmed 2026. Agreement with
old candidates does not establish accuracy for those eight samples.

## Release decision

Only the date region bypasses document orientation classification and unwarping.
Merchant, total and item OCR keep their prior settings. Original crops are read
first; enhancement is attempted only if parsing fails. Enhanced dates remain
unverified and require review under rules 1.2. Original OCR, retry evidence and
configuration metadata are retained. The cache pipeline version was changed.

These results implicate the current full-document preprocessing configuration on
narrow crops, rather than missing crop content. They do not isolate which of the
two disabled preprocessing stages caused the failures or establish that PaddleOCR
in general is unreliable. Rotated or unseen receipt layouts need broader evaluation.

## Validation environment

- macOS, Python 3.12.13, CPU inference.
- PaddleOCR 3.7.0, PaddlePaddle 3.3.1, PaddleX 3.7.2.
- Cached models: PP-OCRv6_medium_det / PP-OCRv6_medium_rec and
  PP-LCNet_x1_0_textline_ori; the baseline also enabled document preprocessing.
- Streamlit 1.59.1, Ultralytics 8.4.90, NumPy 2.3.5, Pillow 12.3.0,
  pandas 3.0.3, OpenCV Python 5.0.0.93.

The existing local environment was used; a fresh install on another OS has not
been verified. Dependency ranges may resolve other versions and OCR defaults may
change. Raw receipt crops and per-receipt diagnostic records remain local.

To reproduce the date-only configuration on an available local crop:

```python
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang="japan", use_textline_orientation=True,
                use_doc_orientation_classify=False, use_doc_unwarping=False)
pages = ocr.predict("path/to/date.jpg")
for page in pages:
    print(page.get("rec_texts", []))
```

A complete original receipt was also run through the released shared pipeline:
all four regions were detected, its date matched the visible 2026-06-19, and a
separate temporary library passed save, edit, reopen, audit and CSV checks.
