import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Tracking/campaign query parameters to strip from URLs
STRIP_PARAMS = {
    # BBC
    "xtor",
    "ns_mchannel",
    "ns_source",
    "ns_campaign",
    "ns_linkname",
    "ns_fee",
    # Guardian
    "CMP",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    # Universal
    "fbclid",
    "gclid",
    "ref",
}

# Al Jazeera programme/video URL pattern — not worth enriching
AJ_SKIP_PATTERN = re.compile(r"aljazeera\.com/(program|video|live)/", re.IGNORECASE)

# BBC iPlayer/Sounds — TV/radio episode pages, not news articles
BBC_MEDIA_PATTERN = re.compile(r"bbc\.co\.uk/(iplayer|sounds)/", re.IGNORECASE)


def normalize(raw: dict) -> dict | None:
    """
    Normalise a raw article dict. Returns a normalised dict, or None if the
    URL is unusable (empty, relative, etc.).
    """
    url = raw.get("url", "").strip()
    if not url or not url.startswith("http"):
        return None

    if BBC_MEDIA_PATTERN.search(url):
        return None

    canonical = _canonical_url(url)
    url_hash = _hash_url(canonical)

    return {
        "url": url,
        "canonical_url": canonical,
        "url_hash": url_hash,
        "title": (raw.get("title") or "").strip(),
        "description": (raw.get("description") or "").strip(),
        "pub_date": raw.get("pub_date"),
        "author": (raw.get("author") or "").strip(),
        "lead_image_url": (raw.get("lead_image_url") or "").strip(),
        "categories": raw.get("categories") or [],
        "skip_enrichment": bool(AJ_SKIP_PATTERN.search(canonical)),
    }


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip /amp suffix (BBC)
    path = re.sub(r"/amp/?$", "", parsed.path)

    # Strip tracking query params
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    cleaned = {k: v for k, v in query_params.items() if k not in STRIP_PARAMS}
    query = urlencode(cleaned, doseq=True)

    # Rebuild without fragment
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def _hash_url(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
