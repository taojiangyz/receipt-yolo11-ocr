import re
import unicodedata

def normalize_store_name(text: str) -> str:
    t = text.replace("\n", " ").strip()
    lower = t.lower()

    if "family" in lower or "famima" in lower or "ファミ" in t:
        return "FamilyMart"

    if "lawson" in lower or "ローソン" in t:
        return "LAWSON"

    if "7-eleven" in lower or "seven" in lower or "セブン" in t or "イレブン" in t:
        return "7-Eleven"

    if "mybasket" in lower or "まいばす" in t or "まいはす" in t or "まいほす" in t:
        return "MyBasket"

    return ""


def extract_date(text: str) -> str:
    from datetime import date
    text = unicodedata.normalize("NFKC", text).replace(" ", "")
    match = re.search(r"(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})", text)
    if match:
        try:
            return date(*map(int, match.groups())).isoformat()
        except ValueError:
            pass
    return ""


def extract_amount(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("￥", "¥")
    lines = [line.replace(" ", "").replace(",", "") for line in text.splitlines() if line.strip()]
    blocked = re.compile(r"小計|お預|預り|預かり|釣|現金|税|支払")
    def numbers(line, currency_only=False):
        pattern = r"¥([0-9]{1,9})(?![0-9])" if currency_only else r"(?<![0-9])([0-9]{1,9})(?![0-9])"
        return re.findall(pattern, line)
    totals = []
    for i, line in enumerate(lines):
        if re.search(r"合計|総計", line) and not blocked.search(line):
            found = numbers(line)
            if not found:
                # OCR can emit label and value in either order.
                adjacent = [lines[j] for j in (i-1, i+1) if 0 <= j < len(lines)]
                found = [n for neighbor in adjacent if re.fullmatch(r"¥?[0-9]+円?", neighbor)
                         for n in numbers(neighbor)]
            totals.extend(found)
    if totals:
        return str(int(totals[0])) if len(set(totals)) == 1 else ""
    candidates = [n for line in lines if not blocked.search(line) for n in numbers(line, True)]
    return str(int(candidates[0])) if len(candidates) == 1 else ""


