
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.template.defaultfilters import slugify


class Task(models.Model):
    title       = models.CharField(max_length=200)
    slug        = models.SlugField(null=True, unique=True)
    description = models.TextField(null=True, blank=True)
    complete    = models.BooleanField(default=False)
    created     = models.DateTimeField(auto_now_add=True)
    updated     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tasks:task', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)
        

#  def save(self, *args, **kwargs):
#         if not self.slug:
#             base_slug = slugify(self.first_name)
#             unique_id = str(uuid.uuid4())[:8]  # Short UUID
#             self.slug = f"{base_slug}-{unique_id}"
#         return super().save(*args, **kwargs)