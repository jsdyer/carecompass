import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from communities import build_guides, local_key
from refresh import ns


class CommunityTests(unittest.TestCase):
    def test_locality_variants_and_nonmatching_neighbours(self):
        self.assertEqual(local_key(" LANGLEY, BC. "), "langley")
        self.assertEqual(local_key("Fort St. John"), "fort-st-john")
        self.assertNotEqual(local_key("Fort Langley"), "langley")

    def test_unknown_flags_do_not_imply_an_age_group(self):
        def row(**fields):
            return ns({"facility_identifier":"10","facility_name":"Example",**fields})["ages"]
        self.assertIsNone(row(age_toddler="No")["under36"])
        self.assertIs(row(age_toddler="No",age_infant="No")["under36"],False)
        self.assertIs(row(age_toddler="No",age_infant="Yes")["infant"],True)
        self.assertIs(row(age_toddler="Yes",age_infant="No")["toddler"],True)

    def test_guides_rebuild_with_capture_and_suppress_empty_communities(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp)
            (stage/"data").mkdir()
            (stage/"config.json").write_text(json.dumps({"community_guides":{"NS":{"Area":["New Town","Empty"]}}}))
            row=ns({"facility_identifier":"zz","facility_name":"A & B <Daycare>","city":"NEW TOWN","age_infant":"Yes","phone":"902-555-0111"})
            source={"id":"ns","name":"NS directory","url":"https://example.com","licence":"Licence","licence_url":"https://example.com/open"}
            record={"sources":[source],"facilities":[row],"checked_at":"2025-10-02T12:23:06Z"}
            def render():
                (stage/"data/latest.json").write_text(json.dumps(record))
                build_guides(stage,{"url":"/carecompass/"},True)
                return (stage/"records/ns-new-town/index.html").read_text()
            page=render()
            self.assertIn("A &amp; B",page)
            self.assertIn('tel:+19025550111',page)
            self.assertIn('id="infant-care"',page)
            self.assertIn('community=New+Town&amp;age=infant',page)
            self.assertNotIn('empty', (stage/"sitemap.xml").read_text())
            self.assertEqual(len(ElementTree.parse(stage/"sitemap.xml").getroot()),2)
            self.assertEqual(page.count('rel="canonical"'),1)
            del row["ages"]["infant"],row["ages"]["toddler"]
            self.assertNotIn('id="infant-care"',render())

    def test_new_province_uses_its_own_coverage_and_links_without_toddler_program_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            (stage / "data").mkdir()
            config = {"community_guides": {"NS": {"Halifax area": ["Halifax"]},
                                          "NB": {"Southeast": ["Dieppe", "Empty"]}}}
            source = {"id": "nb", "province_name": "New Brunswick", "name": "Licence registry",
                      "url": "https://example.ca/licences", "licence": "Open data",
                      "licence_url": "https://example.ca/terms", "sites_url": "https://example.ca/sites",
                      "sites_name": "Facility sites", "sites_source_updated": "2026-10-20"}
            row = {"id": "nb-12", "province": "NB", "name": "Garderie", "type": "Home",
                   "city": "Dieppe, NB", "phone": "", "languages": "French",
                   "ages": {"infant": True, "preschool": True, "school": False}, "programs": {}, "operating": {}}
            (stage / "config.json").write_text(json.dumps(config))
            (stage / "data/latest.json").write_text(json.dumps({
                "sources": [source], "facilities": [row], "checked_at": "2026-11-28"}))
            options = build_guides(stage, {"url": "/carecompass/"}, True)
            page = (stage / "records/nb-dieppe/index.html").read_text()
            self.assertIn("licensed places for that age group", page)
            self.assertIn("Phone not supplied", page)
            self.assertIn("community=Dieppe&amp;language=french", page)
            self.assertIn('href="https://example.ca/sites"', page)
            self.assertIn("2026-10-20", page)
            self.assertNotIn("toddler", page.lower())
            self.assertNotIn("full-day", page.lower())
            self.assertIn('data-province="NB"', options)
            self.assertNotIn("Empty", options)
            self.assertNotIn("Nova Scotia", (stage / "records/index.html").read_text())
            self.assertIn("New Brunswick", (stage / "records/index.html").read_text())
            self.assertEqual(len(ElementTree.parse(stage / "sitemap.xml").getroot()), 2)
