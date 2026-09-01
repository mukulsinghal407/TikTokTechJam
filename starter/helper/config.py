import re

# ---------------------------------------------------------------------------
# Config: regexes, ontologies, and canned question prompts shared across modules
# ---------------------------------------------------------------------------


TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.IGNORECASE)
MONEY_RE = re.compile(r"(?:under|below|less than|max(?:imum)?|<=?)\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
COLOR_RE = re.compile(
    r"\b(black|white|blue|red|pink|green|brown|gray|grey|purple|yellow|orange|navy|beige|tan|gold|silver)\b",
    re.I,
)
MATERIAL_RE = re.compile(
    r"\b(cotton|polyester|nylon|leather|wool|spandex|silk|rayon|linen|fleece|denim|suede|fabric)\b",
    re.I,
)

# The ask_attribute enum the evaluator allows.
ALLOWED_ATTRIBUTES = (
    "category", "material", "color", "size", "style",
    "brand", "budget", "feature", "use_case", "other",
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
    "im", "i'm", "still", "what", "matters", "need", "key", "requirement",
    "those", "options", "quite", "right", "yet", "about", "one", "specific",
    "attribute", "additional", "preference", "have", "dont", "don't",
}

# The internal ontology is finer-grained than the evaluator's ask ontology.
ATTRIBUTE_PATTERNS: dict[str, tuple[str, ...]] = {
    "size": ("size", "sizing", "wide", "narrow", "width", "small", "medium", "large",
             "xl", "xxl", "petite", "plus size"),
    "style": ("style", "fit", "slim", "relaxed", "loose", "fitted", "sleeve",
              "neck", "neckline", "casual", "formal", "vintage", "classic"),
    "use_case": ("running", "hiking", "gym", "workout", "winter", "outdoor", "work",
                 "office", "wedding", "travel", "walking", "sports", "training"),
    "feature": ("waterproof", "breathable", "lightweight", "comfortable", "comfort",
                "cushion", "cushioned", "durable", "durability", "warm", "warmth",
                "stretch", "stretchy", "pocket", "closure", "heel", "insulated",
                "performance", "weather"),
    "brand": ("brand", "made by", "manufacturer"),
    "budget": ("budget", "price", "under", "below", "less than", "$"),
}

# Signals that a previous preference is being replaced.
REPLACEMENT_MARKERS = (
    "actually", "instead", "ignore my earlier", "ignore the earlier",
    "rather", "change", "what i need is", "what i really need",
)
# Signals "no preference on this attribute".
NO_PREFERENCE_MARKERS = (
    "don't have a preference", "do not have a preference", "no preference",
    "doesn't matter", "does not matter", "use your judgment", "any is fine",
)

QUESTION_PROMPTS = {
    "category": "What type of product are you looking for?",
    "material": "Do you have a material preference?",
    "color": "Do you have a color preference?",
    "size": "Is there a size or fit requirement I should prioritize?",
    "style": "What style or fit do you prefer?",
    "brand": "Do you have a brand preference?",
    "budget": "What budget range should I use?",
    "feature": "Which product feature matters most to you?",
    "use_case": "What will you mainly use it for?",
    "other": "Is there another requirement that would help narrow this down?",
}
