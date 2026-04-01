import json
import re
import uuid

INPUT_FILE = "/Users/sophial/Documents/githubs/anonymousanemone.github.io/_data/gardiner_signlist.json"
OUTPUT_FILE = "gardiner_signlist_formatted.json"

# Egyptian hieroglyph Unicode range
HIERO_RANGE = r"\U00013000-\U0001342F"

# Special transliteration characters
SPECIAL_CHARS = "ꜣꜥḥḫẖšṯḏḳṉꜢꜤ"

# Word pattern (Latin + special chars + optional parentheses)
WORD = rf"[A-Za-z{SPECIAL_CHARS}]+(?:\s*\([^)]*\))?"

# --- PATTERNS ---

# 1. Word directly after hieroglyphs
after_hiero_pattern = re.compile(
    rf"([{HIERO_RANGE}]+)\s*({WORD})"
)

# 2. Words containing special transliteration characters
special_word_pattern = re.compile(
    rf"\b[A-Za-z{SPECIAL_CHARS}]*[{SPECIAL_CHARS}][A-Za-z{SPECIAL_CHARS}]*\b"
)

# --- TAGGING FUNCTIONS ---

def tag_after_hieroglyphs(text):
    def replacer(match):
        glyphs = match.group(1)
        word = match.group(2)

        # avoid tagging if already tagged
        if word.startswith("[t]"):
            return match.group(0)

        return f"{glyphs} [t]{word}[/t]"

    return after_hiero_pattern.sub(replacer, text)


def tag_special_words(text):
    def replacer(match):
        word = match.group(0)

        # skip if already tagged
        if word.startswith("[t]") or word.endswith("[/t]"):
            return word

        return f"[t]{word}[/t]"

    return special_word_pattern.sub(replacer, text)


def protect_existing_tags(text):
    protected = {}

    def replacer(match):
        key = f"__PROTECTED_{uuid.uuid4().hex}__"
        protected[key] = match.group(0)
        return key

    text = re.sub(r"\[t\].*?\[/t\]", replacer, text)
    return text, protected

def restore_protected_tags(text, protected):
    for key, value in protected.items():
        text = text.replace(key, value)
    return text

# --- CLEANUP PASS ---

def cleanup_tags(text):
    # 1. Remove nested tags: [t][t]word[/t][/t] → [t]word[/t]
    text = re.sub(r"\[t\]\s*\[t\]", "[t]", text)
    text = re.sub(r"\[/t\]\s*\[/t\]", "[/t]", text)

    # 2. Fix partial overlaps: [t]word[/t][/t] → [t]word[/t]
    text = re.sub(r"\[/t\]+", "[/t]", text)

    # 3. Remove empty tags
    text = re.sub(r"\[t\]\s*\[/t\]", "", text)

    # 4. Ensure spacing after hieroglyphs is clean
    text = re.sub(rf"([{HIERO_RANGE}])\[t\]", r"\1 [t]", text)

    # 5. Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    return text


# --- MAIN PROCESS ---

def process_notes(text):
    # Replace underscores with zero-width space
    text = text.replace("_", "\u200B")

    # --- PROTECT EXISTING TAGS ---
    text, protected = protect_existing_tags(text)

    # --- TAGGING ---
    text = tag_after_hieroglyphs(text)
    text = tag_special_words(text)

    # --- CLEANUP ---
    text = cleanup_tags(text)

    # --- RESTORE ---
    text = restore_protected_tags(text, protected)

    return text


# --- LOAD ---
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
print(type(data))
print(len(data) if isinstance(data, list) else "not a list")
print(data[0] if isinstance(data, list) else list(data.keys())[:5])

# --- PROCESS ---
for entry in data["sign list"]:
    if "notes" in entry and isinstance(entry["notes"], str):
        entry["notes"] = process_notes(entry["notes"])

# --- SAVE ---
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done! Cleaned and tagged output written to", OUTPUT_FILE)