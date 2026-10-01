"""Local annotation preparation and held-out core-field / routing evaluation."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from src.receipt_quality import assess_receipt, RULES_VERSION

CORE_FIELDS = ('store_name', 'date', 'total_amount')


def make_manifest(images_dir):
    records = []
    for path in sorted(Path(images_dir).iterdir()):
        if path.suffix.lower() not in ('.jpg', '.jpeg', '.png'):
            continue
        match = re.fullmatch(r'(.+)_([abc])', path.stem)
        if not match:
            raise ValueError(f'无法确定实体小票分组：{path.name}')
        records.append(dict(image_id=path.stem, receipt_group=match[1],
                            image_path=str(path.resolve()), split='test',
                            reviewed=False, reviewer='',
                            truth={field: None for field in CORE_FIELDS}, notes=''))
    if not records:
        raise ValueError('没有找到图片')
    return records


def load_manifest(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    ids, group_splits = set(), {}
    for row in rows:
        if row['image_id'] in ids:
            raise ValueError('重复的 image_id')
        ids.add(row['image_id'])
        group = row['receipt_group']
        if group in group_splits and group_splits[group] != row['split']:
            raise ValueError('同一实体小票不能出现在多个划分中')
        group_splits[group] = row['split']
        if row.get('reviewed') and (not row.get('reviewer') or any(row.get('truth', {}).get(k) in (None, '') for k in CORE_FIELDS)):
            raise ValueError('标记已审核前须填写审核人和三个核心字段；无法看清的样本保持未审核并写明原因')
    return rows


def evaluate(manifest, predictions):
    reviewed = [row for row in manifest if row.get('reviewed') and row['split'] == 'test']
    evaluated = [row for row in reviewed if row['image_id'] in predictions]
    counts = {field: 0 for field in CORE_FIELDS}
    erroneous = routed_errors = routed = clean_routed = exact_receipts = 0
    for row in evaluated:
        raw = predictions[row['image_id']]
        errors = []
        for field in CORE_FIELDS:
            correct = str(raw.get(field + '_candidate', '')).strip() == str(row['truth'][field]).strip()
            counts[field] += int(correct)
            errors.append(not correct)
        gate = assess_receipt(raw, detected_fields=raw.get('evidence', {}).get('detected_fields'))
        triggered = gate['needs_multimodal']
        routed += triggered
        erroneous += any(errors)
        routed_errors += any(errors) and triggered
        clean_routed += not any(errors) and triggered
        exact_receipts += not any(errors)
    n = len(evaluated)
    return dict(rules_version=RULES_VERSION, manifest_images=len(manifest), reviewed_test_images=len(reviewed),
                evaluated_images=n, evaluated_receipt_groups=len({r['receipt_group'] for r in evaluated}),
                missing_predictions=[r['image_id'] for r in reviewed if r['image_id'] not in predictions],
                field_exact_match={k: counts[k] / n if n else None for k in CORE_FIELDS},
                all_core_fields_exact=exact_receipts / n if n else None,
                routed_images=routed, images_with_core_errors=erroneous,
                core_error_routing_recall=routed_errors / erroneous if erroneous else None,
                missed_core_error_images=erroneous - routed_errors,
                routed_without_core_error=clean_routed,
                note='未审核样本不计分；多视角图片并非独立实体小票。核心字段无误的触发仍可能来自商品明细问题，不能直接判为误触发。')


def prediction_files(directory):
    return {path.stem: json.loads(path.read_text()) for path in sorted(Path(directory).glob('*.json'))}


def inventory(predictions):
    routes, reasons = Counter(), Counter()
    for raw in predictions.values():
        gate = assess_receipt(raw, detected_fields=raw.get('evidence', {}).get('detected_fields'))
        routes[gate['route']] += 1
        reasons.update({r['code'] for r in gate['reasons']})
    return dict(rules_version=RULES_VERSION, prediction_files=len(predictions), routes=dict(routes),
                reason_counts=dict(reasons), accuracy_measured=False,
                note='仅统计历史OCR触发覆盖情况，不是准确率，也不代表当前模型输出。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--images', required=True)
    init.add_argument('--output', required=True)
    inv = sub.add_parser('inventory')
    inv.add_argument('--predictions', required=True)
    ev = sub.add_parser('evaluate')
    ev.add_argument('--manifest', required=True)
    ev.add_argument('--predictions', required=True)
    args = parser.parse_args()
    if args.command == 'init':
        rows = make_manifest(args.images)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as file:
            file.write(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        result = dict(images=len(rows), receipt_groups=len({r['receipt_group'] for r in rows}),
                      output=str(output), reviewed=0)
    elif args.command == 'inventory':
        result = inventory(prediction_files(args.predictions))
    else:
        result = evaluate(load_manifest(args.manifest), prediction_files(args.predictions))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
