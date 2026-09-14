"""
robots.txt handling. Thin wrapper around urllib's RobotFileParser, fetched
over our own httpx client so it goes through the same retry/timeout path
as everything else rather than urllib's blocking one.
"""
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx


async def load_robots_txt(client: httpx.AsyncClient, root_url: str, user_agent: str) -> RobotFileParser:
    robots_url = urljoin(root_url, "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = await client.get(robots_url, timeout=10.0)
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            # No robots.txt (404) or blocked (403/5xx) - treat as "allow all",
            # which is the standard interpretation of a missing robots.txt.
            parser.parse([])
    except httpx.RequestError:
        parser.parse([])

    return parser


def is_allowed(parser: RobotFileParser, url: str, user_agent: str) -> bool:
    return parser.can_fetch(user_agent, url)
