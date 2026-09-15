"""
Phase 4 pure-logic tests - page quality, schema engine, image SEO,
internal linking, content gap, content decay. All of these are pure
functions, no DB/network involved, so tests exercise the real logic
directly.
"""
from app.services.content_decay import detect_decay
from app.services.content_gap import find_content_gaps
from app.services.image_seo import analyze_images
from app.services.internal_linking import analyze_internal_links, compute_link_depth
from app.services.page_quality import score_page
from app.services.schema_engine import detect_schema_types, recommend_missing_schema, validate_schema_block

# ---- Page Quality ----

def test_score_page_rewards_complete_page():
    page = {
        "title": "Packers and Movers in Delhi",
        "meta_description": "Professional relocation services in Delhi.",
        "h1": ["Packers and Movers in Delhi"],
        "h2": ["Our Services", "Why Choose Us"],
        "word_count": 800,
        "canonical_url": "https://sureshift.in/packers-movers-delhi",
        "structured_data": [{"@type": "LocalBusiness"}],
        "open_graph": {"title": "Packers and Movers"},
        "internal_links": ["a", "b", "c", "d", "e", "f"],
        "images": [{"src": "movers.jpg", "alt": "Movers loading a truck"}],
    }
    result = score_page(page)
    assert result["overall_score"] >= 90
    assert result["explanation"] == []  # no issues on a genuinely complete page


def test_score_page_penalizes_thin_broken_page():
    page = {
        "title": None,
        "meta_description": None,
        "h1": [],
        "h2": [],
        "word_count": 50,
        "canonical_url": None,
        "structured_data": [],
        "open_graph": {},
        "internal_links": [],
        "images": [{"src": "img1.jpg", "alt": None}],
    }
    result = score_page(page)
    assert result["overall_score"] < 30
    assert len(result["explanation"]) >= 5


def test_score_page_component_scores_sum_correctly_weighted():
    page = {"title": "T", "meta_description": "D", "h1": ["H"], "h2": [], "word_count": 800,
            "canonical_url": "https://x.com", "structured_data": [], "open_graph": {},
            "internal_links": [], "images": []}
    result = score_page(page)
    # Every component present in the breakdown
    assert set(result["component_scores"].keys()) == {
        "content_depth", "structure", "metadata", "structured_data", "internal_linking", "media"
    }


# ---- Schema Engine ----

def test_detect_schema_types():
    structured_data = [{"@type": "Organization"}, {"@type": "BreadcrumbList"}]
    assert detect_schema_types(structured_data) == ["Organization", "BreadcrumbList"]


def test_validate_schema_block_flags_missing_fields():
    result = validate_schema_block({"@type": "LocalBusiness", "name": "Sure Shift"})
    assert result["valid"] is False
    assert "address" in result["missing_fields"]
    assert "telephone" in result["missing_fields"]


def test_validate_schema_block_valid_when_complete():
    result = validate_schema_block({
        "@type": "LocalBusiness", "name": "Sure Shift", "address": "Delhi", "telephone": "123"
    })
    assert result["valid"] is True
    assert result["missing_fields"] == []


def test_recommend_missing_schema_never_fabricates_address():
    recommendations = recommend_missing_schema(
        page={"url": "https://sureshift.in/"},
        business_name="Sure Shift",
        business_website="https://sureshift.in/",
        existing_types=[],
    )
    local_business_rec = next(r for r in recommendations if r["recommended_type"] == "LocalBusiness")
    assert "address" not in local_business_rec["suggested_jsonld"]
    assert "telephone" not in local_business_rec["suggested_jsonld"]
    assert "do not guess" in local_business_rec["reason"]


def test_recommend_missing_schema_skips_existing_types():
    recommendations = recommend_missing_schema(
        page={"url": "https://sureshift.in/"},
        business_name="Sure Shift",
        business_website="https://sureshift.in/",
        existing_types=["Organization", "LocalBusiness"],
    )
    types_recommended = {r["recommended_type"] for r in recommendations}
    assert "Organization" not in types_recommended
    assert "LocalBusiness" not in types_recommended


def test_recommend_breadcrumb_only_for_non_homepage():
    homepage_recs = recommend_missing_schema(
        page={"url": "https://sureshift.in/"}, business_name="X",
        business_website="https://sureshift.in/", existing_types=[],
    )
    subpage_recs = recommend_missing_schema(
        page={"url": "https://sureshift.in/about"}, business_name="X",
        business_website="https://sureshift.in/", existing_types=[],
    )
    assert "BreadcrumbList" not in {r["recommended_type"] for r in homepage_recs}
    assert "BreadcrumbList" in {r["recommended_type"] for r in subpage_recs}


# ---- Image SEO ----

def test_analyze_images_flags_missing_alt():
    pages = [{"url": "https://x.com/a", "images": [{"src": "/img/photo.jpg", "alt": None, "width": "100", "height": "100"}]}]
    issues = analyze_images(pages)
    assert any(i["issue_type"] == "missing_alt_text" for i in issues)


def test_analyze_images_flags_generic_filename():
    pages = [{"url": "https://x.com/a", "images": [{"src": "/img/IMG_2024.jpg", "alt": "desc", "width": "100", "height": "100"}]}]
    issues = analyze_images(pages)
    assert any(i["issue_type"] == "generic_filename" for i in issues)


