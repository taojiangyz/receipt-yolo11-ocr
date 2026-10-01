import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from src.receipt_items import parse_items, normalize_items, reconcile
from src.receipt_store import ReceiptStore, candidates, export_items_csv


class ItemParsingTests(unittest.TestCase):
    def test_alternating_and_inline(self):
        result = parse_items('牛乳\n¥180軽\nパン ￥４３０\nチーズ\n188')
        self.assertEqual(result['rows'], [dict(name='牛乳', line_total='180'),
                                         dict(name='パン', line_total='430'),
                                         dict(name='チーズ', line_total='188')])
        self.assertEqual(result['unmatched'], [])

    def test_grouped_names_prices_are_not_guessed(self):
        result = parse_items('ザバスチョコレート20\n麦茶1L\n¥239軽\n¥160軽')
        self.assertEqual(result['rows'], [])
        self.assertEqual(len(result['unmatched']), 4)
        self.assertEqual(parse_items('牛乳\n¥180\n¥430\nパン')['rows'], [])

    def test_discounts_tax_quantity_and_missing_price(self):
        result = parse_items('牛乳\n¥180\n消費税 ¥18\n値引 -20\n2点\n合計 ¥178\nパン')
        self.assertEqual(result['rows'], [dict(name='牛乳', line_total='180')])
        self.assertEqual(len(result['unmatched']), 5)

    def test_comparison_is_advisory(self):
        rows = [dict(name='牛乳', line_total='180'), dict(name='パン', line_total='430')]
        self.assertEqual(reconcile(rows, '610')['state'], 'match')
        self.assertEqual(reconcile(rows, '620')['difference'], 10)
        self.assertEqual(reconcile([], '620')['state'], 'unavailable')
        with self.assertRaises(ValueError):
            normalize_items([dict(name='牛乳', line_total='-10')])
        self.assertEqual(normalize_items([dict(name='サンプル', line_total=0)])[0]['line_total'], '0')

    def test_legacy_record_upgrade_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ReceiptStore(Path(tmp) / 'db.sqlite3')
            raw = dict(items_text='牛乳\n¥180', total_amount_candidate='180')
            values = candidates(raw)
            rid = store.save(values, payload=b'photo', filename='sample.png', raw=raw)
            # Reproduce the JSON layout written by the previous version.
            values.pop('line_items')
            with store.connection() as db:
                db.execute('UPDATE receipts SET values_json=? WHERE id=?', (json.dumps(values), rid))
            record = store.get(rid)
            self.assertNotIn('line_items', record['values'])
            updated = dict(record['values'], line_items=[dict(name='牛乳', line_total='180')])
            store.save(updated, receipt_id=rid, revision=1)
            self.assertEqual(store.get(rid)['raw'], raw)
            self.assertEqual(store.get(rid)['values']['line_items'], updated['line_items'])
            self.assertNotIn('line_items', store.history(rid)[0]['before'])
            exported = list(csv.DictReader(io.StringIO(export_items_csv(store.list()).decode('utf-8-sig'))))
            self.assertEqual(exported[0]['name'], '牛乳')
            self.assertEqual(exported[0]['receipt_id'], rid)
            self.assertEqual(exported[0]['status'], '待核对')
            updated['line_items'][0]['name'] = '=1+1'
            store.save(updated, receipt_id=rid, revision=2)
            exported = list(csv.DictReader(io.StringIO(export_items_csv(store.list()).decode('utf-8-sig'))))
            self.assertEqual(exported[0]['name'], "'=1+1")


if __name__ == '__main__':
    unittest.main()
