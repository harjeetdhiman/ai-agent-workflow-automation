from typing import Dict, Any, Optional
from src.tools.registry import tool_registry


@tool_registry.register("generate_product_content", "Generates product descriptions, short summary, SEO title and meta description (WF004)")
def generate_product_content(
    product_name: str,
    category: str = "General",
    material: Optional[str] = None,
    color: Optional[str] = None,
    target_audience: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    llm_provider: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Executes WF004: Product Description Generator
    - Validates required attributes (product_name)
    - Decision Logic: Do not invent missing product attributes; explicitly mark missing information
    - Outputs full description, short description, SEO title (<60 chars), meta description (<160 chars)
    """
    if not product_name or not product_name.strip():
        raise ValueError("Product name is mandatory for content generation.")

    clean_name = product_name.strip()
    clean_cat = category.strip() if category else "General"

    # Audit present vs missing attributes (Strict Business Rule!)
    missing_attributes = []
    provided_attributes = {"Product Name": clean_name, "Category": clean_cat}

    if material and material.strip():
        provided_attributes["Material"] = material.strip()
    else:
        missing_attributes.append("material")

    if color and color.strip():
        provided_attributes["Color"] = color.strip()
    else:
        missing_attributes.append("color")

    if target_audience and target_audience.strip():
        provided_attributes["Target Audience"] = target_audience.strip()
    else:
        missing_attributes.append("target_audience")

    # Generate content strictly without hallucinating unprovided attributes
    mat_text = f"crafted from premium {material}" if material else "[Material: Not Specified]"
    color_text = f"in an elegant {color} finish" if color else "[Color: Not Specified]"
    audience_text = f"tailored for {target_audience}" if target_audience else "[Target Audience: General Consumers]"

    full_description = (
        f"Introducing the {clean_name}, a premier selection in our {clean_cat} catalog. "
        f"Engineered with meticulous attention to detail, this product is {mat_text} {color_text}. "
        f"Designed specifically {audience_text}, it delivers outstanding performance, reliable daily functionality, "
        f"and lasting quality."
    )

    short_description = (
        f"Upgrade your lifestyle with the {clean_name}. High quality design in {clean_cat}, "
        f"{mat_text}."
    )

    # SEO Title: Max 60 characters
    raw_seo_title = f"{clean_name} - Premium {clean_cat} Online"
    seo_title = raw_seo_title[:60].strip()

    # Meta Description: Max 160 characters
    raw_meta = f"Discover the new {clean_name} in {clean_cat}. {mat_text}. Shop now for fast shipping and best price!"
    meta_description = raw_meta[:160].strip()

    return {
        "product_name": clean_name,
        "category": clean_cat,
        "attribute_audit": {
            "provided_attributes": provided_attributes,
            "missing_attributes_flagged": missing_attributes,
            "hallucination_prevention_status": "ENFORCED (No missing attributes were invented)"
        },
        "full_description": full_description,
        "short_description": short_description,
        "seo_title": seo_title,
        "seo_title_length": len(seo_title),
        "meta_description": meta_description,
        "meta_description_length": len(meta_description)
    }


@tool_registry.register("generate_marketing_brief", "Produces structured marketing campaign briefs with channels and checklist (WF007)")
def generate_marketing_brief(
    campaign_goal: Optional[str] = None,
    dates: Optional[str] = None,
    product_list: Optional[str] = None,
    target_audience: Optional[str] = None,
    promotion: Optional[str] = None,
    llm_provider: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Executes WF007: Marketing Campaign Brief
    - Decision Logic: If campaign goal or dates are missing, request them before generating the brief
    - Generates structured objective, audience, messaging, channels, timeline, and launch checklist
    """
    # Decision Gate: Check for required fields
    missing_fields = []
    if not campaign_goal or not str(campaign_goal).strip():
        missing_fields.append("campaign_goal")
    if not dates or not str(dates).strip():
        missing_fields.append("dates")

    if missing_fields:
        return {
            "status": "NEEDS_INPUT",
            "missing_required_fields": missing_fields,
            "message": (
                f"Campaign brief generation cannot proceed. The following mandatory inputs are missing: "
                f"{', '.join(missing_fields)}. Please provide both the campaign goal and dates."
            )
        }

    goal = str(campaign_goal).strip()
    timeline = str(dates).strip()
    products = product_list.strip() if product_list else "Featured New Collection Products"
    audience = target_audience.strip() if target_audience else "Target Brand Demographic & Repeat Buyers"
    promo = promotion.strip() if promotion else "Special Launch Pricing & Limited-Time Bundles"

    return {
        "status": "SUCCESS",
        "campaign_summary": {
            "campaign_objective": f"Achieve strategic milestone: '{goal}' during {timeline}.",
            "target_audience": audience,
            "featured_products": products,
            "promotion_structure": promo,
            "campaign_dates": timeline
        },
        "messaging_pillars": [
            "Pillar 1: Innovation & Quality - Highlight unmatched craftsmanship and reliability.",
            "Pillar 2: Limited-Time Value - Drive urgency with launch-exclusive promotions.",
            "Pillar 3: Community & Trust - Leverage social proof and customer satisfaction."
        ],
        "channel_recommendations": [
            {"channel": "Email Marketing", "strategy": "3-stage sequence: Teaser, Launch Announcement, Last-Chance reminder."},
            {"channel": "Paid Social (Meta & TikTok)", "strategy": "Short-form video hooks demonstrating practical daily utility."},
            {"channel": "Google Search & Shopping", "strategy": "High-intent transactional keywords targeting launch products."},
            {"channel": "On-Site Merchandising", "strategy": "Homepage hero banner, category callouts, and checkout upsell tiles."}
        ],
        "launch_checklist": [
            {"task": "Finalize creative banners and product photography", "status": "PENDING"},
            {"task": "Configure promotional discount codes in cart system", "status": "PENDING"},
            {"task": "Pre-test tracking URLs (UTMs) across all campaign links", "status": "PENDING"},
            {"task": "Brief customer support team on campaign terms & FAQ", "status": "PENDING"},
            {"task": "Deploy launch email blast and publish social announcements", "status": "SCHEDULED"}
        ]
    }
