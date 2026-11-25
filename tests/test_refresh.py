import unittest,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import bc,ns,flag,collect
class RefreshTests(unittest.TestCase):
 def test_bc_defaults_do_not_assert_closed_or_no_care(self):
  row=bc({'FACILITY_ID':'9','OCCUPANT_NAME':'New facility','DESC_PROGRAMS_PROVIDED':'None','DESC_HOURS_OF_OPERATION':'No opening hours','SRVC_UNDER36_IND':'N','OP_WEEKDAY_IND':'N','VACANCY_IND':'Unknown'})
  self.assertIsNone(row['ages']['under36']);self.assertIsNone(row['operating']['weekday']);self.assertIsNone(row['vacancy']);self.assertIsNone(row['vacancy_updated'])
 def test_ns_capacity_is_not_vacancy(self):
  row=ns({'facility_identifier':'19','facility_name':'New facility','total_licence_capacity':'30','age_infant':'Yes'})
  self.assertEqual(row['capacity'],30);self.assertIsNone(row['vacancy']);self.assertIsNone(row['vacancy_updated']);self.assertTrue(row['ages']['under36'])
 def test_incomplete_bc_inventory_is_rejected(self):
  config={'sources':[{'id':'bc','endpoint':'https://example.com','minimum_records':1}]}
  with patch('refresh.get',side_effect=[{'objectIds':[1,2]},{'features':[{'attributes':{'SEQUENCE_ID':1}}]}]):
   with self.assertRaisesRegex(ValueError,'Incomplete BC'):collect(config)
 def test_duplicate_ids_are_rejected_before_fetching_pages(self):
  with patch('refresh.get',return_value={'objectIds':[1,1]}):
   with self.assertRaisesRegex(ValueError,'ID inventory'):collect({'sources':[{'id':'bc','endpoint':'https://example.com'}]})
 def test_unknown_flags_remain_unknown(self):
  for v in ['',None,'Unknown','?']:self.assertIsNone(flag(v))
