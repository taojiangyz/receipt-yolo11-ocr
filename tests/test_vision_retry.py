import io
import os
import socket
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError
from PIL import Image
from streamlit.testing.v1 import AppTest
from src.receipt_multimodal import VisionConfig, recognize, network_failure
from src.receipt_store import ReceiptStore

class VisionRetryTests(unittest.TestCase):
    def test_network_reason_is_specific_and_redacted(self):
        for reason,code in [(TimeoutError('secret timed out'),'network_timeout'),
                            (socket.gaierror('secret'),'dns_resolution_failed'),
                            (ssl.SSLCertVerificationError('secret'),'certificate_verification_failed')]:
            with self.subTest(code=code):
                transport=Mock(side_effect=URLError(reason))
                result=recognize({'total_amount_candidate':''},Image.new('RGB',(10,10)),{},
                    VisionConfig('https://example.test/v1','vision','secret'),transport=transport)
                self.assertEqual(result['network_reason'],code)
                self.assertNotIn('secret',str(result))
                transport.assert_called_once()

    def test_retry_claim_keeps_history_and_enforces_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ReceiptStore(Path(tmp)/'test.db');payload=b'photo'
            self.assertTrue(store.claim_multimodal_attempt(payload,{}))
            self.assertFalse(store.claim_multimodal_attempt(payload,{},retry=True))
            failure={'status':'failed','error_type':'URLError','attempts':1}
            store.finish_multimodal_attempt(payload,failure)
            for number in [2,3]:
                self.assertTrue(store.claim_multimodal_attempt(payload,{},retry=True))
                self.assertFalse(store.claim_multimodal_attempt(payload,{},retry=True))
                store.finish_multimodal_attempt(payload,failure)
                current=store.get_multimodal_attempt(payload)
                self.assertEqual(current['attempt_number'],number)
                self.assertEqual(len(current['history']),number-1)
                self.assertEqual(current['history'][0]['error_type'],'URLError')
            self.assertFalse(store.claim_multimodal_attempt(payload,{},retry=True))

    def test_completed_result_cannot_be_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ReceiptStore(Path(tmp)/'test.db');payload=b'photo'
            store.claim_multimodal_attempt(payload,{})
            store.finish_multimodal_attempt(payload,{'status':'completed'})
            self.assertFalse(store.claim_multimodal_attempt(payload,{},retry=True))

    def test_ui_explicit_retry_does_not_repeat_on_rerun(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{
            'RECEIPT_LIBRARY_DIR':tmp,'RECEIPT_VISION_ENDPOINT':'https://example.test/v1/chat/completions',
            'RECEIPT_VISION_MODEL':'vision','RECEIPT_VISION_API_KEY':'test-key'}):
            image=Image.new('RGB',(30,60));buf=io.BytesIO();image.save(buf,format='PNG');payload=buf.getvalue()
            store=ReceiptStore(Path(tmp)/'receipts.sqlite3')
            store.claim_multimodal_attempt(payload,{})
            store.finish_multimodal_attempt(payload,{'status':'failed','error_type':'URLError','attempts':1})
            app=AppTest.from_file('pages/manager.py')
            app.session_state['receipt_analysis']=dict(digest=hashlib.sha256(payload).hexdigest(),payload=payload,
                image=image,filename='test.png',result={'total_amount_candidate':''})
            with patch('src.receipt_multimodal_view.recognize',return_value={'status':'completed','suggestions':{}}) as call:
                app.run();self.assertFalse(app.exception);call.assert_not_called()
                next(b for b in app.button if b.label.startswith('重试 AI')).click().run()
                self.assertFalse(app.exception);call.assert_called_once()
                app.run();call.assert_called_once()
                current=store.get_multimodal_attempt(payload)
                self.assertEqual(current['attempt_number'],2)
                self.assertEqual(current['history'][0]['status'],'failed')

if __name__=='__main__':unittest.main()
