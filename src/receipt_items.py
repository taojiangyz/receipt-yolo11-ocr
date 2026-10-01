"""Conservative OCR line pairing. All rows are candidates requiring human review."""
import re
import unicodedata

# Footer/payment/tax/discount rows must not be silently treated as purchases.
SPECIAL = re.compile(r"合計|小計|総計|税|お預|釣|現金|クレジット|支払|値引|割引|ポイント|点数|点買|点購入")
MONEY = re.compile(r"(?:[¥￥]([0-9]{1,9})|([0-9]{1,9})円?|([0-9]{1,9}))[軽*※]?")


def parse_items(text):
    tokens = []
    for original in text.splitlines():
        if not original.strip():
            continue
        line = unicodedata.normalize('NFKC', original).strip().replace(',', '')
        if SPECIAL.search(line) or re.search(r'[-−△▲]', line):
            tokens.append(('unknown', original))
            continue
        inline = re.fullmatch(r'(.+?)\s*[¥￥]([0-9]{1,9})[軽*※]?', line)
        if inline:
            tokens.append(('row', {'name': inline[1].strip(), 'line_total': str(int(inline[2]))}))
            continue
        price = MONEY.fullmatch(line.replace(' ', ''))
        if price:
            tokens.append(('price', str(int(next(x for x in price.groups() if x is not None)))))
        elif re.search(r'[A-Za-zぁ-んァ-ヶ一-龯]', line) and not re.fullmatch(r'[0-9]+(?:個|点|本|袋|ml|mL|L)', line):
            tokens.append(('name', original.strip()))
        else:
            tokens.append(('unknown', original))
    rows, unmatched = [], []
    i = 0
    while i < len(tokens):
        kind, value = tokens[i]
        if kind == 'row':
            rows.append(value)
            i += 1
        elif kind == 'name':
            names = []
            while i < len(tokens) and tokens[i][0] == 'name':
                names.append(tokens[i][1]); i += 1
            prices = []
            while i < len(tokens) and tokens[i][0] == 'price':
                prices.append(tokens[i][1]); i += 1
            if len(names) == len(prices) == 1:
                rows.append({'name': names[0], 'line_total': prices[0]})
            else:
                unmatched.extend(names + prices)
        else:
            unmatched.append(value)
            i += 1
    return {'rows': rows, 'unmatched': unmatched}


def normalize_items(rows):
    if not isinstance(rows, list):
        raise ValueError('商品明细格式无效')
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('商品明细行格式无效')
        name = str(row.get('name') or '').strip()
        amount = str(row.get('line_total') if row.get('line_total') is not None else '').strip()
        if not name and not amount:
            continue
        if not name or not re.fullmatch(r'[0-9]{1,9}', amount):
            raise ValueError('每行商品须填写名称和非负整数行金额；不确定的行可删除，保留原文待核对')
        result.append({'name': name, 'line_total': str(int(amount))})
    return result


def reconcile(rows, total):
    """Compare entered line totals, without asserting tax/discount completeness."""
    rows = normalize_items(rows)
    if not rows or not re.fullmatch(r'[0-9]{1,9}', str(total)):
        return {'state': 'unavailable', 'message': '填写商品行和合计金额后可比较。'}
    subtotal = sum(int(row['line_total']) for row in rows)
    difference = int(total) - subtotal
    return {
        'state': 'match' if difference == 0 else 'difference',
        'subtotal': subtotal, 'difference': difference,
        'message': (f'已录入商品行合计 ¥{subtotal}，与票据合计一致；仍需核对商品对应关系。'
                    if difference == 0 else
                    f'已录入商品行合计 ¥{subtotal}，票据合计 ¥{total}，差额 ¥{difference}。请检查漏项、税额、折扣或识别错误。'),
    }
