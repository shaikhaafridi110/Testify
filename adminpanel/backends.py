# adminpanel/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class StatusAwareBackend(ModelBackend):
    def user_can_authenticate(self, user):
        # ignore is_active, defer to your own status field
        return getattr(user, "status", None) == "active"