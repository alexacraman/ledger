from .models import Task
from django.shortcuts import render

def num_tasks(request):
    num_tasks = Task.objects.all().exclude(complete=True).count()
    context = {
        'num_tasks':num_tasks
    }
    return context