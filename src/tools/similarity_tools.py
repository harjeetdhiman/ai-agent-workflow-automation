import os
import csv
import re
from difflib import SequenceMatcher
from typing import Dict, Any
from src.tools.registry import tool_registry


def _calculate_similarity(text1: str, text2: str) -> float:
    """
    Computes a hybrid similarity score using character sequence matching
    and token overlap to accurately detect near-duplicate products.
    """
    t1 = re.sub(r"[^\w\s]", " ", text1.lower()).strip()
    t2 = re.sub(r"[^\w\s]", " ", text2.lower()).strip()

    if not t1 or not t2:
        return 0.0

    # 1. SequenceMatcher ratio (handles spelling differences, word order, substrings)
    seq_ratio = SequenceMatcher(None, t1, t2).ratio()

    # 2. Token overlap (Jaccard)
    words1 = set(t1.split())
    words2 = set(t2.split())
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    jaccard = (intersection / union) if union > 0 else 0.0

    # Weighted hybrid: 70% sequence structure, 30% word tokens
    score = (0.70 * seq_ratio) + (0.30 * jaccard)
    return round(score, 4)


@tool_registry.register("detect_duplicate_products", "Finds exact SKU duplicates and high-similarity attribute duplicates in catalog (WF006)")
def detect_duplicate_products(
    catalog_file: str = "data/product_catalog.csv",
    similarity_threshold: float = 0.75
) -> Dict[str, Any]:
    """
    Executes WF006: Duplicate Product Detection
    - Compares identifiers & product attributes
    - Decision Logic:
      * Exact SKU match is a definite duplicate (100% confidence)
      * High attribute / title similarity (>= threshold) is a possible duplicate
    - Groups duplicates and assigns confidence levels
    """
    if not os.path.exists(catalog_file):
        raise FileNotFoundError(f"Product catalog file not found: {catalog_file}")

    products = []
    with open(catalog_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            products.append({
                "index": idx,
                "sku": row.get("sku", "").strip(),
                "product_name": row.get("product_name", "").strip(),
                "brand": row.get("brand", "").strip(),
                "category": row.get("category", "").strip(),
                "price": row.get("price", "").strip(),
                "full_text": f"{row.get('brand', '')} {row.get('product_name', '')}".strip()
            })

    definite_duplicates = []
    possible_duplicates = []
    seen_pairs = set()

    for i in range(len(products)):
        for j in range(i + 1, len(products)):
            p1 = products[i]
            p2 = products[j]

            # 1. Exact SKU Match -> Definite Duplicate
            if p1["sku"] and p2["sku"] and p1["sku"].upper() == p2["sku"].upper():
                definite_duplicates.append({
                    "type": "DEFINITE_DUPLICATE",
                    "confidence_pct": 100.0,
                    "reason": f"Exact matching SKU identifier: '{p1['sku']}'",
                    "product_a": {"sku": p1["sku"], "name": p1["product_name"], "price": p1["price"]},
                    "product_b": {"sku": p2["sku"], "name": p2["product_name"], "price": p2["price"]},
                    "similarity_score": 1.0
                })
                seen_pairs.add((i, j))
                continue

            # 2. Attribute / Name Similarity -> Possible Duplicate
            sim = _calculate_similarity(p1["full_text"], p2["full_text"])
            if sim >= similarity_threshold:
                possible_duplicates.append({
                    "type": "POSSIBLE_DUPLICATE",
                    "confidence_pct": round(sim * 100, 1),
                    "reason": f"High lexical and attribute similarity ({round(sim * 100, 1)}%)",
                    "product_a": {"sku": p1["sku"], "name": p1["product_name"], "brand": p1["brand"]},
                    "product_b": {"sku": p2["sku"], "name": p2["product_name"], "brand": p2["brand"]},
                    "similarity_score": sim
                })

    all_groups = definite_duplicates + possible_duplicates

    return {
        "catalog_file": catalog_file,
        "total_products_scanned": len(products),
        "definite_duplicates_count": len(definite_duplicates),
        "possible_duplicates_count": len(possible_duplicates),
        "total_duplicate_clusters": len(all_groups),
        "similarity_threshold_used": f"{similarity_threshold * 100}%",
        "duplicate_groups": all_groups
    }
