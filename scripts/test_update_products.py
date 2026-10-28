import json
from pathlib import Path
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from datetime import datetime,timezone
from update_products import ROOT,refresh,validate

class PublicProductSnapshots(unittest.TestCase):
    def test_rejects_negative_boolean_and_missing_counters(self):
        valid={key:{'value':10} for key in ('users','problems','competitions','attempts')}
        for bad in (-1,True,'10',float('nan')):
            with self.subTest(value=bad):
                payload={**valid,'users':{'value':bad}}
                with self.assertRaises(ValueError):validate(payload)
        with self.assertRaises(KeyError):validate({})

    def test_fetch_failure_preserves_both_cards_and_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'assets').mkdir();(root/'data').mkdir()
            for theme in ('dark','light'):shutil.copy2(ROOT/'assets'/f'kep-overview-{theme}.svg',root/'assets'/f'kep-overview-{theme}.svg')
            (root/'data/products.json').write_text('{"last":"verified"}',encoding='utf-8')
            before={path:path.read_bytes() for path in root.rglob('*') if path.is_file()}
            def unavailable():raise OSError('offline')
            log=StringIO()
            with redirect_stdout(log):self.assertFalse(refresh(root,unavailable))
            self.assertIn('KEP snapshot retained',log.getvalue())
            self.assertEqual(before,{path:path.read_bytes() for path in root.rglob('*') if path.is_file()})

    def test_success_updates_both_themes_and_tashkent_date(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'assets').mkdir()
            for theme in ('dark','light'):shutil.copy2(ROOT/'assets'/f'kep-overview-{theme}.svg',root/'assets'/f'kep-overview-{theme}.svg')
            payload={key:{'value':value} for key,value in zip(('users','problems','competitions','attempts'),(12345,2345,400,567890))}
            with redirect_stdout(StringIO()):
                self.assertTrue(refresh(root,lambda:payload,datetime(2026,10,28,22,tzinfo=timezone.utc)))
            snapshot=json.loads((root/'data/products.json').read_text())
            self.assertEqual(snapshot['displayDate'],'2026-10-29')
            for theme in ('dark','light'):
                card=(root/'assets'/f'kep-overview-{theme}.svg').read_text()
                self.assertIn('12,345',card);self.assertIn('567,890',card);self.assertIn('2026-10-29',card)

if __name__=='__main__':unittest.main()
