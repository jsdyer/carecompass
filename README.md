# Care Compass

[Use Care Compass](https://coolcode.ca/carecompass/) to search official child-care directories in British Columbia and Nova Scotia, compare published services and keep a private contact shortlist. It works immediately in the browser and needs no API key.

<!-- coolcode:guide -->
Care Compass collects the complete published BC Child Care Map layer and Nova Scotia Child Care Directory, rather than limiting the search to a preset city list. Search a name, city, street or postal code; filter by province, age, program, operating pattern and reported vacancy. Specific filters match explicit positive source flags, so unknown fields remain visible under “Any / unknown”. The map uses supplied coordinates and loads OpenStreetMap tiles only when opened.

BC covers ministry-funded licensed child care, not every BC provider. Its reported vacancy flags include their original update dates and are never promises of an available space. Nova Scotia updates its directory biannually; its source coverage date and publication date are displayed separately from our collection check. NS does not publish live vacancies in this dataset. Licence capacity is not spare capacity, and source inspection dates are not inspection findings or endorsements.

Choose “Add to shortlist” to save a provider on this device. Contact status and notes survive ordinary refreshes in the same browser, with CSV export and a delete button; they do not sync or submit an application. Directory JSON export/reopen preserves earlier source coverage and dates separately from the private shortlist. Confirm age eligibility, fees, availability and hours with the provider before making plans.
<!-- /coolcode:guide -->

## Sources and date meanings

- [BC Child Care Map](https://catalogue.data.gov.bc.ca/dataset/child-care-map-data): official [ArcGIS layer 700](https://delivery.maps.gov.bc.ca/arcgis/rest/services/mpcm/bcgwpub/MapServer/700). Enumerates every object ID, fetches batches and validates exact ID/count coverage. Facility IDs are preserved. BC advertises daily updates; a whole-layer edition date is not supplied, so it is shown as unknown. Vacancy dates are provider-reported and remain separate.
- [NS Child Care Directory, 3j9v-yimg](https://data.novascotia.ca/Education-Early-Childhood/Child-Care-Directory/3j9v-yimg): counts and paginates all rows ordered by facility identifier. Its metadata’s Usage Considerations supplies the coverage date; `rowsUpdatedAt` supplies the source publication date. At initial capture: current as June 30, 2026, published September 1, 2026. The collector reads these fields on every run, not a hardcoded edition.
- BC information is used under the [Open Government Licence – BC](https://www2.gov.bc.ca/gov/content/data/open-data/open-government-licence-bc); NS information under the [Open Government Licence – Nova Scotia](https://novascotia.ca/opendata/licence.asp). Neither government endorses this tool. Leaflet 1.9.4 is vendored with its BSD licence; map tiles © OpenStreetMap contributors.

`web/data/latest.json` has `schema`, `checked_at`, `record_count`, complete `sources` metadata and `facilities`. `checked_at` means a successful full source check. It is not a new directory edition or live vacancy observation. The small `web/data/status.json` is for operational monitoring.

All-N BC service/hour defaults accompanying “None” or “No opening hours” are normalized to unknown instead of declaring a provider offers no care. Optional missing fields stay null. NS infant/toddler flags map to under-three search; its exact textual age range is also displayed. Locations are taken from each source, never geocoded from guessed addresses.

## Expand or customize

1. Edit `web/config.json`: `default_province`, `page_size`, source names, metadata URLs and coverage descriptions are documented there. Current adapters collect *all* BC and NS records; adding another city requires no change.
2. To add a jurisdiction, write and test a reviewed adapter in `scripts/refresh.py`, then add its source entry to the configuration. Map its ages/operating patterns explicitly; never invent vacancy information. Add its province selector and coverage description in the UI. Unknown adapters fail the collection rather than silently disappearing.
3. Run `python3 scripts/refresh.py`, inspect each source count/date and the normalized data, then run the checks below. A failed or incomplete refresh leaves the previous data and timestamps untouched.
4. Publish a main-branch build through GitHub Pages (source: GitHub Actions). Changes are copied to `dist/`; no CNAME is used. The content-versioned asset graph prevents a returning browser from loading the previous app or capture with the new HTML.

Every validated capture is retained in Git history. Visitors can download a public directory JSON and reopen it later; the displayed coverage/check dates and counts follow that file. Exported shortlist CSV contains the visitor’s private notes; it is separate from directory JSON.

## Development and checks

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server --directory dist 8000
# Browser test (CI uses Ubuntu's installed Chrome):
python3 -m pip install -r tests/browser-requirements.txt
CHROMIUM_PATH=/usr/bin/google-chrome python3 tests/browser_smoke.py
```

The ordinary build is offline and uses the committed validated capture. Collection uses Python’s standard library. Tests cover full-source completeness, unknown flags and dates, filters, private shortlist persistence, safe URLs/CSV, older capture loading, responsive layout and content versions.

## Refresh operations

`.github/workflows/pages.yml` runs at **09:17 UTC daily**, on main changes and on manual dispatch. Collection step: **Refresh complete child-care directories**. Every source must pass before publication; failure preserves the previous deployed capture. The schedule guard explicitly includes `pages.yml` and itself. Register `https://coolcode.ca/carecompass/data/status.json`, `checked_at` (36-hour tolerance), `record_count` (facility records, not vacancy count), workflow and step with the hub watchdog; grant its GitHub App access to this repo. No dispatch input or API secret is required.

Follow the [CoolCode tool lifecycle](https://github.com/jsdyer/jsdyer.github.io/blob/main/docs/tool-lifecycle.md) for catalogue, guide, sitemap, audit, Worker ID and watchdog integration.
