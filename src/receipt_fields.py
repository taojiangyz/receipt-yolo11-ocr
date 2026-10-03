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


def date_candidates(text: str) -> list[str]:
    """Only complete four-digit years; never infer lost year digits or choose between dates."""
    from datetime import date
    text = unicodedata.normalize("NFKC", text)
    # Japanese receipt separators may be OCR'd as parentheses. Digits stay unchanged.
    pattern = r"(?<![0-9])(20[0-9]{2})\s*[年/().-]\s*([0-9]{1,2})\s*[月/().-]\s*([0-9]{1,2})(?![0-9])"
    values = set()
    for match in re.finditer(pattern, text):
        try:
            values.add(date(*map(int, match.groups())).isoformat())
        except ValueError:
            continue
    return sorted(values)


def extract_date(text: str) -> str:
    values = date_candidates(text)
    return values[0] if len(values) == 1 else ""


def extract_amount(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("￥", "¥")
    lines = [re.sub(r"\s+", "", line) for line in text.splitlines() if line.strip()]
    blocked = re.compile(r"小計|お預|預り|預かり|釣|現金|税|支払")
    # Accept only complete integer tokens or consistently grouped thousands.
    # OCR may substitute a dot for a comma, but a decimal or split suffix
    # must never be silently accepted as a shorter integer.
    token = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]{1,9})"
    def numbers(line, currency_only=False):
        prefix = r"¥" if currency_only else r"(?<![0-9.,])"
        values = re.findall(prefix + "(" + token + r")(?![0-9.,])", line)
        normalized = [v.replace(",", "").replace(".", "") for v in values]
        return [v for v in normalized if len(v) <= 9]
    if re.search(r"¥[0-9]+\n[0-9]+\n[0-9]+(?:\n|$)", "\n".join(lines)):
        return ""
    totals = []
    for i, line in enumerate(lines):
        if re.search(r"合計|総計", line) and not blocked.search(line):
            found = numbers(line)
            if not found:
                adjacent = [lines[j] for j in (i-1, i+1) if 0 <= j < len(lines)]
                found = [n for neighbor in adjacent
                         if re.fullmatch(r"¥?" + token + r"円?", neighbor)
                         for n in numbers(neighbor)]
            totals.extend(found)
    if totals:
        return str(int(totals[0])) if len(set(totals)) == 1 else ""
    candidates = [n for line in lines if not blocked.search(line) for n in numbers(line, True)]
    return str(int(candidates[0])) if len(set(candidates)) == 1 else ""


def amount_text_needs_review(text: str) -> bool:
    """A lone currency amount is usable; unrelated OCR fragments lack an anchor."""
    text = unicodedata.normalize("NFKC", text).replace("￥", "¥")
    lines = [re.sub(r"\s+", "", line) for line in text.splitlines() if line.strip()]
    if any(re.search(r"合計|総計", line) and not re.search(r"小計|税|支払", line) for line in lines):
        return False
    currency_line = r"¥[0-9]+(?:[,.][0-9]{3})*円?"
    return any(not re.fullmatch(currency_line, line) for line in lines)
