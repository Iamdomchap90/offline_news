import json
import math

import trafilatura


class EnrichmentError(Exception):
    pass


def enrich(canonical_url: str, fallback_description: str = '') -> dict:
    """
    Fetch and extract full article content from canonical_url.
    Returns a dict with body, reading_time, lead_image_url.
    Raises EnrichmentError on failure.
    """
    html = trafilatura.fetch_url(canonical_url)
    if not html:
        raise EnrichmentError(f'Could not fetch {canonical_url}')

    raw = trafilatura.extract(
        html,
        include_images=True,
        include_links=False,
        output_format='json',
        with_metadata=True,
    )

    if not raw:
        raise EnrichmentError(f'trafilatura returned no content for {canonical_url}')

    data = json.loads(raw)
    body = (data.get('text') or '').strip()

    # Thin content guard — fall back to RSS description
    if len(body) < 200:
        body = fallback_description

    lead_image_url = (data.get('image') or '').strip()

    # Try og:image from raw HTML if trafilatura found nothing
    if not lead_image_url:
        lead_image_url = _extract_og_image(html)

    return {
        'body': body,
        'lead_image_url': lead_image_url,
        'reading_time': _reading_time(body),
    }


def _reading_time(text: str) -> int | None:
    if not text:
        return None
    words = len(text.split())
    return max(1, math.ceil(words / 200))


def _extract_og_image(html: str) -> str:
    import re
    match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not match:
        match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.IGNORECASE)
    return match.group(1).strip() if match else ''
