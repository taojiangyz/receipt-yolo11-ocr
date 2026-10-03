import os
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

class SaveNotificationTests(unittest.TestCase):
    def test_saved_notification_through_real_navigation(self):
        for state, expected in [('difference','warning'),('match','info')]:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'RECEIPT_LIBRARY_DIR':tmp}):
                app=AppTest.from_file('streamlit_app.py')
                app.session_state['receipt_saved']=True
                app.session_state['receipt_comparison']={'state':state,'message':'保存后金额核对结果'}
                with patch('src.receipt_pipeline.analyze_image',side_effect=AssertionError('must not repeat OCR')):
                    app.run()
                    self.assertFalse(app.exception)
                    self.assertTrue(app.success)
                    self.assertTrue(any(x.value=='保存后金额核对结果' for x in getattr(app,expected)))
                    app.run()
                    self.assertFalse(app.exception)
                    self.assertFalse(app.success)

if __name__=='__main__':unittest.main()
