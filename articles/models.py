from django.db import models


class Article(models.Model):
    class Status(models.TextChoices):
        RAW = 'RAW', 'Raw'
        ENRICHED = 'ENRICHED', 'Enriched'
        ENRICH_FAILED = 'ENRICH_FAILED', 'Enrich Failed'

    source = models.ForeignKey(
        'feeds.Source',
        on_delete=models.PROTECT,
        related_name='articles',
    )

    # Identity
    url = models.URLField(max_length=2048, help_text='Original URL from RSS feed')
    canonical_url = models.URLField(max_length=2048, unique=True)
    url_hash = models.CharField(max_length=64, unique=True, db_index=True)

    # From RSS (populated at PARSE/NORMALIZE)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    pub_date = models.DateTimeField(db_index=True)
    author = models.CharField(max_length=200, blank=True)

    # From enrichment (populated at ENRICH)
    body = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    reading_time = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Minutes')
    lead_image_url = models.URLField(max_length=2048, blank=True)

    # Pipeline state
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RAW,
        db_index=True,
    )
    enrich_error = models.TextField(blank=True)
    enrich_attempts = models.PositiveSmallIntegerField(default=0)

    # Timestamps
    fetched_at = models.DateTimeField(auto_now_add=True)
    enriched_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pub_date']
        indexes = [
            models.Index(fields=['source', '-pub_date']),
            models.Index(fields=['status']),
            models.Index(fields=['-pub_date']),
        ]

    def __str__(self):
        return self.title
