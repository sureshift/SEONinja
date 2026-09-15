"""
A tiny FastAPI app standing in for a real website, with deliberately
planted technical SEO issues, served over real HTTP on localhost during
tests. This is what makes the Phase 2 crawler tests "real" - actual
network requests, actual robots.txt parsing, actual HTML parsing -
without needing network access to sureshift.in from this sandbox.

Planted issues, one of each so the detector's full range gets exercised:
  /                    - clean page (baseline, should have zero issues)
  /no-title            - missing <title>
  /no-meta             - missing meta description
  /multi-h1            - two H1 tags
  /no-h1               - no H1 tag
  /thin                - under the word-count threshold
  /noindex-page        - meta robots noindex
  /broken-link-target  - does not exist, linked from / (produces a 404)
  /redirect-me         - 302s to /redirect-target
  /redirect-target     - final destination
  /orphan              - only in sitemap.xml, not linked from anywhere
  /wrong-canonical     - canonical tag points at / instead of itself
  /duplicate-a, /duplicate-b - identical titles and descriptions
  /disallowed          - blocked via robots.txt, must NOT be crawled
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

test_app = FastAPI()

BASE_HEAD = """
<link rel="canonical" href="{canonical}">
<meta name="viewport" content="width=device-width, initial-scale=1">
"""


@test_app.get("/", response_class=HTMLResponse)
def home(request: Request):
    base = str(request.base_url).rstrip("/")
    return f"""
    <html><head>
      <title>Sure Shift Test Home</title>
      <meta name="description" content="Home page description for testing.">
      <link rel="canonical" href="{base}/">
      <script type="application/ld+json">{{"@type": "Organization", "name": "Test Co"}}</script>
    </head><body>
      <h1>Welcome</h1>
      <p>""" + ("word " * 300) + """</p>
      <a href="/no-title">No title page</a>
      <a href="/no-meta">No meta page</a>
      <a href="/multi-h1">Multi H1 page</a>
      <a href="/no-h1">No H1 page</a>
      <a href="/thin">Thin page</a>
      <a href="/noindex-page">Noindex page</a>
      <a href="/broken-link-target">Broken link</a>
      <a href="/redirect-me">Redirect page</a>
      <a href="/duplicate-a">Duplicate A</a>
      <a href="/duplicate-b">Duplicate B</a>
      <a href="/disallowed">Disallowed page</a>
      <a href="/wrong-canonical">Wrong canonical page</a>
      <a href="/cdn-cgi/l/email-protection">Protected email link</a>
      <img src="/logo.png" alt="Sure Shift logo">
      <img src="/no-alt.png">
    </body></html>
    """


@test_app.get("/no-title", response_class=HTMLResponse)
def no_title():
    return '<html><head><meta name="description" content="Has description but no title."></head><body><h1>Content</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/no-meta", response_class=HTMLResponse)
def no_meta():
    return "<html><head><title>No Meta Page</title></head><body><h1>Content</h1><p>" + ("word " * 300) + "</p></body></html>"


@test_app.get("/multi-h1", response_class=HTMLResponse)
def multi_h1():
    return '<html><head><title>Multi H1</title><meta name="description" content="desc"></head><body><h1>First</h1><h1>Second</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/no-h1", response_class=HTMLResponse)
def no_h1():
    return '<html><head><title>No H1</title><meta name="description" content="desc"></head><body><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/thin", response_class=HTMLResponse)
def thin():
    return '<html><head><title>Thin Page</title><meta name="description" content="desc"></head><body><h1>Thin</h1><p>Only a few words here.</p></body></html>'


@test_app.get("/noindex-page", response_class=HTMLResponse)
def noindex_page():
    return '<html><head><title>Noindex Page</title><meta name="description" content="desc"><meta name="robots" content="noindex, follow"></head><body><h1>Noindex</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/redirect-me")
def redirect_me():
    return RedirectResponse(url="/redirect-target", status_code=302)


@test_app.get("/redirect-target", response_class=HTMLResponse)
def redirect_target():
    return '<html><head><title>Redirect Target</title><meta name="description" content="desc"></head><body><h1>Landed</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/duplicate-a", response_class=HTMLResponse)
def duplicate_a():
    return '<html><head><title>Duplicate Title</title><meta name="description" content="Duplicate description text."></head><body><h1>A</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/duplicate-b", response_class=HTMLResponse)
def duplicate_b():
    return '<html><head><title>Duplicate Title</title><meta name="description" content="Duplicate description text."></head><body><h1>B</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/orphan", response_class=HTMLResponse)
def orphan():
    return '<html><head><title>Orphan Page</title><meta name="description" content="desc"></head><body><h1>Orphan</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/disallowed", response_class=HTMLResponse)
def disallowed():
    return '<html><head><title>Disallowed Page</title></head><body><h1>Should never be fetched</h1></body></html>'


@test_app.get("/wrong-canonical", response_class=HTMLResponse)
def wrong_canonical(request: Request):
    base = str(request.base_url).rstrip("/")
    return f'<html><head><title>Wrong Canonical Page</title><meta name="description" content="desc"><link rel="canonical" href="{base}/"></head><body><h1>Wrong Canonical</h1><p>' + ("word " * 300) + "</p></body></html>"


@test_app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    return "User-agent: *\nDisallow: /disallowed\n"


@test_app.get("/cdn-cgi/l/email-protection", response_class=HTMLResponse)
def cdn_cgi_email_protection():
    """Simulates Cloudflare's real automatic email-obfuscation endpoint -
    exists on real Cloudflare-protected sites but is never real content
    and should never be crawled."""
    return "<html><body>Cloudflare rewrote a mailto: link to this - not real content.</body></html>"


@test_app.get("/sitemap.xml")
def sitemap_xml(request: Request):
    from fastapi.responses import Response

    base = str(request.base_url).rstrip("/")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{base}/</loc></url>
  <url><loc>{base}/orphan</loc></url>
</urlset>"""
    return Response(content=xml, media_type="application/xml")
