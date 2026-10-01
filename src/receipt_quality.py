"""Versioned, deterministic routing rules. Passing rules does not establish correctness."""
import re
import unicodedata
from datetime import date
from src.receipt_fields import extract_amount
from src.receipt_items import parse_items, reconcile, SPECIAL

RULES_VERSION = '1.0'
REQUIRED = {'store_name': '商户', 'date': '日期', 'total_amount': '合计金额'}


def assess_receipt(raw, *, detected_fields=None, image_problem=None):
    reasons, advisories = [], []
    def add(code, field, message, evidence=''):
        reasons.append(dict(code=code, field=field, message=message, evidence=evidence))
    if image_problem:
        # Explicit observation from the user/upstream checker, never a model confidence score.
        add('image_unreadable', 'image', '图片模糊、反光或截断，请先重拍或人工核对', str(image_problem))
    for field, label in REQUIRED.items():
        value = str(raw.get(field + '_candidate') or '').strip()
        text = str(raw.get(field + '_raw') or '')
        if not value:
            add('missing_' + field, field, f'{label}未能提取', text)
        elif field == 'date':
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError
                date.fromisoformat(value)
            except ValueError:
                add('invalid_date', field, '日期无效，需要对照图片核对', value)
        elif field == 'total_amount' and not re.fullmatch(r'[0-9]{1,9}', value):
            add('invalid_amount', field, '合计金额不是有效的整数日元', value)
        if detected_fields is not None and field not in detected_fields:
            add('region_missing_' + field, field, f'未检测到{label}区域，补救时应查看原图')
    text = unicodedata.normalize('NFKC', str(raw.get('total_amount_raw') or '')).replace(',', '')
    yen_values = set(re.findall(r'[¥￥]\s*([0-9]+)', text))
    parsed_total = extract_amount(text)
    candidate = str(raw.get('total_amount_candidate') or '')
    if len(yen_values) > 1 and not parsed_total:
        add('amount_conflict', 'total_amount', '存在多个金额且无法确定合计', text)
    elif parsed_total and candidate and parsed_total != candidate:
        add('amount_conflict', 'total_amount', '合计候选与原始金额提取结果不一致', text)
    # Bare amounts with repeated total labels also need conflict detection.
    labeled = set(re.findall(r'(?:合計|総計)\s*[¥￥]?\s*([0-9]+)', text))
    if len(labeled) > 1 and not any(r['code'] == 'amount_conflict' for r in reasons):
        add('amount_conflict', 'total_amount', '存在互相冲突的合计金额', text)
    items = str(raw.get('items_text') or '')
    parsed = parse_items(items)
    ambiguous = [line for line in parsed['unmatched']
                 if not SPECIAL.search(line) and not re.fullmatch(r'\s*[0-9]+(?:個|点|本|袋)\s*', line)]
    if not items.strip():
        add('items_missing', 'items_area', '商品区域没有识别文字')
    elif ambiguous:
        add('items_unpaired', 'items_area', '商品名与价格无法可靠配对', '\n'.join(ambiguous))
    if detected_fields is not None and 'items_area' not in detected_fields:
        add('region_missing_items_area', 'items_area', '未检测到商品区域，补救时应查看原图')
    comparison = reconcile(parsed['rows'], candidate)
    if comparison['state'] == 'difference':
        advisories.append(dict(code='amount_difference', message=comparison['message']))
    route = 'retake' if image_problem else ('multimodal_review' if reasons else 'standard')
    return dict(rules_version=RULES_VERSION, route=route, needs_multimodal=route == 'multimodal_review',
                reasons=reasons, advisories=advisories,
                target_fields=sorted({r['field'] for r in reasons}),
                note='通过规则不等于识别正确；这里只决定是否建议补救，尚未调用外部模型。')


def review_plan(raw, assessment):
    """Local plan for a future image-capable adapter, not a completed API request."""
    return dict(rules_version=assessment['rules_version'],
                enabled=assessment['needs_multimodal'], max_automatic_attempts=1,
                status='not_called', target_fields=assessment['target_fields'],
                reasons=assessment['reasons'],
                required_evidence=['original_image', 'available_field_crops', 'ocr_candidates'],
                ocr_candidates={k: v for k, v in raw.items() if k.endswith(('_raw', '_candidate')) or k == 'items_text'},
                instructions='对照原图与裁剪图核对指定字段。OCR仅为候选。无法确定时返回空值和原因；不可为了匹配总额编造或修改商品价格。')
