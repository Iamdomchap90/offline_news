from django.contrib import admin
from django.utils.timezone import now

from .models import Article


def reenrich_selected(modeladmin, request, queryset):
    from feeds.tasks import enrich_article
    count = 0
    for article in queryset:
        article.status = Article.Status.RAW
        article.enrich_error = ''
        article.save(update_fields=['status', 'enrich_error', 'updated_at'])
        enrich_article.delay(article.id)
        count += 1
    modeladmin.message_user(request, f'Queued {count} article(s) for re-enrichment.')


reenrich_selected.short_description = 'Re-enrich selected articles'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'pub_date', 'status', 'reading_time', 'enrich_attempts']
    list_filter = ['source', 'status']
    search_fields = ['title', 'description', 'body', 'canonical_url']
    readonly_fields = [
        'url_hash', 'canonical_url', 'url',
        'fetched_at', 'enriched_at', 'updated_at',
        'enrich_attempts', 'enrich_error',
    ]
    date_hierarchy = 'pub_date'
    ordering = ['-pub_date']
    actions = [reenrich_selected]
