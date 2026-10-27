import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .services import save_subscription_payload, delete_subscription_by_endpoint


@require_POST
@login_required
def subscribe(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    try:
        sub = save_subscription_payload(request.user, payload)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    return JsonResponse({"status": "ok", "id": sub.id})

@require_POST
@login_required
def unsubscribe(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    endpoint = payload.get("endpoint") or payload.get("subscription", {}).get("endpoint")
    if not endpoint:
        return HttpResponseBadRequest("Missing endpoint")
    deleted = delete_subscription_by_endpoint(endpoint)
    return JsonResponse({"status": "deleted" if deleted else "not_found"})


