from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [

    path("customers/", views.customer_list, name="customer_list"),
    path("customers/add/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_update, name="customer_update"),
    path("customers/<int:pk>/deactivate/", views.customer_deactivate, name="customer_deactivate"),
    path("customers/<int:pk>/activate/", views.customer_activate, name="customer_activate"),

    path("suppliers/", views.supplier_list, name="supplier_list"), 
    path("suppliers/add/", views.supplier_create, name="supplier_create"), 
    path("suppliers/<int:pk>/", views.supplier_detail, name="supplier_detail"), 
    path("suppliers/<int:pk>/edit/", views.supplier_update, name="supplier_update"), 
    path("suppliers/<int:pk>/deactivate/", views.supplier_deactivate, name="supplier_deactivate"), 
    path("suppliers/<int:pk>/activate/", views.supplier_activate, name="supplier_activate"),


]