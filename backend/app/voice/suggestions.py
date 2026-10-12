"""Conservative phrase suggestions, NEVER automatic transcript corrections.

Catalog support is textual evidence only, not acoustic confidence. Do not infer
unspoken attributes or mutate a proper name, SKU, number, price or negation.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from ..search.normalize import strip_accents

WORD = re.compile(r"(?:[^\W_]|[\u0300-\u036f])+", re.UNICODE)
PROTECTED = set("không chẳng đừng trừ ngoại dưới trên từ đến tới khoảng tối đa thiểu một hai ba bốn năm sáu bảy tám chín mười trăm nghìn ngàn triệu rưỡi nửa k vnd not no without under over between".split())


def words(text):
    return tuple(m.group().lower() for m in WORD.finditer(unicodedata.normalize("NFC", text)))


def near(a, b):
    # Same unaccented syllable, or n/l onset with the rest unchanged (including tone).
    return a != b and (strip_accents(a) == strip_accents(b) or
                       (len(a) > 1 and len(b) > 1 and {a[0], b[0]} == {"n", "l"} and a[1:] == b[1:]))


class PhraseSuggester:
    def __init__(self, snap):
        self.phrases = defaultdict(set)
        self.protected = set()
        # Protect entire names and aliases, including their individual words.
        for mapping in (snap.brands, snap.makers, snap.places):
            for obj in mapping.values():
                for text in [obj.get("name", ""), obj.get("name_normalized", ""), obj.get("name_as_sourced", ""),
                             *(a.get("value", "") if isinstance(a, dict) else a for a in obj.get("aliases", []))]:
                    self.protected.update(words(text))
        for alias in snap.data.get("search_dictionary", {}).get("brand_aliases", []):
            self.protected.update(words(alias["alias"]))
        self.protected_names_folded = {strip_accents(w) for w in self.protected}
        for p in snap.products.values():
            for v in p.get("variants", []):
                self.protected.update(words(v["sku"]))
            texts = [p["name_vi"], *p.get("aliases", []), *p.get("materials", [])]
            # Only categories used by visible products; no draft-only vocabulary.
            category = snap.categories.get(p["category_id"], {})
            category_names = [category.get("name_vi", ""), *category.get("aliases", [])]
            texts += category_names
            # Category/alias + material supported by the SAME product (e.g. bát + sứ),
            # still only substituting an existing syllable in the user's phrase.
            for name in category_names:
                if 1 <= len(words(name)) <= 2 and not re.search(r"[,;/]", name):
                    for material in p.get("materials", []):
                        if 1 <= len(words(material)) <= 2 and not set(words(material)) & set(words(name)):
                            texts.append(f"{name} {material}")
            for text in texts:
                # Comma-separated taxonomy alternatives are not a spoken phrase.
                for segment in re.split(r"[,;/.!?()–—]", text):
                    ts = words(segment)
                    for n in (2, 3, 4):
                        for i in range(len(ts) - n + 1):
                            phrase = ts[i:i + n]
                            if any(w in PROTECTED or any(c.isdigit() for c in w) for w in phrase):
                                continue
                            self.phrases[phrase].add(p["id"])
        self.by_length = defaultdict(list)
        for phrase in self.phrases:
            self.by_length[len(phrase)].append(phrase)

    def suggest(self, text: str, limit=3) -> list[dict]:
        if len(text) > 300:
            return []
        spans = list(WORD.finditer(text))
        ts = tuple(unicodedata.normalize("NFC", m.group().lower()) for m in spans)
        candidates = {}
        for n, phrases in self.by_length.items():
            for i in range(len(ts) - n + 1):
                src = ts[i:i + n]
                if src in self.phrases:
                    continue
                # Avoid suggestions crossing punctuation / sentence boundaries.
                if any(text[spans[j].end():spans[j + 1].start()].strip() for j in range(i, i + n - 1)):
                    continue
                for dst in phrases:
                    changed = [k for k, (a, b) in enumerate(zip(src, dst)) if a != b]
                    if len(changed) != 1:
                        continue
                    k = changed[0]
                    a, b = src[k], dst[k]
                    if (a in PROTECTED or b in PROTECTED or a in self.protected or b in self.protected or
                            strip_accents(a) in self.protected_names_folded or
                            strip_accents(b) in self.protected_names_folded):
                        continue
                    if not near(a, b):
                        continue
                    start, end = spans[i + k].start(), spans[i + k].end()
                    query = text[:start] + b + text[end:]
                    support = len(self.phrases[dst])
                    score = (n, support)
                    if query not in candidates or score > candidates[query][0]:
                        candidates[query] = (score, {"text": query, "phrase": " ".join(dst),
                            "source_text": text[spans[i].start():spans[i + n - 1].end()],
                            "evidence": "catalog_text_only", "requires_confirmation": True,
                            "reason": "Cụm gần âm có trong catalog; hãy đối chiếu với điều bạn muốn tìm."})
        return [item for _, item in sorted(candidates.values(), key=lambda x: (-x[0][0], -x[0][1], x[1]["text"]))[:limit]]
