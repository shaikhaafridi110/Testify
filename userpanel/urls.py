from django.urls import path

from . import views

# No app_name here on purpose: login/index sit at the site root, outside
# any namespace, so templates can call {% url 'login' %} / {% url 'index' %}
# directly. Include this module at the PROJECT-level urls.py with path("").
#
# Dashboard routes stay separate in userpanel/urls.py (app_name="userpanel"),
# included under "dashboard/" as before — that file is unchanged.

urlpatterns = [
    path("", views.login_view, name="login"),
    path("index/", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("features/", views.features, name="features"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),



    #exam
    path("exams/", views.exams, name="exams"),
    path("exam/<int:exam_id>/enroll/", views.enroll_exam, name="enroll_exam"),
    path("exam/attempt/<int:attempt_id>/", views.exam_attempt, name="exam_attempt"),
    path("exam/attempt/<int:attempt_id>/result/", views.exam_result, name="exam_result"),
   
    path("contact/", views.contact, name="contact"),
    path("logout/", views.logout_view, name="logout"),
]