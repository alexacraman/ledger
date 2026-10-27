from django.urls import path
from .views import TaskList
from . import views_json
app_name = 'tasks'

urlpatterns = [
    path('', TaskList.as_view(), name='tasks'),
    # path('create/', TaskCreate.as_view(), name='task-create'),
    # path('<slug:slug>/', TaskDetail.as_view(), name='task'),
    # path('<slug:slug>/update/', TaskUpdate.as_view(), name='task-update'),
    # path('<slug:slug>/delete/', TaskDelete.as_view(), name='task-delete'),

    #json_views api
    path('api/tasks/', views_json.task_list_api, name='api_task_list'),            # GET paginated list / search
    path('api/tasks/create/', views_json.task_create_api, name='api_task_create'),# POST create
    path('api/tasks/<slug:slug>/', views_json.task_detail_api, name='api_task_detail'),  # GET one
    path('api/tasks/<slug:slug>/update/', views_json.task_update_api, name='api_task_update'), # POST update
    path('api/tasks/<slug:slug>/delete/', views_json.task_delete_api, name='api_task_delete'), # POST delete
]

