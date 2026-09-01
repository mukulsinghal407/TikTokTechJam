import re

from starter.helper.config import (
    ATTRIBUTE_PATTERNS,
    COLOR_RE,
    MATERIAL_RE,
    MONEY_RE,
    NO_PREFERENCE_MARKERS,
    REPLACEMENT_MARKERS,
)
from starter.helper.dataclasses import Evidence
from starter.helper.utils import _terms


class EvidenceExtractor:
    """Parse user messages into structured evidence and category terms."""

    def detect_attribute(self, text: str) -> str:
        lower = text.lower()
        if MATERIAL_RE.search(lower):
            return "material"
        if COLOR_RE.search(lower):
            return "color"
        if MONEY_RE.search(lower) or any(x in lower for x in ATTRIBUTE_PATTERNS["budget"]):
            return "budget"
        for attr in ("size", "style", "use_case", "feature", "brand"):
            if any(term in lower for term in ATTRIBUTE_PATTERNS[attr]):
                return attr
        return "other"

    def extract_category_terms(self, text: str) -> list[str]:
        lower = text.lower()
        match = re.search(r"looking for\s+(.+?)(?:[,.]|but\b|a key requirement|$)", lower)
        terms = _terms(match.group(1) if match else text)
        vocab: set[str] = set()
        for values in ATTRIBUTE_PATTERNS.values():
            for value in values:
                vocab.update(_terms(value))
        vocab.update(MATERIAL_RE.pattern.lower().split("|"))
        return [term for term in terms if term not in vocab][:10]

    def extract(self, message: str) -> list[Evidence]:
        lower = message.lower().strip()
        if any(marker in lower for marker in NO_PREFERENCE_MARKERS):
            attr = self.detect_attribute(lower)
            if attr != "other":
                return [Evidence(attr, "", status="NO_PREFERENCE")]

        replacement = any(marker in lower for marker in REPLACEMENT_MARKERS)
        found: list[Evidence] = []

        material = MATERIAL_RE.search(message)
        if material:
            found.append(Evidence("material", material.group(1).lower(), hard=replacement))

        color = COLOR_RE.search(message)
        if color:
            found.append(Evidence("color", color.group(1).lower(), hard=replacement))

        money = MONEY_RE.search(message)
        if money:
            found.append(Evidence("budget", money.group(1), hard=True))

        if "what matters is:" in lower:
            for raw in (x.strip() for x in message.split(":", 1)[-1].split(";") if x.strip()):
                found.append(Evidence(self.detect_attribute(raw), raw))
        elif "key requirement is:" in lower:
            raw = message.split(":", 1)[-1].strip()
            if raw:
                found.append(Evidence(self.detect_attribute(raw), raw, hard=True))
        elif replacement and "what i need is:" in lower:
            raw = re.split(r"what i need is:\s*", message, flags=re.I)[-1].strip(" .")
            if raw:
                found.append(Evidence(self.detect_attribute(raw), raw, hard=True))

        dedup: dict[tuple[str, str, str], Evidence] = {}
        for evidence in found:
            dedup[(evidence.attribute, evidence.value.lower(), evidence.status)] = evidence
        return list(dedup.values())
