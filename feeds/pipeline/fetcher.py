import time

import requests

FETCH_TIMEOUT = 15


def fetch_feed(rss_url: str) -> tuple[str, int]:
    """
    Download RSS XML from rss_url.
    Returns (xml_text, duration_ms).
    Raises requests.RequestException on failure.
    """
    start = time.monotonic()
    response = requests.get(
        rss_url,
        timeout=FETCH_TIMEOUT,
        headers={'User-Agent': 'offline-news/1.0 (feed reader)'},
    )
    response.raise_for_status()
    duration_ms = int((time.monotonic() - start) * 1000)
    return response.text, duration_ms
