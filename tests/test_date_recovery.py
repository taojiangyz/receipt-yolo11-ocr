import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from src.receipt_fields import extract_date
from src.receipt_pipeline import recover_date


class DateRecoveryTests(unittest.TestCase):
    def test_separators_and_digit_boundaries(self):
        for value in ['2026）6/16(火)2', '2026）6（23（X）2', '２０２６年６月２３日', '2026.6.23']:
            self.assertTrue(extract_date(value))
        for value in ['26年6月19日', '020年6月19日', '202616116', '2026/16(火)',
                      '12026/6/23', '2026/6/231', '2026/2/30', '2026/6/23\n2026/6/24']:
            self.assertEqual(extract_date(value), '')
        self.assertEqual(extract_date('2026/6/23\n2026年6月23日'), '2026-06-23')

    def test_local_retry_and_failure_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            crop = {'image': Image.new('RGB', (300, 50), 'white')}
            with patch('src.receipt_pipeline.run_ocr_on_image', return_value='2026年6月19日') as run:
                result = recover_date('26年6月19日', crop, Path(tmp), object())
                self.assertEqual(result['candidate'], '2026-06-19')
                self.assertEqual(run.call_count, 1)
                self.assertIsNone(recover_date('2026/6/19', crop, Path(tmp), object()))
                self.assertIsNone(recover_date('', None, Path(tmp), object()))
                self.assertIsNone(recover_date('2026/6/19\n2026/6/20', crop, Path(tmp), object()))
                self.assertEqual(run.call_count, 1)
            with patch('src.receipt_pipeline.run_ocr_on_image', side_effect=RuntimeError('OCR failure')):
                result = recover_date('', crop, Path(tmp), object())
                self.assertEqual(result['candidate'], '')
                self.assertEqual(result['error_type'], 'RuntimeError')


if __name__ == '__main__':
    unittest.main()
