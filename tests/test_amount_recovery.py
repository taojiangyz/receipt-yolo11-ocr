import unittest,tempfile
from pathlib import Path
from unittest.mock import patch,Mock,ANY
from src.receipt_fields import extract_amount
from src.receipt_pipeline import recover_amount,run_ocr_on_image
from src.receipt_quality import assess_receipt

class AmountRecoveryTests(unittest.TestCase):
    def test_complete_grouping_and_fragment_rejection(self):
        for raw,want in [('合計\n¥2.602','2602'),('合計 ¥2,602','2602'),('￥２，６０２','2602'),('¥129\n¥129','129'),('合計 ¥0','0'),('合計 ¥1,234,567','1234567')]:
            self.assertEqual(extract_amount(raw),want)
        for raw in ['合計\n¥2.\n007','¥1\n2\n9','¥1,23','¥12.50','¥2.60','¥1234567890','¥1,234.567']:
            self.assertEqual(extract_amount(raw),'',raw)
    def test_noise_and_retry_candidates_require_review(self):
        raw=dict(store_name_candidate='LAWSON',date_candidate='2026-10-03',total_amount_candidate='1185',total_amount_raw='O天\n海华\n10\n¥1185\n+')
        self.assertIn('amount_ocr_noise',{r['code'] for r in assess_receipt(raw)['reasons']})
        raw.update(total_amount_raw='¥129',total_amount_candidate='129')
        self.assertEqual(assess_receipt(raw)['route'],'standard')
        raw['amount_recovery']={'candidate':'129','raw':'¥129'}
        self.assertIn('amount_recovery_unverified',{r['code'] for r in assess_receipt(raw)['reasons']})
        self.assertEqual(assess_receipt(raw)['target_fields'],['total_amount'])
    def test_retry_once_preserves_failures_and_skips_clean_amount(self):
        crop={'path':Path('amount.jpg')}
        with patch('src.receipt_pipeline.run_ocr_on_image',return_value='合計 ¥698') as run:
            self.assertIsNone(recover_amount('合計 ¥354',crop,object()))
            self.assertIsNone(recover_amount('¥354',crop,object()))
            self.assertIsNone(recover_amount('',None,object()))
            result=recover_amount('7\n869夫',crop,object())
            self.assertEqual(result['candidate'],'698')
            run.assert_called_once_with(ANY,crop['path'],amount_retry=True)
        with patch('src.receipt_pipeline.run_ocr_on_image',side_effect=RuntimeError('failure')):
            result=recover_amount('',crop,object())
            self.assertEqual(result['candidate'],'')
            self.assertEqual(result['error_type'],'RuntimeError')
    def test_retry_disables_document_preprocessing_without_changing_other_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'amount.jpg';path.write_bytes(b'fixture')
            ocr=Mock();ocr.predict.return_value=[{'rec_texts':['合計','¥698']}]
            self.assertEqual(run_ocr_on_image(ocr,path,amount_retry=True),'合計\n¥698')
            ocr.predict.assert_called_once_with(str(path),use_doc_orientation_classify=False,use_doc_unwarping=False)
            ocr.ocr.assert_not_called()
if __name__=='__main__':unittest.main()
