"""
Query fan-out and rank tracking are pure functions - these tests exercise
the real logic directly, no mocking required.
"""
from app.services.query_fanout import generate_fan_out
from app.services.rank_tracking import detect_rank_change, extract_own_rank


def test_fan_out_generates_question_variants():
    variants = generate_fan_out("packers and movers najafgarh")
    questions = [v for v in variants if v.variant_type == "question"]
    assert len(questions) == 5
    assert any("how much does" in v.term for v in questions)


def test_fan_out_generates_local_variants_from_locations():
    variants = generate_fan_out("house shifting", locations=["Najafgarh", "Dwarka"])
    local = [v for v in variants if v.variant_type == "local"]
    assert {v.term for v in local} == {"house shifting Najafgarh", "house shifting Dwarka"}


def test_fan_out_deduplicates_against_seed_term():
    variants = generate_fan_out("movers cost")  # "cost" is also a commercial modifier
    terms_lower = [v.term.lower() for v in variants]
    assert terms_lower.count("movers cost") == 0  # seed itself never appears as a variant


def test_fan_out_empty_seed_returns_empty():
    assert generate_fan_out("") == []
    assert generate_fan_out("   ") == []


def test_fan_out_produces_no_duplicate_terms():
    variants = generate_fan_out("packers movers", locations=["Delhi"])
    terms = [v.term.lower() for v in variants]
    assert len(terms) == len(set(terms))


def test_extract_own_rank_finds_matching_domain():
    results = [
        {"position": 1, "url": "https://competitor.com/movers"},
        {"position": 2, "url": "https://sureshift.in/packers-movers-delhi"},
        {"position": 3, "url": "https://another.com/movers"},
    ]
    rank = extract_own_rank(results, "sureshift.in")
    assert rank["position"] == 2
    assert rank["url"] == "https://sureshift.in/packers-movers-delhi"


def test_extract_own_rank_handles_www_prefix_either_side():
    results = [{"position": 5, "url": "https://www.sureshift.in/about"}]
    assert extract_own_rank(results, "sureshift.in")["position"] == 5
    assert extract_own_rank(results, "www.sureshift.in")["position"] == 5


def test_extract_own_rank_not_found_returns_none():
    results = [{"position": 1, "url": "https://competitor.com/movers"}]
    rank = extract_own_rank(results, "sureshift.in")
    assert rank["position"] is None
    assert rank["url"] is None


def test_detect_rank_change_gained():
    change = detect_rank_change(previous_position=10, current_position=4)
    assert change == {"change_type": "gained", "delta": 6}


def test_detect_rank_change_lost():
    change = detect_rank_change(previous_position=3, current_position=8)
    assert change == {"change_type": "lost", "delta": -5}


def test_detect_rank_change_newly_ranked():
    change = detect_rank_change(previous_position=None, current_position=7)
    assert change == {"change_type": "newly_ranked", "delta": None}


def test_detect_rank_change_dropped_out():
    change = detect_rank_change(previous_position=5, current_position=None)
    assert change == {"change_type": "dropped_out", "delta": None}


def test_detect_rank_change_unranked_both_none():
    change = detect_rank_change(previous_position=None, current_position=None)
    assert change == {"change_type": "unranked", "delta": None}


def test_detect_rank_change_unchanged():
    change = detect_rank_change(previous_position=5, current_position=5)
    assert change == {"change_type": "unchanged", "delta": 0}
