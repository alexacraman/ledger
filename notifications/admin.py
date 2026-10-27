from django.contrib import admin

from .models import PushSubscription, CommitteeNotification
admin.site.register(PushSubscription)
admin.site.register(CommitteeNotification)
