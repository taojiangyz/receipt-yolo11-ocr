# Hybrid recognition: routing and evaluation

## Implemented scope

YOLO/PaddleOCR remains the recognition engine. Versioned rules suggest one of:

- `standard`: no current rule fires; this is not a correctness guarantee.
- `multimodal_review`: missing/invalid required fields, missing detected regions,
  or ambiguous totals in merchant/date/total require image-based review. Item
  text, item-region detection and item pairing never trigger review under rules 1.2.
  Enhanced date candidates also require review, even when syntactically valid.
- `retake`: an explicit observation says the image is unreadable. No automatic
  blur/glare/cropping detector has been implemented.

All item-related issues and item/total differences are advisory: taxes, discounts and incomplete item
extraction can explain differences. Correctly labelled cash/change values do not
by themselves trigger a total conflict. YOLO confidence is detection evidence,
not OCR confidence.

Each new recognition JSON includes `quality_gate`, `evidence`, and `multimodal_plan`.
The original candidates remain unchanged. Evidence stores EXIF-normalized image
size, crop boxes and detection scores. Original image bytes are preserved by the
library; field crops are available in the analysis/runtime directory. A future
adapter must reconstruct crops from original images with the same EXIF orientation
if runtime files are missing.

**There is no external model adapter yet.** `multimodal_plan.status=not_called`
and `max_automatic_attempts=1` describe the planned policy, not an executed request
or implemented retry counter. No API credentials are required for this stage.
The manager applies the current rules to original OCR on read, including older
saved receipts. Stored historical reports remain unchanged. Cached inference also
refreshes its routing report without repeating OCR. Model review targets only
merchant, date and total; item text is excluded from the planned candidate payload.

## Annotation workflow

Prepare the existing test split without overwriting prior annotations:

```bash
python -m src.receipt_evaluation init \
  --images data/yolo_receipt/images/test \
  --output data/evaluation/test_ground_truth.jsonl
```

This local file is excluded from Git through `data/`. Current inventory is 39
images of 13 physical receipts. Image variants retain their shared `receipt_group`.
For each image, inspect the original photograph, fill `truth.store_name` (canonical
chain name), `truth.date` (YYYY-MM-DD), `truth.total_amount` (integer JPY as a string),
and `reviewer`. Only then set `reviewed` to true. Do not copy OCR predictions as
truth. If a field cannot be read, leave the sample unreviewed and explain in `notes`.
Track these exclusions: reported scores cover reviewed/readable samples only.
Item-level truth, OCR character error rate, latency and model cost are not measured
by the current evaluator.

```bash
python -m src.receipt_evaluation inventory --predictions outputs/json_paddle
python -m src.receipt_evaluation evaluate \
  --manifest data/evaluation/test_ground_truth.jsonl \
  --predictions outputs/json_paddle
```

Prediction files are named `<image_id>.json` and use the existing `*_candidate`
fields. Evaluation reports coverage, per-field exact match, all-core-field exact
match, core-field errors routed to review, and core errors missed by routing.
No reviewed samples yields null accuracy, never zero or a fabricated benchmark.
Missing predictions are listed and excluded from the scored denominator.

Compare baseline and future hybrid outputs on the same reviewed image IDs, not
on independently selected subsets. Multiple views of one receipt are correlated;
retain receipt groups and report group counts. Do not move related views across
splits. If these test cases are used to tune rules, treat them as development data
and reserve newly collected receipt groups for a final unbiased evaluation.

## Initial diagnostic, 2026-10-01

Under rules 1.0, 97 of 102 archived outputs triggered review. Rules 1.1 remove
item-based triggers: 57 now trigger review and 45 pass the rules. Reasons overlap:
49 missing dates, 17 missing totals and 1 invalid date. This removes 40 review
triggers without changing any original recognition result. This is historical routing coverage, **not accuracy** and not
a benchmark of the current OCR runtime. It does not demonstrate cost savings.
The prepared truth manifest contains zero reviewed annotations. Re-run current
recognition and review truth before adjusting thresholds or claiming improvements.

## Next integration milestone

