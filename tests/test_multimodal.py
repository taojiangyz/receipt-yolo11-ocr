import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from PIL import Image
from src.receipt_multimodal import VisionConfig, recognize, parse_suggestions, build_request
from src.receipt_store import ReceiptStore, candidates

RAW = dict(store_name_candidate='FamilyMart',date_candidate='2026-10-03',
           total_amount_candidate='',total_amount_raw='1 3 5',items_text='')
CONFIG = VisionConfig('https://vision.example/v1/chat/completions','vision-model','private-test-key',2,4,'USD')

class MultimodalTests(unittest.TestCase):
    def test_items_missing_alone_never_calls_api(self):
        transport=Mock();raw=dict(RAW,total_amount_candidate='135',total_amount_raw='¥135')
        result=recognize(raw,Image.new('RGB',(10,10)),{},CONFIG,transport=transport)
        self.assertEqual(result['status'],'not_needed');transport.assert_not_called()

    def test_image_request_has_only_targeted_crops_and_ocr_context(self):
        image=Image.new('RGB',(20,30))
        body=build_request(RAW,image,{'total_amount':{'image':image},'items_area':{'image':image}},CONFIG,['total_amount'])
        content=body['messages'][0]['content']
        self.assertEqual(sum(p['type']=='image_url' for p in content),2)
        self.assertTrue(content[2]['image_url']['url'].startswith('data:image/jpeg;base64,'))
        self.assertNotIn('private-test-key',json.dumps(body))
        self.assertIn('"total_amount"',content[0]['text'])
        self.assertNotIn('"items_text"',content[0]['text'])
        decoded=Image.open(io.BytesIO(__import__('base64').b64decode(content[2]['image_url']['url'].split(',')[1])))
        self.assertEqual(decoded.size,(20,30))

    def test_suggestions_usage_and_cost_do_not_mutate_ocr(self):
        content=json.dumps({'fields':{'total_amount':{'value':'135','reason':'合計行 ¥135'},'date':{'value':'1999-01-01','reason':'unsolicited'}}})
        response={'id':'request-1','choices':[{'message':{'content':content}}],
                  'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}}
        transport=Mock(return_value=response);raw=dict(RAW)
        result=recognize(raw,Image.new('RGB',(10,10)),{},CONFIG,transport=transport)
        transport.assert_called_once();self.assertEqual(result['status'],'completed')
        self.assertEqual(set(result['suggestions']),{'total_amount'})
        self.assertFalse(result['suggestions']['total_amount']['verified'])
        self.assertEqual(raw,RAW)
        self.assertAlmostEqual(result['cost_estimate']['amount'],.0004)
        self.assertNotIn('private-test-key',json.dumps(result))

    def test_unknown_cost_and_invalid_model_output(self):
        config=VisionConfig(CONFIG.endpoint,CONFIG.model,CONFIG.api_key)
        for content in ['not json',json.dumps({'fields':{'total_amount':{'value':129,'reason':'number'}}}),
                        json.dumps({'fields':{'total_amount':{'value':'1,29','reason':'fragment'}}})]:
            with self.subTest(content=content):
                result=recognize(RAW,Image.new('RGB',(10,10)),{},config,
                   transport=lambda *_:{'choices':[{'message':{'content':content}}]})
                self.assertEqual(result['suggestions'],{})
                self.assertIsNone(result['cost_estimate'])
        suggestions,rejected=parse_suggestions('```json\n{"fields":{"date":{"value":"2026-02-30","reason":""}}}\n```',['date'])
        self.assertEqual(suggestions,{});self.assertEqual(rejected,['date'])

    def test_http_failure_does_not_leak_secret_or_retry(self):
        transport=Mock(side_effect=HTTPError(CONFIG.endpoint,401,'private-test-key',{},None))
        result=recognize(RAW,Image.new('RGB',(10,10)),{},CONFIG,transport=transport)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['http_status'],401)
        transport.assert_called_once();self.assertNotIn('private-test-key',json.dumps(result))

    def test_config_requires_image_api_explicitly_and_hides_key(self):
        with patch.dict(os.environ,{'RECEIPT_VISION_ENDPOINT':CONFIG.endpoint,'RECEIPT_VISION_MODEL':'v',
                                   'RECEIPT_VISION_API_KEY':'secret'},clear=True):
            config=VisionConfig.from_env();self.assertNotIn('secret',repr(config))
            for endpoint in ['http://vision.example/v1','https://user:secret@vision.example/v1','https://vision.example/v1?key=secret']:
                with patch.dict(os.environ,{'RECEIPT_VISION_ENDPOINT':endpoint}):
                    with self.assertRaises(ValueError):VisionConfig.from_env()

    def test_durable_attempt_survives_reopen_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'receipts.sqlite3';store=ReceiptStore(path);payload=b'photo'
            rid=store.save(candidates(RAW),payload=payload,filename='photo.png',raw=RAW)
            self.assertTrue(store.claim_multimodal_attempt(payload,{'model':'v'}))
            reopened=ReceiptStore(path)
            self.assertFalse(reopened.claim_multimodal_attempt(payload,{'model':'v2'}))
            self.assertEqual(reopened.get_multimodal_attempt(payload)['status'],'started')
            result={'status':'completed','suggestions':{'total_amount':{'value':'135','verified':False}}}
            reopened.finish_multimodal_attempt(payload,result)
            self.assertEqual(store.get_multimodal_attempt(payload),result)
            self.assertEqual(store.get(rid)['raw'],RAW)
            self.assertEqual(len(store.history(rid)),1)
            self.assertEqual(store.get(rid)['values']['amount'],'')

if __name__=='__main__':unittest.main()
