import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils import timezone
from trip.models import Trip
from .models import Task



class TaskList(LoginRequiredMixin, ListView):
    model = Task
    queryset = Task.objects.all().order_by('-created')
    paginate_by = 8

    # def get_queryset(self):
    #     search_query = self.request.GET.get('q')
    #     queryset = super().get_queryset()
    #     if search_query:
    #         queryset = queryset.filter(
    #             Q(title__icontains=search_query) | 
    #             Q(description__icontains=search_query)
    #         )
    #     return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().today()
        tomorrow = today + datetime.timedelta(days=1)
        context['today']  = today
        context['bookings'] = Trip.objects.filter(request_date__gte=today, request_date__lte=tomorrow)[:1]
        context['ended'] = Task.objects.filter(complete=True).count()
        context['search_query'] = self.request.GET.get('q') 
        context['count'] = Task.objects.filter(complete=False).count()
        return context



# from django.http import JsonResponse
# from django.core import serializers
# from django.core.paginator import Paginator
# , DetailView, CreateView, DeleteView, UpdateView
# from django.urls import reverse_lazy
# from django.shortcuts import get_object_or_404
# class TaskDetail(LoginRequiredMixin, DetailView):
#     model = Task
#     template_name = 'tasks/task_detail.html'
#     context_object_name = 'task'


# class TaskUpdate(LoginRequiredMixin, UpdateView):
#     form_class = TaskModelForm
#     model = Task
#     success_url = reverse_lazy('tasks:tasks')
#     template_name = 'tasks/task_form.html'

# class TaskDelete(LoginRequiredMixin, DeleteView):
#     model = Task
#     success_url =reverse_lazy('tasks:tasks')
    

# class TaskCreate(LoginRequiredMixin, CreateView):
#     form_class = TaskModelForm
#     model = Task
#     # success_url = reverse_lazy('tasks:tasks')

#     def form_valid(self, form):
#         form.instance.user = self.request.user
#         return super().form_valid(form)

