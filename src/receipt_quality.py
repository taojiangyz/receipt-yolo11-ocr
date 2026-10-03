"""Versioned, deterministic routing rules. Passing rules does not establish correctness."""
import re
import unicodedata
from datetime import date
from src.receipt_fields import extract_amount, amount_text_needs_review
from src.receipt_items import parse_items, reconcile, SPECIAL

RULES_VERSION = '1.3'
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
    if candidate and amount_text_needs_review(raw.get('total_amount_raw', '')):
        add('amount_ocr_noise', 'total_amount',
            '金额原文缺少明确合计标签且包含其他识别片段，需对照原图核对',
            str(raw.get('total_amount_raw', '')))
    amount_recovery = raw.get('amount_recovery') or {}
    if amount_recovery.get('candidate'):
        add('amount_recovery_unverified', 'total_amount',
            '金额重试产生了候选，需对照原图确认，不能仅凭整数格式接受',
            str(amount_recovery.get('raw', '')))
    recovery = raw.get('date_recovery') or {}
    if recovery.get('candidate'):
        add('date_recovery_unverified', 'date',
            '增强识别产生了日期候选，需对照原图确认，不能仅凭格式合法接受',
            str(recovery.get('raw', '')))
    items = str(raw.get('items_text') or '')
    parsed = parse_items(items)
    ambiguous = [line for line in parsed['unmatched']
                 if not SPECIAL.search(line) and not re.fullmatch(r'\s*[0-9]+(?:個|点|本|袋)\s*', line)]
    if not items.strip():
        advisories.append(dict(code='items_missing', message='商品区域没有识别文字，不触发补救'))
    elif ambiguous:
        advisories.append(dict(code='items_unpaired', message='商品名与价格无法可靠配对，仅供人工核对，不触发补救'))
    if detected_fields is not None and 'items_area' not in detected_fields:
        advisories.append(dict(code='region_missing_items_area', message='未检测到商品区域，不触发补救'))
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
                ocr_candidates={k: v for k, v in raw.items() if k in {field + suffix for field in REQUIRED for suffix in ('_raw', '_candidate')}},
                instructions='只核对店名、日期和总金额中的指定字段，不要求识别商品明细。对照原图与相关裁剪图，OCR仅为候选。无法确定时返回空值和原因，不得编造。')


def annotate_quality(raw):
    """Apply current policy to candidates without mutating stored historical reports."""
    updated = dict(raw)
    gate = assess_receipt(raw, detected_fields=raw.get('evidence', {}).get('detected_fields'))
    updated['quality_gate'] = gate
    updated['multimodal_plan'] = review_plan(raw, gate)
    return updated
