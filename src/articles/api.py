from datetime import datetime
from typing import Annotated, Optional

from ninja import Query, Router, Schema
from ninja.errors import HttpError

from feeds.models import Source

from .models import Article


class ArticleOut(Schema):
    id: int
    title: str
    description: str
    author: str
    canonical_url: str
    pub_date: datetime
    categories: list[str]
    body: str
    reading_time: Optional[int]
    lead_image_url: str
    source_slug: str

    @staticmethod
    def resolve_source_slug(obj) -> str:
        return obj.source.slug


router = Router()


@router.get("/", response=list[ArticleOut])
def get_articles(
    request,
    category: str,
    source: str = Query(default="bbc"),
    limit: Annotated[int, Query(ge=1, le=10)] = 3,
):
    if not Source.objects.filter(slug=source).exists():
        raise HttpError(404, f"Source '{source}' not found")

    articles = (
        Article.objects.select_related("source")
        .filter(
            status=Article.Status.ENRICHED,
            source__slug=source,
            categories__contains=[category],
        )
        .order_by("-pub_date")[:limit]
    )
    return list(articles)
