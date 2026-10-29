import unittest
from rules import parse_embedded,resolve_scope,selective_compare

class RuleTests(unittest.TestCase):
    def test_embedded(self):
        p=parse_embedded(['[DOCMATCH:START id="objek" mode="exact"]','Jumlah 25 unit','[DOCMATCH:END]','Harga 150 juta'])
        self.assertEqual(p.blocks,['Jumlah 25 unit','Harga 150 juta'])
        self.assertEqual(p.embedded,{0})
        self.assertEqual(resolve_scope(p,{1},'hybrid'),{0,1})
    def test_selective(self):
        diff,unknown,mapping=selective_compare(['Jumlah 25 unit','Harga 150 juta'],['Jumlah 20 unit','Harga 100 juta'],{0})
        self.assertEqual(len(diff),1)
        self.assertEqual(diff[0].reference_index,0)
    def test_unmapped(self):
        diff,unknown,_=selective_compare(['Pengadaan 25 komputer'],['Kalimat yang tidak berkaitan'],{0})
        self.assertEqual(unknown,[0]);self.assertEqual(diff,[])
    def test_malformed(self):
        with self.assertRaises(ValueError):parse_embedded(['[DOCMATCH:END]'])
if __name__=='__main__':unittest.main()
