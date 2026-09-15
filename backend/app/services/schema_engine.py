"""
Module 16 - Schema Engine. Detects existing JSON-LD, validates it has
required fields, and recommends additional schema types.

Hard rule from the roadmap: "The system must NEVER fabricate facts."
Every suggested schema block only uses data that was ACTUALLY found on
the page or passed in as known business facts - never invented values.
If a required field can't be populated from real data, it's left out
and flagged, not filled with a placeholder.
"""

REQUIRED_FIELDS = {
    "Organization": ["name", "url"],
    "LocalBusiness": ["name", "address", "telephone"],
    "Service": ["name", "provider"],
    "BreadcrumbList": ["itemListElement"],
    "FAQPage": ["mainEntity"],
}


def detect_schema_types(structured_data: list[dict]) -> list[str]:
    return [block.get("@type") for block in structured_data if block.get("@type")]


def validate_schema_block(block: dict) -> dict:
    """Checks a single JSON-LD block for missing required fields."""
    schema_type = block.get("@type")
    required = REQUIRED_FIELDS.get(schema_type, [])
    missing = [f for f in required if f not in block or not block[f]]
    return {
        "type": schema_type,
        "valid": len(missing) == 0,
        "missing_fields": missing,
    }


def recommend_missing_schema(
    *,
    page: dict,
    business_name: str,
    business_website: str,
    existing_types: list[str],
) -> list[dict]:
    """
    Recommends schema the page is missing, using ONLY real known data
    (business name/website from the Business record, page title/canonical
    from the actual crawl). Never invents address, phone, ratings, or
    any fact not actually available - those fields are simply omitted
    from the suggestion with a note explaining what's needed.
    """
    recommendations: list[dict] = []

    is_homepage = page.get("url", "").rstrip("/") == business_website.rstrip("/")

    if "Organization" not in existing_types and is_homepage:
        recommendations.append({
            "recommended_type": "Organization",
            "reason": "Homepage has no Organization schema - this is the baseline entity signal for the business.",
            "suggested_jsonld": {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": business_name,
                "url": business_website,
            },
        })

    if "LocalBusiness" not in existing_types and is_homepage:
        recommendations.append({
            "recommended_type": "LocalBusiness",
            "reason": (
                "No LocalBusiness schema found. NOTE: address and telephone are "
                "required fields for this schema to be complete - populate them "
                "from actual business records before deploying, do not guess."
            ),
            "suggested_jsonld": {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": business_name,
                "url": business_website,
                # address/telephone deliberately omitted - not fabricated
            },
        })

    if "BreadcrumbList" not in existing_types and not is_homepage:
        recommendations.append({
            "recommended_type": "BreadcrumbList",
            "reason": "Non-homepage page has no breadcrumb schema - helps search engines understand site hierarchy.",
            "suggested_jsonld": {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                # itemListElement requires the actual page hierarchy -
                # deliberately not guessed here, needs real site structure
            },
        })

    return recommendations
