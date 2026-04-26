from django.contrib import admin

from .models import FetchLog, FeedSchedule, Source


class FeedScheduleInline(admin.StackedInline):
    model = FeedSchedule
    extra = 0
    max_num = 1


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'rss_url', 'fetch_interval', 'updated_at']
    list_editable = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [FeedScheduleInline]


@admin.register(FetchLog)
class FetchLogAdmin(admin.ModelAdmin):
    list_display = ['source', 'fetched_at', 'status', 'items_found', 'items_new', 'items_stored', 'duration_ms']
    list_filter = ['status', 'source']
    readonly_fields = ['source', 'fetched_at', 'status', 'items_found', 'items_new', 'items_stored', 'error_message', 'duration_ms']
    date_hierarchy = 'fetched_at'
    ordering = ['-fetched_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