def test_analyze_images_clean_image_has_no_issues():
    pages = [{"url": "https://x.com/a", "images": [
        {"src": "/img/movers-truck-delhi.jpg", "alt": "Movers loading a truck in Delhi", "width": "800", "height": "600"}
    ]}]
    assert analyze_images(pages) == []


# ---- Internal Linking ----

def test_under_linked_page_flagged():
    pages = [
        {"url": "https://x.com/a", "internal_links": ["https://x.com/b"]},
        {"url": "https://x.com/b", "internal_links": []},
    ]
    recs = analyze_internal_links(pages, under_linked_threshold=2)
    urls_flagged = {r["url"] for r in recs}
    assert "https://x.com/b" in urls_flagged  # 1 inbound link, below threshold of 2


def test_well_linked_page_not_flagged():
    pages = [
        {"url": "https://x.com/a", "internal_links": ["https://x.com/b", "https://x.com/c"]},
        {"url": "https://x.com/c", "internal_links": ["https://x.com/b"]},
        {"url": "https://x.com/b", "internal_links": []},
    ]
    recs = analyze_internal_links(pages, under_linked_threshold=2)
    assert "https://x.com/b" not in {r["url"] for r in recs}  # 2 inbound links, meets threshold


def test_compute_link_depth_bfs():
    pages = [
        {"url": "https://x.com/", "internal_links": ["https://x.com/a"]},
        {"url": "https://x.com/a", "internal_links": ["https://x.com/b"]},
        {"url": "https://x.com/b", "internal_links": []},
    ]
    depths = compute_link_depth(pages, start_url="https://x.com/")
    assert depths["https://x.com/"] == 0
    assert depths["https://x.com/a"] == 1
    assert depths["https://x.com/b"] == 2


def test_compute_link_depth_unreachable_page_absent():
    pages = [
        {"url": "https://x.com/", "internal_links": []},
        {"url": "https://x.com/orphan", "internal_links": []},
    ]
    depths = compute_link_depth(pages, start_url="https://x.com/")
    assert "https://x.com/orphan" not in depths


# ---- Content Gap ----

def test_content_gap_missing_when_no_page_matches():
    keywords = [{"id": "kw1", "term": "international relocation services"}]
    pages = [{"url": "https://x.com/local-moving", "title": "Local Moving", "h1": ["Local Moving"], "word_count": 500}]
    gaps = find_content_gaps(keywords, pages)
    assert gaps[0]["classification"] == "missing"
    assert gaps[0]["matched_url"] is None


def test_content_gap_covered_when_page_matches_and_substantial():
    keywords = [{"id": "kw1", "term": "packers and movers delhi"}]
    pages = [{"url": "https://x.com/pm-delhi", "title": "Packers and Movers Delhi", "h1": ["Packers and Movers Delhi"], "word_count": 800}]
    gaps = find_content_gaps(keywords, pages)
    assert gaps[0]["classification"] == "covered"
    assert gaps[0]["matched_url"] == "https://x.com/pm-delhi"


def test_content_gap_weak_when_page_matches_but_thin():
    keywords = [{"id": "kw1", "term": "packers and movers delhi"}]
    pages = [{"url": "https://x.com/pm-delhi", "title": "Packers and Movers Delhi", "h1": ["Packers and Movers Delhi"], "word_count": 50}]
    gaps = find_content_gaps(keywords, pages)
    assert gaps[0]["classification"] == "weak"


# ---- Content Decay ----

def test_decay_detects_word_count_drop():
    previous = [{"url": "https://x.com/a", "word_count": 800, "h1": ["A"], "title": "A", "structured_data": []}]
    current = [{"url": "https://x.com/a", "word_count": 300, "h1": ["A"], "title": "A", "structured_data": []}]
    alerts = detect_decay(previous, current)
    assert any(a["decay_type"] == "word_count_drop" for a in alerts)


def test_decay_detects_lost_structured_data():
    previous = [{"url": "https://x.com/a", "word_count": 500, "h1": ["A"], "title": "A", "structured_data": [{"@type": "Organization"}]}]
    current = [{"url": "https://x.com/a", "word_count": 500, "h1": ["A"], "title": "A", "structured_data": []}]
    alerts = detect_decay(previous, current)
    assert any(a["decay_type"] == "lost_structured_data" for a in alerts)


def test_decay_detects_lost_h1():
    previous = [{"url": "https://x.com/a", "word_count": 500, "h1": ["Title"], "title": "A", "structured_data": []}]
    current = [{"url": "https://x.com/a", "word_count": 500, "h1": [], "title": "A", "structured_data": []}]
    alerts = detect_decay(previous, current)
    assert any(a["decay_type"] == "lost_h1" for a in alerts)


def test_decay_no_alerts_for_unchanged_page():
    page_data = {"url": "https://x.com/a", "word_count": 500, "h1": ["A"], "title": "A", "structured_data": [{"@type": "Organization"}]}
    alerts = detect_decay([page_data], [dict(page_data)])
    assert alerts == []


def test_decay_ignores_urls_not_in_both_crawls():
    previous = [{"url": "https://x.com/gone", "word_count": 500, "h1": ["A"], "title": "A", "structured_data": []}]
    current = [{"url": "https://x.com/new", "word_count": 500, "h1": ["A"], "title": "A", "structured_data": []}]
    assert detect_decay(previous, current) == []
