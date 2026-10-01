import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from streamlit.testing.v1 import AppTest
from src.receipt_batch import enqueue, process, save_pending, MAX_FILE_BYTES
from src.receipt_store import ReceiptStore, candidates


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ReceiptStore(Path(self.tmp.name) / 'receipts.sqlite3')
        self.queue = {}

    def analyze(self, payload, filename):
        return dict(digest=hashlib.sha256(payload).hexdigest(), filename=filename, payload=payload,
                    result={'store_name_candidate': 'LAWSON', 'date_candidate': '2026-06-23',
                            'total_amount_candidate': '180', 'items_text': '牛乳\n¥180'})

    def test_content_dedup_and_saved_skip(self):
        saved = self.analyze(b'saved', 'saved.png')
        self.store.save(candidates(saved['result']), payload=b'saved', filename='saved.png', raw=saved['result'])
        self.assertEqual(enqueue(self.queue, [('a.png', b'a'), ('copy.png', b'a'), ('saved.png', b'saved')], self.store), 2)
        calls = []
        def analyze(payload, filename):
            calls.append(payload)
            return self.analyze(payload, filename)
        process(self.queue, analyze, self.store)
        process(self.queue, analyze, self.store)
        self.assertEqual(calls, [b'a'])
        self.assertEqual(save_pending(self.queue, self.store), 1)
        self.assertEqual(save_pending(self.queue, self.store), 0)
        self.assertEqual(len(self.store.list()), 2)
        self.assertTrue(all(row['status'] == '待核对' for row in self.store.list()))

    def test_failed_file_does_not_stop_batch_or_repeat_success(self):
        enqueue(self.queue, [('a.png', b'a'), ('bad.png', b'b'), ('c.png', b'c')], self.store)
        calls = []
        def analyze(payload, filename):
            calls.append(payload)
            if payload == b'b':
                raise ValueError('bad image')
            return self.analyze(payload, filename)
        process(self.queue, analyze, self.store)
        self.assertEqual(calls, [b'a', b'b', b'c'])
        failed = hashlib.sha256(b'b').hexdigest()
        self.assertEqual(self.queue[failed]['status'], 'failed')
        process(self.queue, self.analyze, self.store, retry_id=failed)
        self.assertEqual(self.queue[failed]['attempts'], 2)
        self.assertEqual([e['attempts'] for e in self.queue.values()], [1, 2, 1])
        self.assertEqual(save_pending(self.queue, self.store), 3)

    def test_limits_are_atomic(self):
        with self.assertRaises(ValueError):
            enqueue(self.queue, [('big.png', b'x' * (MAX_FILE_BYTES + 1))], self.store)
        with self.assertRaises(ValueError):
            enqueue(self.queue, [(f'{n}.png', str(n).encode()) for n in range(11)], self.store)
        self.assertEqual(self.queue, {})

    def test_storage_failure_keeps_recognition_for_retry(self):
        enqueue(self.queue, [('a.png', b'a')], self.store)
        process(self.queue, self.analyze, self.store)
        with patch.object(self.store, 'save', side_effect=OSError('disk unavailable')):
            self.assertEqual(save_pending(self.queue, self.store), 0)
        entry = next(iter(self.queue.values()))
        self.assertEqual(entry['status'], 'ready')
        self.assertIn('保存失败', entry['error'])
        self.assertEqual(save_pending(self.queue, self.store), 1)
        self.assertEqual(entry['attempts'], 1)

    def test_batch_ui_save_pending_and_history(self):
        image = Image.new('RGB', (20, 40), 'white')
        buf = io.BytesIO(); image.save(buf, format='PNG')
        payload = buf.getvalue()
        enqueue(self.queue, [('sample.png', payload)], self.store)
        def analyze(payload, filename):
            return dict(self.analyze(payload, filename), image=image)
        process(self.queue, analyze, self.store)
        with patch.dict(os.environ, {'RECEIPT_LIBRARY_DIR': self.tmp.name}):
            app = AppTest.from_file('pages/manager.py')
            app.session_state['receipt_batch'] = self.queue
            app.run()
            app.radio[0].set_value('批量处理').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input[0].value, 'LAWSON')
            next(b for b in app.button if b.label == '将成功结果保存为待核对').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(self.store.list()[0]['status'], '待核对')
            self.assertTrue(all(e['status'] == 'saved' for e in self.queue.values()))
            app.radio[0].set_value('历史票据').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input[1].value, 'LAWSON')


if __name__ == '__main__':
    unittest.main()
