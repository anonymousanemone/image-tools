from bs4 import BeautifulSoup
import json

# Path to your HTML snippet file
HTML_FILE = "temp_html_signs.html"
OUTPUT_FILE = "gardiner_signlist.json"

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

# BeautifulSoup can parse incomplete HTML fragments
soup = BeautifulSoup(html, "html.parser")

rows = soup.select("table#myTable tr")

grouped = {}
data = []

for row in rows:
    # Skip header row
    if row.find("th"):
        continue
    cells = row.find_all("td")
    if not cells or len(cells) < 7:
        continue

    category_group = cells[2].get_text(strip=True)
    gardiner_number = cells[3].get_text(strip=True)
    glyph_tag = cells[4].find("a")
    glyph = glyph_tag.get_text(strip=True) if glyph_tag else ""
    # Convert glyph to Unicode codepoint
    unicode_number = (
        f"U+{ord(glyph):04X}" if glyph else ""
    )

    if category_group not in grouped:
        grouped[category_group] = []

    grouped[category_group].append([
        glyph,
        gardiner_number])

    record = {
        "category_group": category_group,
        "gardiner_number": gardiner_number,
        "glyph": glyph,
        "unicode": unicode_number,
        "description": cells[5].get_text(strip=True),
        "notes": cells[6].get_text(" ", strip=True),}
    data.append(record)

    output = {
    "index": grouped,
    "sign list": data
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(data)} records to {OUTPUT_FILE}")


# with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#     json.dump(data, f, ensure_ascii=False, indent=2)

# print(f"Wrote {len(data)} records to {OUTPUT_FILE}")
