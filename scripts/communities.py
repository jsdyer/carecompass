"""Build self-contained child-care locality guides from the validated public capture."""
from collections import Counter, defaultdict
from html import escape
from itertools import groupby
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree as ET
import json
import re
import unicodedata

PROVINCES = {"BC": "British Columbia", "NS": "Nova Scotia"}
AGE_LABELS = {"under36": "Under 3", "preschool": "Preschool age", "school": "School age"}
NS_AGE_LABELS = {"infant": "Infant", "toddler": "Toddler", "preschool": "Preschool age", "school": "School age"}
PROGRAM_LABELS = {"full_day": "Full day", "part_day": "Part day", "school": "School-age program"}
HOUR_LABELS = {"weekend": "Weekends", "early": "Before 6 a.m.", "late": "After 7 p.m.", "overnight": "Overnight"}


def local_key(value):
    """Match published locality variants while retaining separate named communities."""
    value = re.sub(r",\s*(?:BC\.?|NS\.?)?\s*$", "", value.strip(), flags=re.I)
    folded = unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def anchor(url, title, css=""):
    attr = f' class="{css}"' if css else ""
    return f'<a href="{escape(url, quote=True)}"{attr}>{escape(title)}</a>'


def render(stage, canonical_root, path, title, description, content, live):
    folder = stage / path
    folder.mkdir(parents=True, exist_ok=True)
    back = "../" * len(Path(path).parts)
    canonical = f'<link rel="canonical" href="{canonical_root}{path}">' if live else ""
    directory = anchor(back + "records/", "Community guides")
    meta = '<script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script>' if live else ""
    (folder / "index.html").write_text(f'''<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Care Compass</title><meta name="description" content="{escape(description, quote=True)}">
{canonical}<link rel="stylesheet" href="{back}style.css">{meta}</head><body class="community-guide" data-tool-id="carecompass">
<header><nav aria-label="Navigation">{anchor(back, "Care Compass")} · {directory}</nav><h1>{escape(title)}</h1></header>
<main>{content}</main><footer>{anchor(back, "Search the full child-care directory")} {anchor("https://coolcode.ca/", "CoolCode.ca")}</footer></body></html>''', encoding="utf-8")


def facts(rows, field, labels, base):
    counts = Counter(key for r in rows for key in labels if r[field].get(key) is True)
    parameter = {"ages": "age", "programs": "program", "operating": "hours"}[field]
    parts = []
    for key, label in labels.items():
        count = counts[key]
        item = anchor(base + "&" + parameter + "=" + key, label) if count else escape(label)
        parts.append(f"<li><b>{count:,}</b>{item}</li>")
    return '<ul class="facts">' + "".join(parts) + "</ul>"


def providers(rows, age_labels, *, always_flat=False):
    result = []
    sorted_rows = sorted(rows, key=lambda r: (r["name"].casefold(), r["id"]))
    for r in sorted_rows:
        tags = [label for k, label in age_labels.items() if r["ages"].get(k)]
        if r["province"] == "NS":
            tags.extend(label for k, label in PROGRAM_LABELS.items() if r["programs"].get(k))
        else:
            tags = ([r["type"]] if r.get("type") else []) + tags
        phone = str(r.get("phone") or "").strip()
        digits = re.fullmatch(r"(?:\+?1[\s.()-]*)?(\d{3})[\s.()-]*(\d{3})[\s.-]*(\d{4})", phone.lstrip("("))
        contact = anchor("tel:+1" + "".join(digits.groups()), phone) if digits else escape(phone or "Phone not supplied")
        name = escape(r["name"])
        detail = escape(" · ".join(tags))
        result.append((r["name"][:1].upper(), f"<li><span>{name}<small>{detail}</small></span>{contact}</li>"))
    if len(rows) <= 20 or always_flat:
        return '<ul class="provider-list">' + "".join(x[1] for x in result) + "</ul>"
    output = ""
    for first, group in groupby(result, key=lambda x: x[0]):
        group = list(group)
        output += (f'<details><summary>{escape(first)} · {len(group)} listings</summary><ul class="provider-list">'
                   + "".join(x[1] for x in group) + "</ul></details>")
    return output


def place_links(places, prefix):
    return '<ul class="place-list">' + "".join(
        "<li>" + anchor(prefix + slug + "/", city) + f"<small>{len(rows):,} facility listings</small></li>"
        for slug, city, rows in places) + "</ul>"


