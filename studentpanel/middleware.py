from django.contrib import messages
from django.shortcuts import redirect

STUDENT_APP_NAME = "studentpanel"
STUDENT_SESSION_KEYS = ("student_enrollment", "student_class_id", "student_name")

# URL names inside studentpanel that don't need a logged-in student.
PUBLIC_URL_NAMES = {"login", "logout"}


class StudentAuthMiddleware:
    """
    Handles student authentication for every studentpanel URL, so views don't
    need their own login/logout code.

    Students are not Django User rows; they sign in with enrollment number +
    password and live in the session (student_enrollment / student_class_id).

    For studentpanel URLs this middleware:
      * sets request.student_enrollment and request.student_name
        (None / "" when the student is not signed in to *this* class)
      * LOGOUT: clears only the student's session data, adds a message and
        redirects to that class's login page
      * redirects to the login page, with a message, if a protected page is
        opened without a valid student session
    Every other app (admin, teacher, website users) is left untouched.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if match is None or match.app_name != STUDENT_APP_NAME:
            return None

        class_id = view_kwargs.get("class_id")
        enrollment = request.session.get("student_enrollment")
        logged_class = request.session.get("student_class_id")
        signed_in_here = bool(enrollment) and logged_class == class_id

        request.student_enrollment = enrollment if signed_in_here else None
        request.student_name = request.session.get("student_name", "") if signed_in_here else ""

        # ---------- logout ----------
        if match.url_name == "logout":
            self._clear_student_session(request)
            if signed_in_here:
                messages.success(request, "You've been signed out.")
            return redirect("studentpanel:login", class_id=class_id)

        # ---------- signed in, but the URL is for a different class ----------
        # e.g. signed in to class 8 and the address bar is changed to /9/...
        # Send them back to their own class instead of the other class's login.
        # (To switch classes, they log out first.)
        if enrollment and logged_class is not None and logged_class != class_id:
            messages.error(
                request,
                "That link is for a different class. Log out first if you want to sign in to another class.",
            )
            return redirect("studentpanel:exams", class_id=logged_class)

        # ---------- public pages ----------
        if match.url_name in PUBLIC_URL_NAMES or signed_in_here:
            return None

        # ---------- protected page, not signed in ----------
        messages.info(request, "Please sign in to continue.")
        return redirect("studentpanel:login", class_id=class_id)

    @staticmethod
    def _clear_student_session(request):
        # Only remove student data. session.flush() would also sign out a
        # teacher/admin logged in from the same browser.
        for key in list(request.session.keys()):
            if key in STUDENT_SESSION_KEYS or key.startswith("exam_progress_"):
                del request.session[key]