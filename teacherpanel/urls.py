from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),

     # ---------- Teacher: own classes ----------
    path('classes/', views.my_classes, name='my_classes'),
    path('classes/add/', views.my_class_add, name='my_class_add'),
    path('classes/<int:class_id>/edit/', views.my_class_edit, name='my_class_edit'),
    path('classes/<int:class_id>/delete/', views.my_class_delete, name='my_class_delete'),




]