def place_page(province, city, rows, source, checked, others):
    province_name = PROVINCES[province]
    title = f"Licensed child care in {city}, {province}"
    query = "../../?" + urlencode({"province": province, "community": city})
    desc = (f"Compare age groups and {'operating schedules' if province == 'BC' else 'programs'} "
            f"across {len(rows):,} facility listings in {city}, {province}. Find providers to call about care.")
    count = len(rows)
    summary = (f'<p>{count:,} facility listing{"s" if count != 1 else ""} in the {province_name} directory '
               f'use{"s" if count == 1 else ""} {escape(city)} as the address locality.</p>')
    if province == "BC":
        types = Counter(r.get("type") for r in rows)
        summary += (f'<p>The directory identifies {types["Licensed Group"]:,} licensed group and '
                    f'{types["Licensed Family"]:,} licensed family care listings here. It covers providers receiving provincial funding.</p>')
    else:
        summary += (f'<p>{sum(r["programs"].get("full_day") is True for r in rows)} list a full-day program. '
                    'Check which ages that program serves with the provider.</p>')
    if (province, city) == ("BC", "Langley"):
        summary += "<p>The source uses Langley addresses for both the City and the Township. Check the address when planning your trip.</p>"
    elif (province, city) == ("NS", "Halifax"):
        summary += "<p>Dartmouth, Bedford and other separately named communities in Halifax Regional Municipality have their own listings.</p>"
    body = summary + '<p class="guide-actions">' + anchor(query, f"Build a {city} contact shortlist", "guide-primary") + anchor("#providers", "Find a provider phone number") + "</p>"
    split_ages = province == "NS" and any(r["ages"].get(k) is not None for r in rows for k in ("infant", "toddler"))
    age_labels = NS_AGE_LABELS if split_ages else AGE_LABELS
    explain = ("The province lists infant and toddler care separately. A facility can serve both. "
               "Ask about your child’s age and intended start date." if split_ages else
               "One listing can serve several age groups. Under 3 includes infant or toddler care. Ask about your child’s exact age and start date.")
    if province == "NS" and not split_ages:
        explain += " This edition does not distinguish infant and toddler listings."
    missing = sum(all(r["ages"].get(k) is None for k in AGE_LABELS) for r in rows)
    body += ("<section><h2>Which ages do providers list?</h2>"
             f"<p>{explain}</p>"
             + facts(rows, "ages", age_labels, query))
    if missing:
        body += (f"<p>{missing:,} of the {count:,} listings have no age information. Include those providers in your calls "
                 "if the age filter gives you few matches.</p>")
    body += "</section>"
    if province == "BC":
        known = sum(any(v is not None for v in r["operating"].values()) for r in rows)
        body += (f"<section><h2>Who lists care outside regular weekday hours?</h2><p>{known:,} of {count:,} listings supply an operating pattern. "
                 "The figures count providers that explicitly report each schedule. Ask about the days and times you need.</p>"
                 + facts(rows, "operating", HOUR_LABELS, query) + "</section>")
    else:
        body += ("<section><h2>Full-day, part-day and school-age care</h2><p>Choose a program to see matching providers. "
                 "For school-age care, ask which schools the provider serves and whether it offers pickup.</p>"
                 + facts(rows, "programs", PROGRAM_LABELS, query) + "</section>")
    if split_ages:
        infant_rows = [r for r in rows if r["ages"].get("infant") is True]
        if infant_rows:
            body += (f'<section id="infant-care"><h2>Infant care in {escape(city)}</h2>'
                     f'<details><summary>Show {len(infant_rows)} infant-care listings and contact numbers</summary>'
                     + providers(infant_rows, age_labels, always_flat=True) + '</details></section>')
    body += ('<section id="providers"><h2>Providers to call</h2><p>These are directory listings. Contact a provider to confirm fees, '
             'hours and available spaces or join its waitlist.</p>' + providers(rows, age_labels) + "</section>")
    if others:
        body += "<section><h2>Other communities to compare</h2>" + place_links(others, "../") + "</section>"
    if (province, city) == ("NS", "Halifax"):
        body += "<p>" + anchor("https://coolcode.ca/field-notes/comparing-halifax-rent-and-child-care/", "Compare Halifax rent and child care before a move") + "</p>"
    edition = source.get("coverage_date")
    date = source.get("source_updated")
    timing = (f"{escape(edition)}. " if edition else "The province does not supply a whole-directory edition date. ")
    if date:
        timing += f"Source data updated {escape(date[:10])}. "
    body += (f'<section class="sources"><h2>Source and dates</h2><p>{anchor(source["url"], source["name"])}. '
             + timing + f'Directory checked {escape(checked[:10])}. Call to confirm current availability.</p><p>'
             + anchor(source["licence_url"], source["licence"]) + "</p></section>")
    return title, desc, body


def build_guides(stage, tool, live):
    data = json.loads((stage / "data/latest.json").read_text())
    groups = json.loads((stage / "config.json").read_text())["community_guides"]
    base = "https://coolcode.ca" + tool["url"]
    sources = {s["id"].upper(): s for s in data["sources"]}
    rows = defaultdict(list)
    for facility in data["facilities"]:
        rows[(facility["province"], local_key(facility.get("city", "")))].append(facility)
    paths = ["records/"]
    sections, options = [], []
    for province, regions in groups.items():
        sections.append(f'<h2 id="{province.lower()}">{PROVINCES[province]}</h2>')
        options.append(f'<optgroup label="{PROVINCES[province]}">')
        for region, names in regions.items():
            places = [(province.lower() + "-" + local_key(name), name, rows[province, local_key(name)]) for name in names]
            places = [place for place in places if place[2]]
            if not places:
                continue
            sections.append("<section><h3>" + escape(region) + "</h3>" + place_links(places, "") + "</section>")
            for slug, city, records in places:
                path = "records/" + slug + "/"
                if path in paths:
                    raise ValueError("Duplicate community slug: " + slug)
                paths.append(path)
                others = [place for place in places if place[0] != slug]
                title, desc, body = place_page(province, city, records, sources[province], data["checked_at"], others)
                render(stage, base, path, title, desc, body, live)
                options.append(f'<option data-province="{province}" value="{escape(slug)}">{escape(city)}</option>')
        options.append("</optgroup>")
    body = ("<p>Choose a community to compare published age groups and programs, find phone numbers and start a contact shortlist. "
            "The full directory also includes smaller communities beyond these guides.</p>"
            '<p class="guide-actions"><a href="#bc">British Columbia</a><a href="#ns">Nova Scotia</a>'
            '<a href="../">Search all facilities</a></p>' + "".join(sections))
    render(stage, base, "records/", "Child care by community in BC and Nova Scotia",
           "Find licensed child-care providers, compare published programs and prepare a contact shortlist in communities across BC and Nova Scotia.", body, live)
    if live:
        sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for path in sorted(paths):
            ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = base + path
        ET.ElementTree(sitemap).write(stage / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    return "".join(options)
