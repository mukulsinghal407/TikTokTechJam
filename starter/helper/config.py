import re

# ---------------------------------------------------------------------------
# 설정 / Config
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

# 평가기가 허용하는 ask_attribute enum. / The ask_attribute enum the evaluator allows.
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

# 내부 온톨로지는 평가기의 ask 온톨로지보다 세분화되어 있다.
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

# "이전 선호를 교체" 신호. / Signals that a previous preference is being replaced.
REPLACEMENT_MARKERS = (
    "actually", "instead", "ignore my earlier", "ignore the earlier",
    "rather", "change", "what i need is", "what i really need",
)
# "이 속성에는 선호가 없음" 신호. / Signals "no preference on this attribute".
NO_PREFERENCE_MARKERS = (
    "don't have a preference", "do not have a preference", "no preference",
    "doesn't matter", "does not matter", "use your judgment", "any is fine",
)



export = {
    "TOKEN_RE": TOKEN_RE,
    "MONEY_RE": MONEY_RE,
    "COLOR_RE": COLOR_RE,
    "MATERIAL_RE": MATERIAL_RE,
    "ALLOWED_ATTRIBUTES": ALLOWED_ATTRIBUTES,
    "STOPWORDS": STOPWORDS,
    "ATTRIBUTE_PATTERNS": ATTRIBUTE_PATTERNS,
    "REPLACEMENT_MARKERS": REPLACEMENT_MARKERS,
    "NO_PREFERENCE_MARKERS": NO_PREFERENCE_MARKERS
}


SYSTEM_PROMPT = """You are the dialogue-state module of a shopping assistant (Track 4: Shopping Copilot).
 
You are given:
- `current_attributes`: slots already tracked in this session. May be empty.
- `user_message`: the newest turn.
- `conversation_history`: the full conversation history so far in order.

Step 1 - Classify:
- ACCUMULATION (intent_changed=false): the user is still pursuing the same shopping goal \
and is adding, narrowing, or correcting a detail (e.g. "make it size M", "actually under $50").
- OVERRIDE (intent_changed=true): the user has abandoned the previous goal for a materially \
different one -- a different product type/category, or an explicit reset such as "never mind", \
"forget that", "instead show me...". If the wording is not there then it is not a OVERRIDE. There will be wording like: 'Actually, ignore my earlier preference. What I need is:'

Step 2 - Extract:
Return ONLY the attributes stated or clearly implied in `user_message` itself, in \
`attributes_this_turn`. Do not repeat values from `current_attributes` unless the user \
restates them in this message -- the caller merges or resets the state, not you.

Output result per schema.
"""

MODEL = "llama3.2:3b"  # ~2.2GB, fast on CPU. Alternatives: qwen2.5:3b, llama3.2:3b, gemma4:e2b