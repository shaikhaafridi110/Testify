from django.urls import reverse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse

from userpanel.views import _generate_and_send_otp


class MyAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        user = request.user
        role = getattr(user, "role", None)

        if role == "admin":
            return reverse("admin_dashboard")

        if role == "teacher":
            info = getattr(user, "teacher_info", None)
            if not info or info.approval_status != "approved":
                messages.error(
                    request,
                    "Your teacher account is still pending admin approval. "
                    "You'll be notified by email once it's reviewed."
                )
                return reverse("login")
            return reverse("index")

        return reverse("index")


class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def _handle_inactive_or_blocked(self, request, user):
        """
        Shared status gate for both Case 1 (existing link) and Case 3
        (existing user, new Google link). Returns True if it raised a
        redirect (caller should stop), False if the user is active and
        the normal flow should continue.
        """
        if user.status == "blocked":
            messages.error(request, "Your account has been blocked. Please contact support.")
            raise ImmediateHttpResponse(redirect("login"))

        if user.status == "inactive":
            _generate_and_send_otp(user, purpose="login_verification")
            request.session["otp_user_id"] = user.pk
            messages.success(request, "We've emailed you a verification code.")
            raise ImmediateHttpResponse(redirect("otp_verify"))

        return False

    def pre_social_login(self, request, sociallogin):
        # Case 1: Google identity already linked to a user -> normal login
        if sociallogin.is_existing:
            self._handle_inactive_or_blocked(request, sociallogin.user)
            return  # active -> let allauth log this in normally

        # Not linked yet — see if an account with this email already exists
        email = sociallogin.account.extra_data.get("email", "").lower()
        if not email:
            return

        User = get_user_model()

        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # ---------- Case 2: email NOT in DB -> create user now, ----------
            # ---------- skip allauth's own signup form, and send them ----------
            # ---------- to complete_profile (mirrors the login-form auto-create) ----------
            google_name = sociallogin.account.extra_data.get("name", "") or ""

            new_user = User(
                email=email,
                name="",          # left blank on purpose — collected on complete_profile
                role="user",
                status="active",
            )
            new_user.set_unusable_password()
            new_user.save()

            # link the Google identity to this new row so future Google
            # logins for this email hit Case 1 above
            sociallogin.connect(request, new_user)

            # not logging them in yet — same as the email/password auto-create
            # flow, they finish setup first
            request.session["complete_profile_user_id"] = new_user.pk
            if google_name:
                request.session["complete_profile_name_suggestion"] = google_name

            raise ImmediateHttpResponse(redirect("complete_profile"))

        # ---------- Case 3: email exists -> check status, then link + log in ----------
        self._handle_inactive_or_blocked(request, existing_user)

        sociallogin.connect(request, existing_user)
        raise ImmediateHttpResponse(redirect("login"))