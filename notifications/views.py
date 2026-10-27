import json
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import CommitteeNotification, PushSubscription
from .forms import CommitteeNotificationForm
from .services import send_committee_push
from membership.utils import committee_required

@login_required
@committee_required
def send_notification_view(request):
    if request.method == "POST":
        form = CommitteeNotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.sent_by = request.user
            notification.save()
            result = send_committee_push(notification)
            notification.sent = result.get("sent", 0) > 0
            notification.save(update_fields=["sent"])
            messages.success(request, "Notification processed. Sent: %(sent)s Failed: %(failed)s" % result)
            return redirect("notifications:send")
    else:
        form = CommitteeNotificationForm()
    return render(request, "notifications/send.html", {"form":form})

@login_required
def list_notifications(request):
    qs = CommitteeNotification.objects.all()
    paginator = Paginator(qs, 6)
    page = request.GET.get('page')
    notifications = paginator.get_page(page)
    context = {
        "page_obj":notifications
    }
    return render(request, "notifications/list-notifications.html", context)

@committee_required
@login_required
def delete_notification(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        notification_id = data.get('id')

        notification = CommitteeNotification.objects.get(id=notification_id)
        notification.delete()

        return JsonResponse({'success': 'Notification Deleted!'})

    except CommitteeNotification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def notification_settings_view(request):
    subscription_count = PushSubscription.objects.filter(user=request.user).count()
    context = {
    "subscription_count": subscription_count,
    "VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY
    }
    return render(request, "notifications/settings.html", context)

