from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    endpoint     = models.TextField(unique=True, db_index=True)
    subscription = models.JSONField()
    created      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.endpoint

class CommitteeNotification(models.Model):
    title   = models.CharField(max_length=120)
    message = models.TextField()
    url     = models.CharField(max_length=255, blank=True)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_notifications")
    created = models.DateTimeField(auto_now_add=True)
    sent    = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

