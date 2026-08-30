from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by",
    "for", "from", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "please", "some", "that", "the",
    "this", "to", "want", "with", "would", "you", "looking",
}


OVERRIDE_WORDS = [
    "actually",
    "instead",
    "rather",
    "prefer",
    "changed my mind",
    "never mind",
    "forget",
    "scratch that",
    "on second thought",
]


CATEGORIES = [
    "hoodie",
    "shirt",
    "t-shirt",
    "jacket",
    "coat",
    "dress",
    "leggings",
    "pants",
    "shorts",
    "sweatshirt",
    "underwear",
    "jeans",
]


MATERIALS = [
    "cotton",
    "wool",
    "fleece",
    "silk",
    "polyester",
    "leather",
]


COLORS = [
    "black",
    "white",
    "blue",
    "red",
    "green",
    "gray",
    "grey",
    "pink",
    "brown",
]


def _text(value: object) -> str:

    if value is None:
        return ""

    if isinstance(value, dict):
        return " ".join(
            f"{k} {v}"
            for k, v in value.items()
        )

    if isinstance(value, list):
        return " ".join(str(x) for x in value)

    return str(value)


def _terms(text: str) -> listreturn [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1
        and token.lower() not in STOPWORDS
    ]


def is_override(text: str) -> bool:

    text = text.lower()

    return any(
        word in text
        for word in OVERRIDE_WORDS
    )


def extract_attributes(text: str, state: dict) -> None:

    text = text.lower()

    for category in CATEGORIES:
        if category in text:
            state["category"] = category

    for material in MATERIALS:
        if material in text:
            state["material"] = material

    for color in COLORS:
        if color in text:
            state["color"] = color


class Agent:

    QUESTION_MAP = {
        "category":
            "What type of clothing are you looking for?",

        "use_case":
            "What will you mainly use it for, such as casual wear, work, exercise, travel, or cold weather?",

        "material":
            "Do you have a preferred material such as cotton, fleece, wool, or performance fabric?",

        "style":
            "What style do you prefer, such as casual, athletic, classic, or trendy?",

        "budget":
            "Do you have a budget range in mind?",

        "brand":
            "Do you have a preferred brand?",

        "color":
            "Do you have a preferred color?",

        "size":
            "What size are you looking for?"
    }

    ATTRIBUTE_ORDER = [
        "category",
        "use_case",
        "material",
        "style",
        "budget",
    ]

    def __init__(
        self,
        catalog_path: str | Path = "data/catalog.jsonl",
    ) -> None:

        self.catalog_path = Path(catalog_path)

        self.connection = sqlite3.connect(":memory:")

        self._sessions = set()
        self._profiles = {}
        self._history = {}
        self._state = {}

        self._build_index()

    def _build_index(self) -> None:

        cursor = self.connection.cursor()

        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED,"
            "title,"
            "categories,"
            "features,"
            "details,"
            "store,"
            "description,"
            "tokenize='unicode61 remove_diacritics 2'"
            ")"
        )

        batch = []

        with self.catalog_path.open(
            encoding="utf-8"
        ) as handle:

            for line in handle:

                product = json.loads(line)

                batch.append(
                    (
                        str(product["parent_asin"]),
                        _text(product.get("title")),
                        _text(product.get("categories")),
                        _text(product.get("features")),
                        _text(product.get("details")),
                        _text(product.get("store")),
                        _text(product.get("description")),
                    )
                )

                if len(batch) >= 1000:
                    cursor.executemany(
                        "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                        batch,
                    )
                    batch.clear()

        if batch:
            cursor.executemany(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                batch,
            )

        self.connection.commit()

    def next_question(
        self,
        state: dict
    ) -> str | None:

        for attribute in self.ATTRIBUTE_ORDER:

            if state.get(attribute) is None:
                return attribute

        return None

    def build_query(
        self,
        session_id: str
    ) -> str:

        parts = []

        history_text = " ".join(
            self._history[session_id]
        )

        parts.append(history_text)

        state = self._state[session_id]

        for value in state.values():

            if value:
                parts.append(str(value))

        profile = self._profiles.get(
            session_id,
            {},
        )

        for tag in profile.get(
            "preference_tags",
            [],
        ):
            parts.append(tag)

        return " ".join(parts)

    def reset(
        self,
        session_id: str,
        user_profile: dict,
    ) -> None:

        self._sessions.add(session_id)

        self._profiles[session_id] = user_profile

        self._history[session_id] = []

        self._state[session_id] = {
            "category": None,
            "use_case": None,
            "material": None,
            "style": None,
            "budget": None,
            "brand": None,
            "color": None,
            "size": None,
        }

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:

        if session_id not in self._sessions:
            raise RuntimeError(
                "reset must be called before respond"
            )

        state = self._state[session_id]

        if is_override(user_message):

            state = {
                "category": None,
                "use_case": None,
                "material": None,
                "style": None,
                "budget": None,
                "brand": None,
                "color": None,
                "size": None,
            }

            self._state[session_id] = state

            self._history[session_id] = []

        self._history[session_id].append(
            user_message
        )

        extract_attributes(
            user_message,
            state,
        )

        query_text = self.build_query(
            session_id
        )

        unique_terms = list(
            dict.fromkeys(
                _terms(query_text)
            )
        )[:40]

        expression = " OR ".join(
            f'"{term}"'
            for term in unique_terms
        )

        recommendations = []

        if expression:

            rows = self.connection.execute(
                """
                SELECT parent_asin
                FROM products
                WHERE products MATCH ?
                ORDER BY bm25(
                    products,
                    0.0,
                    6.0,
                    4.0,
                    2.5,
                    2.5,
                    1.5,
                    1.0
                )
                LIMIT ?
                """,
                (
                    expression,
                    top_k,
                ),
            ).fetchall()

            recommendations = [
                {
                    "parent_asin": str(
                        row[0]
                    )
                }
                for row in rows
            ]

        ask_attribute = self.next_question(
            state
        )

        message = self.QUESTION_MAP.get(
            ask_attribute,
            "Here are the closest matches I found."
        )

        return {
            "message": message,

            "ask_attribute": ask_attribute,

            "recommendations": recommendations,

            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
            },
        }