Select a provider/model supporting image input and configure credentials server-side.
Send original image plus relevant crops, OCR candidates and specific reasons. Keep
model output separate from original OCR and show changed fields. Enforce one automatic
attempt per image/rules/model version, validate response schema, retain unresolved
fields, and record latency/cost. Test both corrected errors and newly introduced
errors; sample receipts passing the rules to measure missed errors.

## Date recovery diagnostic

The 49 archived missing-date outputs contained 10 separator-format cases now
parseable, 38 incomplete/corrupted strings, and 1 empty string. Re-parsing all 102
archived outputs yields 47 routing triggers, versus 57 with the prior parsing.
These are recovered candidates and routing coverage, not field accuracy. Historical
JSON files are not rewritten. A complete four-digit year is required; two-digit or
truncated years remain unresolved. Multiple distinct dates are not silently selected.

Current recognition attempts one local contrast/upscale retry on the date crop when
parsing fails. `date_raw` retains the original OCR, and `date_recovery` records retry
source, text and candidate (or error type). If the detector found no date crop, the
system leaves the field for review; it does not pick an arbitrary date from the whole
receipt. Other fields survive an OCR retry error. Cache entries carry a pipeline
version so a changed recognition pipeline does not silently reuse older results.

## Audited retry results and rules 1.2

The remaining 39 archived failures (23 physical receipts) were each processed on
original and enhanced saved date crops, for 78 OCR passes. Codex visually read all
39 crops; these labels have not been independently verified by the user. All date
strings were visually readable, so no crop in this diagnostic required retaking.
Original-crop OCR produced no parseable dates. Enhanced OCR produced four candidates:
three matched the visible dates, while `lawson_002_b` incorrectly changed 2026-06-19
to 2020-06-19. The other 35 remained blank. This is a selected failure-set diagnostic,
not overall accuracy or a comparison of all possible OCR configurations.

Rules 1.2 therefore treat every nonempty enhanced date recovery as unverified and
route it for date review. A syntactically valid recovered date is not accepted as
proof of correctness. The three verified recoveries are `lawson_013_c` (2026-06-20),
`mybasket_001_a` and `mybasket_014_c` (both 2026-06-16). The other 36 remain candidates
for multimodal review or manual correction. Original OCR remains unchanged.

## 2.0 release configuration

The follow-up bounded comparison disabled full-document orientation and unwarping
for date crops only. Original crops then matched all 39 visually read dates. This
supersedes the default-preprocessing diagnostic as the released date configuration;
it does not change its historical findings. See [method, limits and results](date-crop-diagnostic.md).
Saved historical OCR is not rewritten. External multimodal calls remain unimplemented.

## Amount recovery and rules 1.3

JPY parsing accepts complete integer tokens and consistently grouped thousands
using commas or OCR-substituted dots. It never accepts a numeric prefix before
an incomplete separator, decimal or overlong token. Repeated identical currency
amounts are deduplicated; distinct amounts remain ambiguous unless labelled totals
resolve them. Clearly fragmented multi-line currency digits are left unresolved.

The initial amount OCR settings are retained: disabling document preprocessing
for every crop caused regressions in the development comparison. Only missing
amounts or unanchored noisy amount text receive one retry without document
orientation classification or unwarping. Retry errors preserve the receipt.
Original text stays in `total_amount_raw`; `amount_recovery` records retry evidence.
Nonempty retry candidates always require review. Unanchored original amount text
with unrelated OCR fragments also triggers review under rules 1.3. A clean single
currency line remains usable, but this does not guarantee correct digits.

Only merchant, date and total remain required. No item-related trigger was added.
Existing saved OCR is not rewritten. The pipeline version changed to invalidate
old inference caches, while read-time rules refresh without mutating stored reports.

### Missing core-region recovery (rules 1.4)

The primary YOLO pass keeps confidence 0.25. Only when store name, date, or
total amount has no detected region, one additional pass uses confidence 0.15.
It takes the highest-confidence region per missing core field, never replaces
existing crops, and does not recover item regions. Recovery source, threshold,
and detection confidence are retained in `region_recovery`. Any recovered
region requires human review (`region_recovery_unverified`), even when its OCR
candidate has a valid format. An optional detection failure leaves the primary
results usable. No external multimodal API is called by this fallback.
