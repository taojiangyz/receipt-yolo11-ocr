import csv
import io
import tempfile
import unittest
from pathlib import Path
from src.receipt_fields import extract_amount, extract_date
from src.receipt_store import ReceiptStore, candidates, export_csv


class FieldsTests(unittest.TestCase):
    def test_total_not_cash_or_change(self):
        self.assertEqual(extract_amount('合計 ¥610\nお預り ¥1000\nお釣り ¥390'), '610')
        self.assertEqual(extract_amount('合計\n¥98'), '98')
        self.assertEqual(extract_amount('¥610\n合計'), '610')
        self.assertEqual(extract_amount('¥1234'), '1234')
        self.assertEqual(extract_amount('¥610\n¥1000'), '')
        self.assertEqual(extract_amount('お預り ¥1000'), '')

    def test_invalid_and_fullwidth_dates(self):
        self.assertEqual(extract_date('2026年2月30日'), '')
        self.assertEqual(extract_date('２０２６年６月２３日'), '2026-06-23')


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'library.sqlite3'
        self.store = ReceiptStore(self.path)
        self.raw = {'store_name_candidate': 'LAWSON', 'date_candidate': '2026-06-23',
                    'total_amount_candidate': '610', 'items_text': 'milk'}
        self.values = candidates(self.raw)

    def create(self):
        return self.store.save(self.values, payload=b'image bytes', filename='receipt.png', raw=self.raw)

    def test_reopen_edit_original_and_history(self):
        rid = self.create()
        reopened = ReceiptStore(self.path)
        rec = reopened.get(rid)
        changed = dict(rec['values'], amount='620', status='已核对')
        reopened.save(changed, receipt_id=rid, revision=rec['revision'])
        result = reopened.get(rid)
        self.assertEqual(result['image'], b'image bytes')
        self.assertEqual(result['raw'], self.raw)
        self.assertEqual(result['values']['amount'], '620')
        self.assertEqual(len(reopened.history(rid)), 2)
        self.assertEqual(reopened.history(rid)[0]['before']['amount'], '610')
        with self.assertRaises(ValueError):
            reopened.save(changed, receipt_id=rid, revision=1)
        self.assertEqual(len(reopened.history(rid)), 2)

    def test_duplicate_validation_and_filters(self):
        rid = self.create()
        self.assertEqual(self.store.find_digest(b'image bytes'), rid)
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(len(self.store.list(query='lawson', start='2026-06-01', end='2026-06-30')), 1)
        self.assertEqual(self.store.list(status='已核对'), [])
        with self.assertRaises(ValueError):
            self.store.save(dict(self.values, date='2026-02-30'), receipt_id=rid, revision=1)
        with self.assertRaises(ValueError):
            self.store.save(dict(self.values, amount='', status='已核对'), receipt_id=rid, revision=1)
        self.assertEqual(self.store.get(rid)['revision'], 1)

    def test_csv_formula_protection_and_unicode(self):
        self.create()
        rows = self.store.list()
        rows[0]['store'] = '=HYPERLINK("example")'
        rows[0]['items'] = '牛乳\nパン'
        parsed = list(csv.DictReader(io.StringIO(export_csv(rows).decode('utf-8-sig'))))
        self.assertTrue(parsed[0]['store'].startswith("'="))
        self.assertEqual(parsed[0]['items'], '牛乳\nパン')


if __name__ == '__main__':
    unittest.main()
