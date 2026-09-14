"""
Stands in for api.dataforseo.com (unreachable from this sandbox) so the
provider's actual HTTP client behavior - basic auth, request shape,
response parsing - gets exercised over a real socket, not mocked out.

Response shape follows DataForSEO's documented "live/regular" SERP API
contract as understood at build time - see the caveat in
app/providers/serp_provider.py's DataForSEOProvider docstring.
"""
import base64

from fastapi import FastAPI, Header, HTTPException, Request

mock_dataforseo_app = FastAPI()

VALID_LOGIN = "testuser"
VALID_PASSWORD = "testpass"


def _check_auth(authorization: str | None) -> None:
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Missing credentials")
    decoded = base64.b64decode(authorization.removeprefix("Basic ")).decode()
    login, _, password = decoded.partition(":")
    if login != VALID_LOGIN or password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@mock_dataforseo_app.post("/v3/serp/google/organic/live/regular")
async def organic_serp(request: Request, authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    body = await request.json()
    keyword = body[0]["keyword"]

    if keyword == "trigger-error":
        raise HTTPException(status_code=500, detail="Simulated upstream failure")

    return {
        "tasks": [{
            "result": [{
                "keyword": keyword,
                "items": [
                    {"type": "organic", "position": 1, "url": "https://competitor-a.com/movers", "title": "Competitor A", "domain": "competitor-a.com"},
                    {"type": "organic", "position": 2, "url": "https://sureshift.in/packers-and-movers", "title": "Sure Shift", "domain": "sureshift.in"},
                    {"type": "organic", "position": 3, "url": "https://competitor-b.com/moving", "title": "Competitor B", "domain": "competitor-b.com"},
                    {
                        "type": "people_also_ask",
                        "items": [
                            {"title": "How much do movers cost?"},
                            {"title": "How do I choose a moving company?"},
                        ],
                    },
                    {
                        "type": "featured_snippet",
                        "url": "https://competitor-a.com/movers",
                        "text": "Movers typically charge based on distance and volume.",
                    },
                    {
                        "type": "local_pack",
                        "title": "Sure Shift Relocation",
                        "rating": 4.5,
                    },
                ],
            }],
        }],
    }


@mock_dataforseo_app.post("/v3/serp/google/maps/live/regular")
async def maps_serp(request: Request, authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    return {
        "tasks": [{
            "result": [{
                "items": [
                    {"title": "Sure Shift Relocation", "rating": 4.5, "position": 1},
                    {"title": "Competitor Movers", "rating": 4.2, "position": 2},
                ],
            }],
        }],
    }
