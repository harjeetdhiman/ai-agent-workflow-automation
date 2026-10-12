import os
import csv
from typing import Dict, Any, List, Optional
from src.tools.registry import tool_registry


def _determine_search_intent(kw: str) -> str:
    """
    Classifies search intent into 4 standard categories:
    - Transactional: buy, purchase, order, cheap, discount, coupon, shipping, price
    - Commercial: best, top, review, comparison, vs, compare, alternative
    - Informational: how to, what is, guide, tips, why, tutorial, ideas
    - Navigational: login, official, portal, support, website, brand specific
    """
    kw_lower = kw.lower()

    # Transactional intent keywords
    if any(term in kw_lower for term in ["buy", "order", "purchase", "discount", "cheap", "coupon", "price"]):
        return "Transactional"

    # Commercial investigation keywords
    if any(term in kw_lower for term in ["best", "top", "review", "vs", "compare", "comparison", "alternative"]):
        return "Commercial"

    # Informational intent keywords
    if any(term in kw_lower for term in ["how", "what", "guide", "tutorial", "tips", "difference", "learn"]):
        return "Informational"

    # Navigational intent keywords
    if any(term in kw_lower for term in ["login", "portal", "official", "support", "customer service", "website"]):
        return "Navigational"

    # Default fallback
    return "Informational"


def _map_target_page(intent: str, kw: str) -> str:
    """Maps search intent to recommended site architecture page."""
    if intent == "Transactional":
        return f"/products/{kw.replace(' ', '-')}"
    elif intent == "Commercial":
        return f"/collections/top-{kw.replace(' ', '-')}"
    elif intent == "Informational":
        return f"/blog/guides/{kw.replace(' ', '-')}"
    else:  # Navigational
        return "/support/portal"


@tool_registry.register("classify_seo_keywords", "Deduplicates keywords, classifies search intent, and maps to landing pages (WF008)")
def classify_seo_keywords(
    file_path: str = "data/keywords.csv",
    custom_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes WF008: SEO Keyword Classification
    - Ingests keywords and eliminates duplicate entries
    - Decision Logic: Classify each keyword as Informational, Commercial, Transactional, or Navigational
    - Maps target landing pages and calculates SEO priority
    """
    raw_keywords = []

    if custom_keywords:
        raw_keywords = [k.strip() for k in custom_keywords if k.strip()]
    elif os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                k = r.get("keyword", "").strip()
                if k:
                    raw_keywords.append({
                        "keyword": k,
                        "volume": int(r.get("search_volume", 1000)),
                        "cpc": float(r.get("cpc", 0.50))
                    })
    else:
        raise FileNotFoundError(f"Keyword file not found: {file_path}")

    # Remove duplicates
    seen_kw = set()
    deduped = []
    duplicate_count = 0

    for item in raw_keywords:
        kw_text = item["keyword"] if isinstance(item, dict) else item
        vol = item.get("volume", 1000) if isinstance(item, dict) else 1000
        cpc = item.get("cpc", 0.5) if isinstance(item, dict) else 0.5

        if kw_text.lower() in seen_kw:
            duplicate_count += 1
            continue
        seen_kw.add(kw_text.lower())

        intent = _determine_search_intent(kw_text)
        target_page = _map_target_page(intent, kw_text)

        # Priority calculation: Transactional + Commercial high volume -> High priority
        if intent in ["Transactional", "Commercial"] or vol > 10000:
            priority = "High"
        elif vol > 3000:
            priority = "Medium"
        else:
            priority = "Low"

        deduped.append({
            "keyword": kw_text,
            "search_volume": vol,
            "cpc": cpc,
            "search_intent": intent,
            "priority": priority,
            "recommended_target_page": target_page
        })

    # Summary breakdown by intent
    intent_counts = {}
    for item in deduped:
        intent_counts[item["search_intent"]] = intent_counts.get(item["search_intent"], 0) + 1

    return {
        "total_keywords_ingested": len(raw_keywords),
        "duplicates_removed": duplicate_count,
        "unique_keywords_analyzed": len(deduped),
        "intent_distribution": intent_counts,
        "classified_keywords_report": deduped
    }
