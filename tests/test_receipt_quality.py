import unittest
from src.receipt_quality import assess_receipt, review_plan
from src.receipt_evaluation import evaluate


def baseline(**changes):
    return dict(dict(store_name_candidate='LAWSON', store_name_raw='LAWSON',
                     date_candidate='2026-06-23', date_raw='2026年6月23日',
                     total_amount_candidate='180', total_amount_raw='合計 ¥180',
                     items_text='牛乳\n¥180'), **changes)


class QualityTests(unittest.TestCase):
    def codes(self, raw, **kwargs):
        return {r['code'] for r in assess_receipt(raw, **kwargs)['reasons']}

    def test_normal_receipt_and_payment_not_conflict(self):
        for raw in (baseline(), baseline(total_amount_raw='合計 ¥180\nお預り ¥1000\nお釣り ¥820')):
            self.assertEqual(assess_receipt(raw)['route'], 'standard')

    def test_missing_invalid_and_conflicting_fields(self):
        raw = baseline(store_name_candidate='', date_candidate='2026-02-30',
                       total_amount_raw='合計 ¥180\n合計 ¥280')
        codes = self.codes(raw)
        self.assertTrue({'missing_store_name', 'invalid_date', 'amount_conflict'} <= codes)
        self.assertIn('invalid_amount', self.codes(baseline(total_amount_candidate='18O')))
        self.assertIn('region_missing_date', self.codes(baseline(), detected_fields=['store_name','total_amount','items_area']))

    def test_items_ambiguity_tax_advisory_and_retake(self):
        self.assertIn('items_unpaired', self.codes(baseline(items_text='牛乳\nパン\n¥80\n¥100')))
        gate = assess_receipt(baseline(total_amount_candidate='198', total_amount_raw='合計 ¥198',
                                       items_text='牛乳\n¥180\n消費税 ¥18'))
        self.assertEqual(gate['route'], 'standard')
        self.assertEqual(gate['advisories'][0]['code'], 'amount_difference')
        self.assertEqual(assess_receipt(baseline(), image_problem='反光遮挡金额')['route'], 'retake')

    def test_plan_is_not_an_external_call(self):
        raw = baseline(date_candidate='')
        plan = review_plan(raw, assess_receipt(raw))
        self.assertEqual(plan['status'], 'not_called')
        self.assertEqual(plan['max_automatic_attempts'], 1)
        self.assertIn('original_image', plan['required_evidence'])
        self.assertIn('date', plan['target_fields'])

    def test_no_truth_means_no_accuracy_and_misses_are_visible(self):
        pending = dict(image_id='a', receipt_group='g1', split='test', reviewed=False, truth={})
        self.assertIsNone(evaluate([pending], {'a': baseline()})['field_exact_match']['date'])
        # A valid-looking wrong amount with a matching item total must remain visible as a missed error.
        truth = dict(store_name='LAWSON', date='2026-06-23', total_amount='190')
        reviewed = dict(pending, reviewed=True, truth=truth)
        result = evaluate([reviewed], {'a': baseline()})
        self.assertEqual(result['missed_core_error_images'], 1)
        self.assertEqual(result['core_error_routing_recall'], 0)
        missing = evaluate([reviewed], {})
        self.assertEqual(missing['evaluated_images'], 0)
        self.assertEqual(missing['missing_predictions'], ['a'])


if __name__ == '__main__':
    unittest.main()
