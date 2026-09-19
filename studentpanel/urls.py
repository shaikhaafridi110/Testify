from django.urls import path, register_converter

from . import views
from .converters import ClassTokenConverter

register_converter(ClassTokenConverter, "ctoken")

app_name = "studentpanel"

urlpatterns = [
    path("<ctoken:class_id>/login/", views.student_login, name="login"),
    path("<ctoken:class_id>/logout/", views.student_logout, name="logout"),
    path("<ctoken:class_id>/exams/", views.exams_list, name="exams"),
    path("<ctoken:class_id>/exams/<int:exam_id>/", views.take_exam, name="take_exam"),
]