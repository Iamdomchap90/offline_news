import logging

from celery import shared_task
from django.db import IntegrityError
from django.utils.timezone import now

from articles.models import Article
from feeds.models import FetchLog, Source
from feeds.pipeline.enricher import EnrichmentError, enrich
from feeds.pipeline.fetcher import fetch_feed
from feeds.pipeline.normalizer import normalize
from feeds.pipeline.parser import parse_feed

logger = logging.getLogger(__name__)

MAX_ENRICH_ATTEMPTS = 3


@shared_task
def fetch_all_active_feeds():
    """Beat entry point — fans out one fetch task per active source."""
    source_slugs = list(Source.objects.filter(is_active=True).values_list('slug', flat=True))
    for source_slug in source_slugs:
        fetch_and_parse_feed.delay(source_slug)
    logger.info('Dispatched fetch tasks for %d source(s)', len(source_slugs))


@shared_task
def fetch_and_parse_feed(source_slug: str):
    """FETCH → PARSE → DEDUPLICATE → NORMALIZE for one source."""
    try:
        source = Source.objects.get(slug=source_slug)
    except Source.DoesNotExist:
        logger.error('Source %r not found', source_slug)
        return

    log = FetchLog.objects.create(source=source, status=FetchLog.Status.PENDING)

    try:
        xml, duration_ms = fetch_feed(source.rss_url)
    except Exception as exc:
        log.status = FetchLog.Status.FAILED
        log.error_message = str(exc)
        log.save(update_fields=['status', 'error_message'])
        logger.error('Fetch failed for %s: %s', source, exc)
        return

    raw_items = parse_feed(xml)
    log.items_found = len(raw_items)
    log.duration_ms = duration_ms

    # Normalise all items first
    normalised = []
    for raw in raw_items:
        result = normalize(raw)
        if result:
            normalised.append(result)

    if not normalised:
        log.status = FetchLog.Status.SUCCESS
        log.save(update_fields=['status', 'items_found', 'duration_ms'])
        return

    # Bulk deduplication — one query for all candidate hashes
    candidate_hashes = [item['url_hash'] for item in normalised]
    existing_hashes = set(
        Article.objects.filter(url_hash__in=candidate_hashes).values_list('url_hash', flat=True)
    )
    new_items = [item for item in normalised if item['url_hash'] not in existing_hashes]
    log.items_new = len(new_items)

    stored = 0
    for item in new_items:
        pub_date = item['pub_date']
        if pub_date is None:
            pub_date = now()

        try:
            article = Article.objects.create(
                source=source,
                url=item['url'],
                canonical_url=item['canonical_url'],
                url_hash=item['url_hash'],
                title=item['title'],
                description=item['description'],
                pub_date=pub_date,
                author=item['author'],
                lead_image_url=item['lead_image_url'],
                status=Article.Status.RAW,
            )
        except IntegrityError:
            # Race condition: another worker stored this article simultaneously
            logger.debug('Duplicate article skipped: %s', item['canonical_url'])
            continue

        # Skip enrichment for video/programme pages
        if item.get('skip_enrichment'):
            article.status = Article.Status.ENRICHED
            article.save(update_fields=['status'])
        else:
            enrich_article.delay(article.id)

        stored += 1

    log.items_stored = stored
    log.status = FetchLog.Status.SUCCESS if stored == len(new_items) else FetchLog.Status.PARTIAL
    log.save(update_fields=['status', 'items_found', 'items_new', 'items_stored', 'duration_ms'])
    logger.info('%s: %d found, %d new, %d stored', source, log.items_found, log.items_new, stored)


@shared_task
def enrich_article(article_id: int):
    """ENRICH → STORE for one article."""
    try:
        article = Article.objects.get(pk=article_id)
    except Article.DoesNotExist:
        logger.error('Article %d not found', article_id)
        return

    article.enrich_attempts += 1

    try:
        result = enrich(article.canonical_url, fallback_description=article.description)
    except EnrichmentError as exc:
        article.status = Article.Status.ENRICH_FAILED
        article.enrich_error = str(exc)
        article.save(update_fields=['status', 'enrich_error', 'enrich_attempts', 'updated_at'])
        logger.warning('Enrichment failed for article %d: %s', article_id, exc)
        return

    article.body = result['body']
    article.reading_time = result['reading_time']
    # Only overwrite lead_image_url if we found something — RSS thumbnail takes priority
    if result['lead_image_url'] and not article.lead_image_url:
        article.lead_image_url = result['lead_image_url']
    article.status = Article.Status.ENRICHED
    article.enrich_error = ''
    article.enriched_at = now()
    article.save(update_fields=[
        'body', 'reading_time', 'lead_image_url',
        'status', 'enrich_error', 'enrich_attempts', 'enriched_at', 'updated_at',
    ])
    logger.info('Enriched article %d: %s', article_id, article.title[:60])


@shared_task
def retry_failed_enrichments():
    """Re-queue ENRICH_FAILED articles that haven't exceeded the attempt limit."""
    qs = Article.objects.filter(
        status=Article.Status.ENRICH_FAILED,
        enrich_attempts__lt=MAX_ENRICH_ATTEMPTS,
    ).values_list('id', flat=True)
    count = 0
    for article_id in qs:
        enrich_article.delay(article_id)
        count += 1
    if count:
        logger.info('Queued %d article(s) for retry enrichment', count)
