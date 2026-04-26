from django.db import models
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Source(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    rss_url = models.URLField()
    is_active = models.BooleanField(default=True)
    fetch_interval = models.PositiveIntegerField(
        default=60, help_text="Minutes between fetches"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FeedSchedule(models.Model):
    source = models.OneToOneField(
        Source, on_delete=models.CASCADE, related_name="schedule"
    )
    interval_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.source} every {self.interval_minutes}m"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_periodic_task()

    def delete(self, *args, **kwargs):
        self._delete_periodic_task()
        super().delete(*args, **kwargs)

    def _sync_periodic_task(self):
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=self.interval_minutes,
            period=IntervalSchedule.MINUTES,
        )
        PeriodicTask.objects.update_or_create(
            name=f"fetch-{self.source.slug}",
            defaults={
                "task": "feeds.tasks.fetch_and_parse_feed",
                "interval": schedule,
                "args": f'["{self.source.slug}"]',
                "enabled": self.is_active,
            },
        )

    def _delete_periodic_task(self):
        from django_celery_beat.models import PeriodicTask

        PeriodicTask.objects.filter(name=f"fetch-{self.source.slug}").delete()


class FetchLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        PARTIAL = "PARTIAL", "Partial"
        FAILED = "FAILED", "Failed"

    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, related_name="fetch_logs"
    )
    fetched_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    items_found = models.PositiveIntegerField(default=0)
    items_new = models.PositiveIntegerField(default=0)
    items_stored = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-fetched_at"]
        indexes = [
            models.Index(fields=["source", "-fetched_at"]),
        ]

    def __str__(self):
        return f"{self.source} — {self.fetched_at:%Y-%m-%d %H:%M} ({self.status})"
