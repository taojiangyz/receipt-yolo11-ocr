# 2.0 validation — 2026-10-03

## Local recognition development retest

17 newly photographed receipts (two chains, two dates) were converted from HEIC
into JPEG for processing. Original files were preserved. The same images and
YOLO weights were used for the before/after comparison.

| Agreement with visual reference | Initial pipeline | Amount fixes | Core-region fallback |
|---|---:|---:|---:|
| Merchant brand | 16/17 | 16/17 | 17/17 |
| Date | 15/17 | 15/17 | 17/17 |
| Total | 9/17 | 15/17 | 15/17 |
| All three core fields | 6/17 | 12/17 | 15/17 |
| Incorrect core result passing routing rules | 3 | 0 | 0 |

Changes addressed three different failure stages: conservative amount parsing,
conditional amount-crop OCR retry without document orientation/unwarping, and a
second detection pass at confidence 0.15 only for missing core regions (primary
threshold remains 0.25). Recovery candidates always require review. Item issues
never trigger image-model requests.

References came from Codex visual reading and are not independently verified.
Merchant comparisons use chain names, not branches. The images were used to
diagnose and tune the changes, so these are development results, not held-out
accuracy. Rules passing does not establish correctness on other receipts.

## Live multimodal workflow checks

Alibaba Cloud Bailian, Beijing, `qwen3-vl-plus`; target field: total amount only.
Each successful request included the full image and the detected amount crop.
The figures below were read from local SQLite request records after successful
manual entry and saving. No receipt images, API credentials, full responses or
request identifiers are published here.

| Case | Local OCR total | Model suggestion | Visual reference | Successful-request tokens | Latency |
|---|---|---:|---:|---:|---:|
| A | Missing | 129 JPY | 129 JPY | 3,035 (2,909 input / 126 output) | 79.554 s |
| B | Missing | 135 JPY | 135 JPY | 3,000 (2,910 input / 90 output) | 52.166 s |

The user entered and saved both suggested totals. Their saved review status is
still **pending review**. The model suggestions remain separate and unverified;
model explanation text has not been independently assessed for correctness.

Successful calls total **6,035 tokens**. Earlier attempts included a network
failure and HTTP 401 while credentials were being corrected. Failed-request
usage and bill charges are unknown; cost estimates are unavailable because token
prices were not configured. Do not treat missing usage as zero cost.

No automatic retry occurs. Failed calls can be manually retried with a fee notice,
up to three attempts by default. One additional attempt was explicitly authorized
after credential correction, preserving prior failures. A fix to the save-notice
rendering was verified after a saved receipt exposed a Streamlit magic-display
error; the stored receipt was not lost.

These two deliberately selected failures demonstrate image API integration and
the review/save workflow. They do not establish overall multimodal accuracy,
receipt-level 100% accuracy, production latency, or proven cost savings.

## Automated verification and next validation

51 tests passed with the project's Python environment. Coverage includes parsing,
region recovery, targeted image requests, response validation, safe network error
classification, retry/history limits, SQLite persistence, manual editing, and
save notifications through actual Streamlit navigation. External API responses
in automated tests are simulated; the two live checks above are separate evidence.

Next: collect a small independent sample during ordinary use, retain field-level
human references, and record core-field agreement, request proportion, latency
and returned token usage. Authentication/cloud sync remain outside this local MVP.
Existing 1.0 detector metrics and the old demo animation are preserved. The old
animation is not presented as evidence of the latest multimodal features.
