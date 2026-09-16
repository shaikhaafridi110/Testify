from django.shortcuts import redirect
from django.contrib import messages


class TeacherAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/teacher/"):

            # Not logged in
            if not request.user.is_authenticated:
                messages.error(
                    request,
                    "Access denied. Only teachers can access the teacher panel."
                )
                return redirect("login")

            # Logged in but not teacher
            if request.user.role != "teacher":
                messages.error(request, "Access denied. Only teachers can access the teacher panel.")
                return redirect("logout")

            # Teacher, but not yet approved
            info = getattr(request.user, "teacher_info", None)
            if not info or info.approval_status != "approved":
                messages.error(request, "Your teacher account is still pending admin approval.")
                return redirect("logout")

        return self.get_response(request)