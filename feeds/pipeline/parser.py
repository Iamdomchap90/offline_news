import datetime
from typing import Optional

import feedparser


def parse_feed(xml_text: str) -> list[dict]:
    """
    Parse RSS/Atom XML and return a list of raw article dicts.
    Each dict contains the raw fields extracted from the feed entry.
    """
    feed = feedparser.parse(xml_text)
    items = []
    for entry in feed.entries:
        items.append({
            'title': entry.get('title', '').strip(),
            'url': entry.get('link', '').strip(),
            'description': _get_description(entry),
            'pub_date': _parse_date(entry),
            'author': entry.get('author', '').strip(),
            'lead_image_url': _get_thumbnail(entry),
        })
    return items


def _get_description(entry) -> str:
    # Prefer summary over content
    if 'summary' in entry:
        return entry.summary.strip()
    if 'content' in entry and entry.content:
        return entry.content[0].get('value', '').strip()
    return ''


def _parse_date(entry) -> Optional[datetime.datetime]:
    # feedparser normalises published_parsed to UTC struct_time
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime.datetime(*entry.updated_parsed[:6], tzinfo=datetime.timezone.utc)
    return datetime.datetime.now(tz=datetime.timezone.utc)


def _get_thumbnail(entry) -> str:
    # BBC and some others provide media:thumbnail in RSS
    media_thumbnail = entry.get('media_thumbnail')
    if media_thumbnail and isinstance(media_thumbnail, list) and media_thumbnail:
        return media_thumbnail[0].get('url', '')
    media_content = entry.get('media_content')
    if media_content and isinstance(media_content, list) and media_content:
        url = media_content[0].get('url', '')
        if url and any(url.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp')):
            return url
    return ''
