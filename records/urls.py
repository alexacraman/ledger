from django.urls import path
from .views import RecordListView, RecordCreateView, RecordUpdateView, RecordDeleteView, WorkReportView

app_name = 'record'

urlpatterns = [
    path("record/", RecordListView.as_view(), name="record_list"),
    path("record/create/", RecordCreateView.as_view(), name="record_create"),
    path("record/report/", WorkReportView.as_view(), name="work_report"),
    path("record/<int:pk>/edit/", RecordUpdateView.as_view(), name="record_update"),
    path("record/<int:pk>/delete/", RecordDeleteView.as_view(), name="record_delete"),
]

