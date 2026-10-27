from django.contrib import admin
from .models import Task

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    
admin.site.register(Task, TaskAdmin)
