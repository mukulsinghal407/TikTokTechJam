import json

from typing import Any
from pathlib import Path

class CatalogRepository:
    """Owns catalog loading and product access."""

    def __init__(self, catalog_path: str | Path) -> None:
        self.catalog_path = Path(catalog_path)
        self._products = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        products = {}

        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                product = json.loads(line)
                asin = str(product["parent_asin"])
                products[asin] = product

        return products

    def get(self, asin: str) -> dict[str, Any]:
        return self._products[asin]

    def contains(self, asin: str) -> bool:
        return asin in self._products

    def all(self):
        return self._products.values()

    def items(self):
        return self._products.items()