import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from streamlit.testing.v1 import AppTest
from src.receipt_store import ReceiptStore

class MultimodalUITests(unittest.TestCase):
    def test_request_rerun_manual_edit_save_reopen(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{
            'RECEIPT_LIBRARY_DIR':tmp,'RECEIPT_VISION_ENDPOINT':'https://vision.example/v1/chat/completions',
            'RECEIPT_VISION_MODEL':'test-model','RECEIPT_VISION_API_KEY':'test-key'}):
            image=Image.new('RGB',(30,60),'white');buf=io.BytesIO();image.save(buf,format='PNG')
            payload=buf.getvalue();raw=dict(store_name_candidate='FamilyMart',date_candidate='',
                                          total_amount_candidate='129',total_amount_raw='¥129')
            result=dict(status='completed',attempts=1,suggestions={'date':{'value':'2026-10-03','reason':'印字日期','verified':False}})
            app=AppTest.from_file('pages/manager.py')
            app.session_state['receipt_analysis']=dict(digest=hashlib.sha256(payload).hexdigest(),
                filename='test.png',payload=payload,image=image,result=raw)
            with patch('src.receipt_multimodal_view.recognize',return_value=result) as call:
                app.run();self.assertFalse(app.exception)
                next(b for b in app.button if b.label=='让 AI 辅助核对').click().run()
                self.assertFalse(app.exception);call.assert_called_once()
                app.run();call.assert_called_once()
                date_input=next(t for t in app.text_input if t.label.startswith('日期'))
                self.assertEqual(date_input.value,'')
                date_input.set_value('2026-10-03')
                next(b for b in app.button if b.label=='保存票据').click().run()
                self.assertFalse(app.exception)
                app.radio[0].set_value('历史票据').run()
                self.assertFalse(app.exception);call.assert_called_once()
                store=ReceiptStore(Path(tmp)/'receipts.sqlite3');rid=store.list()[0]['id']
                self.assertEqual(store.get(rid)['raw']['date_candidate'],'')
                self.assertEqual(store.get(rid)['values']['date'],'2026-10-03')
                self.assertEqual(store.get_multimodal_attempt(payload),result)
                self.assertTrue(any('2026-10-03' in m.value for m in app.markdown))

if __name__=='__main__':unittest.main()
