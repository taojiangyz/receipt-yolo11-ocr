import io
import os
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from streamlit.testing.v1 import AppTest
from src.receipt_store import ReceiptStore


class ManagerUITests(unittest.TestCase):
    def test_review_save_edit_and_reopen_without_inference(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'RECEIPT_LIBRARY_DIR': tmp}):
            image = Image.new('RGB', (30, 60), 'white')
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            app = AppTest.from_file('pages/manager.py')
            app.session_state['receipt_analysis'] = dict(
                digest='fixture', filename='sample.png', payload=buf.getvalue(), image=image,
                result=dict(store_name_candidate='LAWSON', date_candidate='2026-06-23',
                            total_amount_candidate='610', items_text='牛乳\n¥610'))
            with patch('src.receipt_pipeline.analyze_image', side_effect=AssertionError('Unexpected inference')):
                app.run()
                self.assertFalse(app.exception)
                app.text_input[2].set_value('620')
                app.selectbox[0].set_value('已核对')
                next(b for b in app.button if b.label == '保存票据').click().run()
                self.assertFalse(app.exception)
                self.assertTrue(app.success)
                app.radio[0].set_value('历史票据').run()
                self.assertEqual(app.text_input[3].value, '620')
                app.text_input[3].set_value('630')
                next(b for b in app.button if b.label == '保存票据').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.text_input[3].value, '630')
                from pathlib import Path
                store = ReceiptStore(Path(tmp) / 'receipts.sqlite3')
                row = store.list()[0]
                self.assertEqual(row['amount'], '630')
                self.assertEqual(row['line_items'], [{'name': '牛乳', 'line_total': '610'}])
                self.assertTrue(any('差额' in x.value for x in app.warning))
                self.assertEqual(store.get(row['id'])['raw']['total_amount_candidate'], '610')
                self.assertEqual(len(store.history(row['id'])), 2)
                reopened = AppTest.from_file('pages/manager.py').run()
                reopened.radio[0].set_value('历史票据').run()
                self.assertEqual(reopened.text_input[3].value, '630')
                self.assertFalse(reopened.exception)

    def test_item_table_edit_is_saved_and_audited(self):
        from pathlib import Path
        from src.receipt_store import candidates
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'RECEIPT_LIBRARY_DIR': tmp}):
            image = io.BytesIO()
            Image.new('RGB', (10, 10)).save(image, format='PNG')
            store = ReceiptStore(Path(tmp) / 'receipts.sqlite3')
            raw = {'items_text': '牛乳\n¥180', 'total_amount_candidate': '180'}
            rid = store.save(candidates(raw), payload=image.getvalue(), filename='test.png', raw=raw)
            app = AppTest.from_file('pages/manager.py').run()
            app.radio[0].set_value('历史票据').run()
            app.session_state[f'edit_{rid}_1_items'] = {
                'edited_rows': {0: {'line_total': '190'}}, 'added_rows': [], 'deleted_rows': []}
            next(b for b in app.button if b.label == '保存票据').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(store.get(rid)['values']['line_items'][0]['line_total'], '190')
            self.assertEqual(store.history(rid)[0]['before']['line_items'][0]['line_total'], '180')
            self.assertEqual(store.get(rid)['raw'], raw)


if __name__ == '__main__':
    unittest.main()
