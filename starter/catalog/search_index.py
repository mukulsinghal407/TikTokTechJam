from __future__ import annotations

import sqlite3
from starter.catalog.repository import CatalogRepository
from starter.helper.utils import (_fts_expression,_text)


class FTS5SearchIndex:
    """SQLite FTS5 implementation of catalog search."""

    def __init__(
        self,
        catalog: CatalogRepository,
        feature_multiplier: float = 1.5,
    ) -> None:
        self.catalog = catalog
        self.feature_multiplier = feature_multiplier

        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

        self._build()

    def _build(self) -> None:
        cur = self.connection.cursor()

        cur.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, "
            "title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )

        batch = []

        for asin, product in self.catalog.items():
            batch.append(
                (
                    asin,
                    _text(product.get("title")),
                    _text(product.get("categories")),
                    _text(product.get("features")),
                    _text(product.get("details")),
                    _text(product.get("store")),
                    _text(product.get("description")),
                )
            )

            if len(batch) >= 1000:
                cur.executemany(
                    "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                    batch,
                )
                batch.clear()

        if batch:
            cur.executemany(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                batch,
            )

        self.connection.commit()

    def search(
        self,
        terms: list[str],
        limit: int,
        weights: tuple[float, ...],
    ) -> list[tuple[str, float]]:

        expr = _fts_expression(terms)

        if not expr:
            return []

        weights = list(weights)

        weights[3] *= self.feature_multiplier
        weights[1] /= self.feature_multiplier ** 0.5

        weight_sql = ", ".join(
            str(float(weight))
            for weight in weights
        )

        rows = self.connection.execute(
            f"""
            SELECT
                parent_asin,
                bm25(products, {weight_sql}) AS bm
            FROM products
            WHERE products MATCH ?
            ORDER BY bm
            LIMIT ?
            """,
            (expr, limit),
        ).fetchall()

        return [
            (
                str(row["parent_asin"]),
                max(0.0, -float(row["bm"])),
            )
            for row in rows
        ]