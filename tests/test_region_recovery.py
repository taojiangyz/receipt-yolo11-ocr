import tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
from PIL import Image
from src.receipt_pipeline import recover_missing_regions
from src.receipt_quality import assess_receipt

def box(cls, confidence):
    return SimpleNamespace(cls=np.array([cls]),conf=np.array([confidence]),xyxy=np.array([[10,10,90,30]]))

class RegionRecoveryTests(unittest.TestCase):
    def test_only_missing_core_fields_are_recovered(self):
        model=Mock();model.predict.return_value=[SimpleNamespace(names={0:'store_name',1:'date',2:'total_amount',3:'items_area'},boxes=[box(0,.9),box(1,.2),box(1,.16),box(2,.8),box(3,.9)])]
        original=object();crops={'store_name':original,'total_amount':original}
        with tempfile.TemporaryDirectory() as tmp:
            recovered=recover_missing_regions(model,Path('input.png'),Image.new('RGB',(100,100)),crops,Path(tmp))
            self.assertEqual(set(recovered),{'date'})
            self.assertEqual(crops['date']['confidence'],.2)
            self.assertIs(crops['store_name'],original)
            self.assertNotIn('items_area',crops)
            model.predict.assert_called_once()
            self.assertEqual(model.predict.call_args.kwargs['conf'],.15)
    def test_items_missing_does_not_trigger_detection_retry(self):
        model=Mock();crops={k:object() for k in ['store_name','date','total_amount']}
        self.assertEqual(recover_missing_regions(model,Path('input.png'),None,crops,None),{})
        model.predict.assert_not_called()
    def test_optional_failure_preserves_primary_crops(self):
        model=Mock();model.predict.side_effect=RuntimeError('failure')
        crops={'store_name':object()};original=dict(crops)
        self.assertEqual(recover_missing_regions(model,Path('input.png'),None,crops,None),{})
        self.assertEqual(crops,original)
    def test_recovered_region_needs_review_even_with_valid_candidate(self):
        raw=dict(store_name_candidate='FamilyMart',date_candidate='2026-10-03',total_amount_candidate='129',total_amount_raw='¥129',region_recovery={'date':{'threshold':.15,'detection_confidence':.2}})
        gate=assess_receipt(raw)
        self.assertEqual(gate['route'],'multimodal_review')
        self.assertEqual(gate['target_fields'],['date'])
        self.assertIn('region_recovery_unverified',{r['code'] for r in gate['reasons']})
if __name__=='__main__':unittest.main()
