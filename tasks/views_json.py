import json
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.utils.text import Truncator
from .models import Task
from .forms import TaskModelForm

def task_to_dict(task):
    return {
        "title": task.title,
        "slug": task.slug,
        "description": Truncator(task.description).words(10),
        "complete": task.complete,
        "created": task.created.isoformat(),
        "updated": task.updated.isoformat(),
    }

def task_to_dict_detail_view(task):
    return {
        "title": task.title,
        "slug": task.slug,
        "description":task.description,
        "complete": task.complete,
        "created": task.created.isoformat(),
        "updated": task.updated.isoformat(),
    }

@require_GET
def task_list_api(request):
    # --- Extract request parameters ---
    page_number = request.GET.get("page", 1)
    items_per_page = int(request.GET.get("per_page", 6))
    
    # --- Base queryset ---
    queryset = Task.objects.all().order_by("-created")
    
    filter = request.GET.get("complete", "")
    if filter:
        queryset = queryset.filter(
            Q(complete__icontains=filter)
        )

    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )

    # --- Pagination ---
    paginator = Paginator(queryset, items_per_page)
    page = paginator.get_page(page_number)

    # --- Serialize tasks ---
    tasks = [task_to_dict(t) for t in page.object_list]

    return JsonResponse(
        {
            "tasks": tasks,
            "page_info": {
                "page_number": page.number,
                "num_pages": paginator.num_pages,
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
                "total_items": paginator.count,
            },
        },
        status=200,
    )

@require_GET
def task_detail_api(request, slug):
    task = get_object_or_404(Task, slug=slug)
    return JsonResponse(task_to_dict_detail_view(task), status=200)


@require_POST
def task_create_api(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        payload = request.POST.dict()

    form = TaskModelForm(payload)
    if form.is_valid():
        task = form.save()
        return JsonResponse(task_to_dict(task), status=201)
    else:
        return JsonResponse({"errors": form.errors}, status=400)


@require_POST
def task_update_api(request, slug):
    task = get_object_or_404(Task, slug=slug)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        payload = request.POST.dict()

    form = TaskModelForm(payload, instance=task)
    if form.is_valid():
        task = form.save()
        return JsonResponse(task_to_dict(task), status=200)
    else:
        return JsonResponse({"errors": form.errors}, status=400)


from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def task_delete_api(request, slug):
    task = get_object_or_404(Task, slug=slug)
    completed = bool(task.complete)   # snapshot before deleting
    task.delete()
    return JsonResponse({"success": True, "completed": completed}, status=200)



