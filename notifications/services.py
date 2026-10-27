import json
import logging
from pywebpush import webpush, WebPushException
from django.conf import settings
from .models import PushSubscription

logger = logging.getLogger(__name__)

def save_subscription_payload(user, payload):
    endpoint = payload.get("endpoint")
    if not endpoint:
        raise ValueError("Missing endpoint in subscription payload")
    sub, created = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "subscription": payload,
            "user": user
        }
    )
    return sub

def delete_subscription_by_endpoint(endpoint):
    qs = PushSubscription.objects.filter(endpoint=endpoint)
    count = qs.count()
    qs.delete()
    return count > 0

#Centralised webpush call using fresh settings each time.Avoids stale config issues in long-running processes.
def _webpush_call(subscription_info, data):
    if not settings.VAPID_PRIVATE_KEY:
        raise RuntimeError("VAPID_PRIVATE_KEY not configured")

    return webpush(
        subscription_info=subscription_info,
        data=json.dumps(data),
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={
            "sub": f"mailto:{settings.WEBPUSH_CONTACT_EMAIL}"
        },
        timeout=10
    )

# Sends a push notification to a single subscription.Automatically cleans up invalid/stale subscriptions.
def send_push_to_subscription(subscription: PushSubscription, payload: dict):
    try:
        sub_info = subscription.subscription
        if not sub_info or not sub_info.get("endpoint"):
            logger.warning("Invalid subscription payload, deleting: %s", subscription.id)
            subscription.delete()
            return False

        _webpush_call(sub_info, payload)
        logger.info("Push sent to %s", subscription.endpoint)
        return True

    except WebPushException as exc:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        logger.warning("WebPush failed for %s: %s status=%s",subscription.endpoint,exc,status_code)

        # Clean up ALL invalid subscriptions
        if status_code in (400, 403, 404, 410):
            subscription.delete()
            logger.info("Deleted invalid subscription %s (status %s)",subscription.endpoint,status_code)
        return False

    except Exception:
        logger.exception("Unexpected error sending push to %s", subscription.endpoint)
        return False

#Sends push notifications to a queryset (or all subscriptions).Returns summary of results.
def send_bulk_push(payload: dict, queryset=None):
    qs = queryset if queryset is not None else PushSubscription.objects.all()
    results = {"sent": 0, "failed": 0}

    for sub in qs.iterator():
        ok = send_push_to_subscription(sub, payload)
        if ok:
            results["sent"] += 1
        else:
            results["failed"] += 1

    logger.info("Push results: %s", results)
    return results


def send_committee_push(notification):
    payload = {
        "title": notification.title,
        "body": notification.message,
        "url": notification.url or "/",
    }
    return send_bulk_push(payload)