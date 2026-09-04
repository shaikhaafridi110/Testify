from django.shortcuts import redirect
from django.contrib import messages


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/admin/"):

            # Not logged in
            if not request.user.is_authenticated:
                messages.error(
                                    request,
                                    "Access denied. Only administrators can access the admin panel."
                                )
                return redirect("login")

            # Logged in but not admin
            if request.user.role != "admin":
                messages.error(
                    request,
                    "Access denied. Only administrators can access the admin panel."
                )
                return redirect("logout")

        return self.get_response(request)