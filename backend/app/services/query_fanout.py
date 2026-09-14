"""
Module 6 - Query Fan-Out Engine. Takes a seed keyword and generates
related query variants: questions, comparisons, local/commercial/
transactional modifiers.

Deliberately template-based rather than LLM-based for Phase 3 - it's
fast, free, deterministic (testable without mocking an LLM call), and
covers the mechanical variant generation the roadmap's example shows.
An LLM-backed semantic expansion (via the LLMProvider abstraction from
Phase 0) is a reasonable Phase 3+ enhancement once real usage shows
template coverage isn't enough - not built preemptively.
"""
from dataclasses import dataclass

QUESTION_PREFIXES = ["how much does", "how to book", "what is the cost of", "is", "when to book"]
COMPARISON_TEMPLATES = ["{term} vs local movers", "best {term}", "cheapest {term}", "top rated {term}"]
COMMERCIAL_MODIFIERS = ["cost", "price", "charges", "quote", "rates"]
TRANSACTIONAL_MODIFIERS = ["near me", "booking", "online booking"]
LOCAL_MODIFIER_TEMPLATE = "{term} {location}"


@dataclass
class FanOutVariant:
    term: str
    variant_type: str  # question | comparison | commercial | transactional | local


def generate_fan_out(seed_term: str, *, locations: list[str] | None = None) -> list[FanOutVariant]:
    """
    Pure function: seed term in, list of variant terms out. No DB, no
    network - the API layer is responsible for turning these into
    Keyword rows (and deduplicating against existing keywords).
    """
    seed_term = seed_term.strip()
    if not seed_term:
        return []

    variants: list[FanOutVariant] = []
    seen: set[str] = {seed_term.lower()}

    def add(term: str, variant_type: str) -> None:
        term = term.strip()
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            variants.append(FanOutVariant(term=term, variant_type=variant_type))

    for prefix in QUESTION_PREFIXES:
        add(f"{prefix} {seed_term}", "question")

    for template in COMPARISON_TEMPLATES:
        add(template.format(term=seed_term), "comparison")

    for modifier in COMMERCIAL_MODIFIERS:
        add(f"{seed_term} {modifier}", "commercial")

    for modifier in TRANSACTIONAL_MODIFIERS:
        add(f"{seed_term} {modifier}", "transactional")

    for location in locations or []:
        add(LOCAL_MODIFIER_TEMPLATE.format(term=seed_term, location=location), "local")

    return variants
