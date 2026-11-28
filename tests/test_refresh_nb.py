import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh import collect, nb, nb_source_rows


class NewBrunswickTests(unittest.TestCase):
    def setUp(self):
        self.facility = {
            'license_number': '123', 'operator_id': '42', 'facility_name': 'Example',
            'facility_address_1': '123 Lake Road, Bathurst', 'facility_address_2': 'NB',
            'facility_address_3': 'E2A 1A1', 'facility_type': 'Full-time Centre',
            'max_number_of_children': '30', 'max_number_of_preschool_aged': '20',
            'max_number_of_infants': '0', 'language_of_service': 'French'
        }
        self.site = {
            'licence_number': '123', 'operator_id': '42', 'facility_name': 'Example',
            'civic_address': '123 Lake Road, Bathurst NB E2A 1A1',
            'facility_phone': '(506) 555-0101', 'longitude': '-65.6', 'latitude': '47.6',
        }
        self.source = {'id': 'nb', 'endpoint': 'facilities', 'metadata': 'facility-meta',
                       'sites_endpoint': 'sites', 'sites_metadata': 'site-meta',
                       'minimum_records': 1, 'minimum_site_records': 1}

    def test_licence_level_age_counts_and_unknowns(self):
        row = nb(self.facility, [self.site])
        self.assertEqual((row['id'], row['capacity'], row['city']), ('nb-123', 30, 'Bathurst'))
        self.assertEqual(row['languages'], 'French')
        self.assertFalse(row['ages']['infant'])
        self.assertTrue(row['ages']['preschool'])
        self.assertIsNone(row['ages']['school'])
        self.assertIsNone(row['ages']['under36'])
        self.assertTrue(nb({**self.facility, 'max_number_of_infants':'2'}, [])['ages']['under36'])
        self.assertEqual(row['capacity_by_age']['preschool'], 20)
        self.assertIsNone(row['vacancy'])
        self.assertIsNone(row['programs'].get('full_day'))
        self.assertEqual(row['phone'], self.site['facility_phone'])
        self.assertEqual(row['coordinates'], [-65.6, 47.6])

    def test_contact_requires_one_matching_name_operator_address_and_published_street(self):
        for sites in ([], [self.site, self.site], [{**self.site, 'facility_name':'Moved'}],
                      [{**self.site, 'operator_id':'2'}], [{**self.site, 'civic_address': 'Old street'}]):
            with self.subTest(sites=sites):
                row = nb(self.facility, sites)
                self.assertEqual(row['phone'], '')
                self.assertIsNone(row['coordinates'])
                self.assertEqual(row['capacity'], 30)
        limited = {**self.facility, 'facility_address_1': ', Bathurst', 'facility_address_3': ''}
        row = nb(limited, [{**self.site, 'civic_address': ', Bathurst NB'}])
        self.assertEqual(row['city'], 'Bathurst')
        self.assertEqual(row['address'], 'Bathurst, NB')
        self.assertIsNone(row['coordinates'])
        self.assertEqual(row['phone'], '')
        self.assertEqual(nb({**limited, 'facility_address_1': ', Riverbank, Carleton Co'}, [])['city'], 'Riverbank')

    def test_duplicate_licences_are_rejected_even_if_socrata_row_ids_differ(self):
        with patch('refresh.nb_source_rows', side_effect=[([self.facility, deepcopy(self.facility)], '2026-11-01'),
                                                          ([self.site], '2026-11-02')]):
            with self.assertRaisesRegex(ValueError, 'Duplicate facility identifiers'):
                collect({'sources':[self.source]})

    def test_complete_capture_preserves_both_publication_dates(self):
        with patch('refresh.nb_source_rows', side_effect=[([self.facility],'2026-11-01'),([self.site],'2026-11-02')]):
            capture = collect({'sources':[self.source]})
        source = capture['sources'][0]
        self.assertEqual(source['source_updated'], '2026-11-01')
        self.assertEqual(source['sites_source_updated'], '2026-11-02')
        self.assertIsNone(source['coverage_date'])
        self.assertEqual(capture['record_count'], 1)

    def test_reject_changed_source_and_missing_page_or_duplicate_row(self):
        for count, rows, end in ((1, [{'portal_row_id':'a'}], 2),
                                 (2, [{'portal_row_id':'a'}], 1),
                                 (2, [{'portal_row_id':'a'}]*2, 1)):
            with self.subTest(count=count, rows=rows, end=end), patch('refresh.get', side_effect=[
                {'rowsUpdatedAt':1}, [{'count':str(count)}], rows, {'rowsUpdatedAt':end}
            ]):
                with self.assertRaises(ValueError):
                    nb_source_rows('rows', 'meta', 1)
