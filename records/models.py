from django.db import models

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone

from .utils import format_duration

class Record(models.Model):
    STATUS_CHOICES = [
    ('BACKLOG', 'Backlog'),
    ('PLANNED', 'Planned'),
    ('IN_PROGRESS', 'In Progress'),
    ('IN_REVIEW', 'In Review'),
    ('BLOCKED', 'Blocked'),
    ('ON_HOLD', 'On Hold'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
]
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='records')
    date                = models.DateField(default=timezone.now)
    project             = models.CharField(max_length=150)
    task_description    = models.TextField()
    duration_hours      = models.DecimalField( max_digits=4, decimal_places=2, validators=[MinValueValidator(0.01)], help_text="Time in decimal hours eg 1h30m = 0.90" )
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    notes               = models.TextField(blank=True, null=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Work Log"
        verbose_name_plural = "Work Logs"

    def __str__(self):
        return f"{self.user.username} - {self.date} - ({self.duration_hours}h)"

    @property
    def formatted_duration(self):
        return format_duration(self.duration_hours)

