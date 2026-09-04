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
    path("logout/", views.logout_view, name="logout"),
]