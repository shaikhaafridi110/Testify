from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from django.db.models import Avg, Count, Sum
from adminpanel.models import User, Exam, UserExamAttempt, Contact, Question, QuestionOption, UserExamAnswer
from adminpanel.signals import recalculate_attempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Avg, Sum, Count

import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from adminpanel.models import User


def _generate_and_send_otp(user, purpose="login_verification"):
    code = f"{random.randint(0, 999999):06d}"
    user.otp = code
    user.otp_expires_at = timezone.now() + timezone.timedelta(minutes=10)
    user.otp_purpose = purpose
    user.otp_attempts = 0
    user.save(update_fields=["otp", "otp_expires_at", "otp_purpose", "otp_attempts"])

    send_mail(
        subject="Your Testify verification code",
        message=f"Your verification code is {code}. It expires in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def _redirect_for_role(request, user):
    if user.role == "admin":
        return redirect("admin_dashboard")
    if user.role == "teacher":
        info = getattr(user, "teacher_info", None)
        if not info or info.approval_status != "approved":
            messages.error(request, "Your teacher account is still pending admin approval.")
            return redirect("login")
        return redirect("teacher_dashboard")
    return redirect("index")



@login_required

def profile(request):
    """
    Logged-in user's profile: view + edit basic info (name, phone, profile image),
    plus a quick summary of their exam performance.
    """
    user = request.user

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        profile_image = request.FILES.get("profile_image")

        errors = []

        if phone:
            if not phone.isdigit() or len(phone) != 10:
                errors.append("Phone number must be exactly 10 digits.")
            elif User.objects.filter(phone=phone).exclude(id=user.id).exists():
                errors.append("This phone number is already in use by another account.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            if name:
                user.name = name
            # allow clearing the phone field by submitting it empty
            user.phone = phone or None
            if profile_image:
                user.profile_image = profile_image
            user.save()
            messages.success(request, "Profile updated.")

        return redirect("profile")

    attempts = UserExamAttempt.objects.filter(user=user, status="submitted")
    stats = attempts.aggregate(
        avg_percentage=Avg("percentage"),
        total_score=Sum("score"),
        exams_taken=Count("id"),
    )
    exams_taken = stats["exams_taken"] or 0
    pct = round(stats["avg_percentage"] or 0, 1)
    grade, badge_class = _grade_for(pct) if exams_taken else (None, None)

    recent_attempts = (
        attempts.select_related("exam").order_by("-submitted_at")[:5]
    )

    return render(request, "profile.html", {
        "avg_percentage": pct,
        "exams_taken": exams_taken,
        "total_score": stats["total_score"] or 0,
        "grade": grade,
        "badge_class": badge_class,
        "recent_attempts": recent_attempts,
    })

@login_required
def logout_view(request):
    user = request.user
    user.status = "inactive"
    user.save(update_fields=["status"])

    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")



def login_view(request):
    """
    Single email+password login form.
      - email exists in DB  -> normal login (with OTP step if inactive)
      - email doesn't exist -> error message, back to login (no auto-create)
    """
    if request.user.is_authenticated:
        return _redirect_for_role(request, request.user)

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Please enter both email and password.")
            return redirect("login")

        user = User.objects.filter(email__iexact=email).first()

        # ---------- EMAIL NOT IN DB ----------
        if user is None:
            messages.error(request, "No account found with that email address.")
            return redirect("login")

        # ---------- EMAIL EXISTS: normal login path ----------
        if not user.check_password(password):
            messages.error(request, "Invalid password.")
            return redirect("login")

        if user.status == "blocked":
            messages.error(request, "Your account has been blocked. Please contact support.")
            return redirect("login")

        if user.status == "inactive":
            _generate_and_send_otp(user, purpose="login_verification")
            request.session["otp_user_id"] = user.pk
            messages.success(request, "We've emailed you a verification code.")
            return redirect("otp_verify")

        login(request, user, backend="adminpanel.backends.StatusAwareBackend")
        return _redirect_for_role(request, user)

    return render(request, "login.html")



def complete_profile(request):
    user_id = request.session.get("complete_profile_user_id")
    if not user_id:
        return redirect("login")

    user = get_object_or_404(User, pk=user_id)
    name_suggestion = request.session.get("complete_profile_name_suggestion", "")
    needs_password = not user.has_usable_password()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        form_context = {
            "email": user.email,
            "name": name,
            "phone": phone,
            "needs_password": needs_password,
        }

        if not name:
            messages.error(request, "Please enter your name.")
            return render(request, "complete_profile.html", form_context)

        if not phone:
            messages.error(request, "Please enter your phone number.")
            return render(request, "complete_profile.html", form_context)

        if User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
            messages.error(request, "That phone number is already in use.")
            return render(request, "complete_profile.html", form_context)

        if needs_password:
            if not password or not confirm_password:
                messages.error(request, "Please choose a password.")
                return render(request, "complete_profile.html", form_context)
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters.")
                return render(request, "complete_profile.html", form_context)
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, "complete_profile.html", form_context)

        user.name = name
        user.phone = phone
        update_fields = ["name", "phone"]

        if needs_password:
            user.set_password(password)
            update_fields.append("password")

        user.save(update_fields=update_fields)

        del request.session["complete_profile_user_id"]
        request.session.pop("complete_profile_name_suggestion", None)

        login(request, user, backend="adminpanel.backends.StatusAwareBackend")
        messages.success(request, "Welcome to Testify!")
        return redirect("index")

    return render(request, "complete_profile.html", {
        "email": user.email,
        "name": name_suggestion,
        "needs_password": needs_password,
    })



def otp_verify(request):
    user_id = request.session.get("otp_user_id")
    if not user_id:
        return redirect("login")
    user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        code = request.POST.get("otp", "").strip()

        if not user.otp or not user.otp_expires_at or timezone.now() > user.otp_expires_at:
            messages.error(request, "This code has expired. Please request a new one.")
            return redirect("otp_verify")
        if user.otp_attempts >= 5:
            messages.error(request, "Too many attempts. Please request a new code.")
            return redirect("otp_verify")
        if code != user.otp:
            user.otp_attempts += 1
            user.save(update_fields=["otp_attempts"])
            messages.error(request, "Incorrect code. Please try again.")
            return redirect("otp_verify")

        user.status = "active"
        user.otp = None
        user.otp_expires_at = None
        user.otp_verified_at = timezone.now()
        user.otp_attempts = 0
        user.save(update_fields=["status", "otp", "otp_expires_at", "otp_verified_at", "otp_attempts"])

        del request.session["otp_user_id"]
        login(request, user, backend="adminpanel.backends.StatusAwareBackend")
        return _redirect_for_role(request, user)

    return render(request, "otp_verify.html", {"email": user.email})


def otp_resend(request):
    user_id = request.session.get("otp_user_id")
    if not user_id:
        return redirect("login")
    user = get_object_or_404(User, pk=user_id)
    _generate_and_send_otp(user, purpose="login_verification")
    messages.success(request, "A new code has been sent to your email.")
    return redirect("otp_verify")







def _platform_stats():
    """
    Shared stat numbers for the public marketing pages (homepage + about).
    """
    return {
        "total_students": User.objects.filter(role="user").count(),
        "total_teachers": User.objects.filter(
            role="teacher",
            teacher_info__approval_status="approved",
        ).count(),
        "total_exams": Exam.objects.count(),
        "total_attempts": UserExamAttempt.objects.count(),
    }


def index(request):
    """Renders the public homepage with live platform stats."""
    return render(request, "index.html", _platform_stats())


def about(request):
    """Renders the public About page with live platform stats."""
    return render(request, "about.html", _platform_stats())


def features(request):
    """Renders the public Features page. Fully static — no context, no db."""
    return render(request, "features.html")


def how_it_works(request):
    """Renders the public How It Works page. Fully static — no context, no db."""
    return render(request, "how-it-works.html")


def exams(request):
    """
    Public Exams page — shows only exams the user has NOT enrolled in
    (no attempt at all): upcoming / available / closed-with-no-attempt,
    plus the sign-in-to-take-exam state for anonymous users.

    Exams the user already has an attempt for (status == 'started' or
    'submitted') are excluded entirely — completed/in-progress exams no
    longer appear on this page.
    """
    now = timezone.now()

    qs = (
        Exam.objects.filter(created_by__role="admin")
        .exclude(status="draft")
        .select_related("created_by", "class_obj")
        .order_by("start_datetime", "-created_at")
    )

    search = request.GET.get("q", "").strip()
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(subject__icontains=search))

    status_filter = request.GET.get("status", "").strip()

    attempted_exam_ids = set()
    if request.user.is_authenticated:
        attempted_exam_ids = set(
            UserExamAttempt.objects.filter(user=request.user).values_list("exam_id", flat=True)
        )

    available_list = []

    for exam_obj in qs:
        if exam_obj.id in attempted_exam_ids:
            # Already enrolled (started or submitted) -> skip entirely.
            continue

        if exam_obj.status == "closed":
            display_status = "completed"
        elif exam_obj.start_datetime and exam_obj.start_datetime > now:
            display_status = "upcoming"
        else:
            display_status = "available"

        if status_filter and display_status != status_filter:
            continue

        exam_obj.display_status = display_status
        available_list.append(exam_obj)

    paginator = Paginator(available_list, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "exams.html", {
        "exams": page_obj,
        "search": search,
        "status_filter": status_filter,
    })



@login_required
def completed_exams(request):
    """
    Lists every exam the logged-in user has submitted, most recent first,
    each linking through to its full result/review page.
    """
    attempts = (
        UserExamAttempt.objects.filter(user=request.user, status="submitted")
        .select_related("exam", "exam__class_obj")
        .order_by("-submitted_at")
    )

    search = request.GET.get("q", "").strip()
    if search:
        attempts = attempts.filter(
            Q(exam__title__icontains=search) | Q(exam__subject__icontains=search)
        )

    result_filter = request.GET.get("result", "").strip()
    if result_filter in ("pass", "fail"):
        attempts = attempts.filter(result_status=result_filter)

    paginator = Paginator(attempts, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "completed_exams.html", {
        "attempts": page_obj,
        "search": search,
        "result_filter": result_filter,
    })

@login_required
def enroll_exam(request, exam_id):
    """
    - No attempt yet -> create one (status='started'), go to question 1.
    - Attempt exists and 'submitted' -> already finished, go to result.
    - Attempt exists and 'started' -> resume at the first question that
      has no UserExamAnswer row yet (never visited).
    """
    exam = get_object_or_404(Exam, pk=exam_id)
    attempt = UserExamAttempt.objects.filter(exam=exam, user=request.user).first()

    if attempt and attempt.status == "submitted":
        return redirect("exam_result", attempt_id=attempt.pk)

    if not attempt:
        attempt = UserExamAttempt.objects.create(exam=exam, user=request.user)

    visited_ids = set(
        UserExamAnswer.objects.filter(attempt=attempt).values_list("question_id", flat=True)
    )
    question_ids = list(
        attempt.exam.questions.order_by("question_order").values_list("id", flat=True)
    )

    resume_position = len(question_ids)  # default: last question if all visited
    for i, qid in enumerate(question_ids, start=1):
        if qid not in visited_ids:
            resume_position = i
            break

    url = reverse("exam_attempt", args=[attempt.pk])
    return redirect(f"{url}?q={resume_position}")


@login_required
def exam_attempt(request, attempt_id):
    """
    One question per page, position tracked via ?q=<1-indexed>.
    """
    attempt = get_object_or_404(UserExamAttempt, pk=attempt_id, user=request.user)

    if attempt.status == "submitted":
        return redirect("exam_result", attempt_id=attempt.pk)

    questions = list(attempt.exam.questions.order_by("question_order").prefetch_related("options"))
    total_questions = len(questions)
    if total_questions == 0:
        raise Http404("This exam has no questions.")

    try:
        position = int(request.GET.get("q", 1))
    except ValueError:
        position = 1
    position = max(1, min(position, total_questions))
    current_question = questions[position - 1]
    is_last_question = position == total_questions

    error = None

    if request.method == "POST":
        action = request.POST.get("action")
        option_id = request.POST.get("selected_option")

        if action == "prev":
            if option_id:
                option = get_object_or_404(QuestionOption, pk=option_id, question=current_question)
                UserExamAnswer.objects.update_or_create(
                    attempt=attempt, question=current_question,
                    defaults={"selected_option": option, "is_correct": option.is_correct},
                )
            return redirect(f"{request.path}?q={max(1, position - 1)}")

        elif action == "skip":
            if is_last_question:
                return redirect(f"{request.path}?q={position}")
            UserExamAnswer.objects.update_or_create(
                attempt=attempt, question=current_question,
                defaults={"selected_option": None, "is_correct": False},
            )
            return redirect(f"{request.path}?q={position + 1}")

        elif action == "next":
            if not option_id:
                error = "Please select an answer, or use Skip to move on."
            else:
                option = get_object_or_404(QuestionOption, pk=option_id, question=current_question)
                UserExamAnswer.objects.update_or_create(
                    attempt=attempt, question=current_question,
                    defaults={"selected_option": option, "is_correct": option.is_correct},
                )
                next_pos = position if position >= total_questions else position + 1
                return redirect(f"{request.path}?q={next_pos}")

        elif action in ("submit", "submit_confirm"):
            if option_id:
                option = get_object_or_404(QuestionOption, pk=option_id, question=current_question)
                UserExamAnswer.objects.update_or_create(
                    attempt=attempt, question=current_question,
                    defaults={"selected_option": option, "is_correct": option.is_correct},
                )
            attempt.status = "submitted"
            attempt.submitted_at = timezone.now()
            attempt.save(update_fields=["status", "submitted_at", "updated_at"])
            recalculate_attempt(attempt)
            return redirect("exam_result", attempt_id=attempt.pk)

    existing_answers = {
        a.question_id: a
        for a in UserExamAnswer.objects.filter(attempt=attempt).select_related("selected_option")
    }
    answered_count = sum(1 for a in existing_answers.values() if a.selected_option_id)
    skipped_count = sum(1 for a in existing_answers.values() if not a.selected_option_id)
    remaining_count = total_questions - answered_count - skipped_count
    selected_option_id = (
        existing_answers[current_question.pk].selected_option_id
        if current_question.pk in existing_answers else None
    )

    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    remaining_seconds = max(0, int(attempt.exam.duration_minutes * 60 - elapsed))

    return render(request, "exam_attempt.html", {
        "attempt": attempt,
        "exam": attempt.exam,
        "question": current_question,
        "position": position,
        "total_questions": total_questions,
        "answered_count": answered_count,
        "skipped_count": skipped_count,
        "remaining_count": remaining_count,
        "is_last_question": is_last_question,
        "needs_confirm_submit": is_last_question and skipped_count > 2,
        "selected_option_id": selected_option_id,
        "remaining_seconds": remaining_seconds,
        "error": error,
    })


@login_required
def exam_result(request, attempt_id):
    """
    Full per-question review — every question in the exam, each with its
    options, the user's pick, the correct option, and a
    correct / incorrect / skipped status.
    """
    attempt = get_object_or_404(UserExamAttempt, pk=attempt_id, user=request.user)

    if attempt.status != "submitted":
        return redirect("exam_attempt", attempt_id=attempt.pk)

    questions = attempt.exam.questions.order_by("question_order").prefetch_related("options")
    answers_by_question = {
        a.question_id: a
        for a in UserExamAnswer.objects.filter(attempt=attempt).select_related("selected_option")
    }

    full_review = []
    for q in questions:
        ans = answers_by_question.get(q.id)
        correct_option = next((o for o in q.options.all() if o.is_correct), None)

        if ans and ans.selected_option_id:
            status = "correct" if ans.is_correct else "incorrect"
            selected_option = ans.selected_option
        else:
            status = "skipped"
            selected_option = None

        full_review.append({
            "question": q,
            "status": status,
            "selected_option": selected_option,
            "selected_option_id": selected_option.id if selected_option else None,
            "correct_option": correct_option,
        })

    return render(request, "exam_result.html", {
        "attempt": attempt,
        "exam": attempt.exam,
        "full_review": full_review,
    })



def _grade_for(pct):
    """Map an average percentage to a letter grade + badge style."""
    if pct >= 90:
        return "A", "badge-success"
    if pct >= 75:
        return "B", "badge-primary"
    if pct >= 60:
        return "C", "badge-warning"
    if pct >= 50:
        return "D", "badge-warning"
    return "F", "badge-error"
 


def leaderboard(request):
    """
    Public leaderboard, ranked by each student's average score % across
    every exam they've submitted. Optional filters: search by name/email,
    or narrow to a single exam's ranking instead of the overall one.
    """
    search = request.GET.get("q", "").strip()
    exam_filter = request.GET.get("exam", "").strip()

    attempts = UserExamAttempt.objects.filter(status="submitted", user__role="user")

    exam_total_marks = None
    if exam_filter:
        attempts = attempts.filter(exam__title=exam_filter)
        exam_total_marks = (
            Exam.objects.filter(title=exam_filter)
            .values_list("total_marks", flat=True)
            .first()
        )

    stats = (
        attempts.values("user")
        .annotate(
            avg_percentage=Avg("percentage"),
            total_score=Sum("score"),
            exams_taken=Count("id"),
        )
        .order_by("-avg_percentage", "-exams_taken")
    )

    users_by_id = {
        u.id: u for u in User.objects.filter(id__in=[s["user"] for s in stats])
    }

    ranking = []
    for position, s in enumerate(stats, start=1):
        user = users_by_id.get(s["user"])
        if not user:
            continue

        if search and search.lower() not in (user.name or "").lower() and search.lower() not in user.email.lower():
            continue

        pct = round(s["avg_percentage"] or 0, 1)
        grade, badge_class = _grade_for(pct)

        ranking.append({
            "rank": position,
            "user": user,
            "avg_percentage": pct,
            "total_score": s["total_score"],
            "exams_taken": s["exams_taken"],
            "grade": grade,
            "badge_class": badge_class,
        })

    exam_titles = (
        Exam.objects.filter(created_by__role="admin")
        .exclude(status="draft")
        .values_list("title", flat=True)
        .distinct()
        .order_by("title")
    )

    top3 = ranking[:3]

    paginator = Paginator(ranking, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "leaderboard.html", {
        "ranking": page_obj,
        "top3": top3,
        "search": search,
        "exam_filter": exam_filter,
        "exam_titles": exam_titles,
        "exam_total_marks": exam_total_marks,   # <-- new
    })

def contact(request):
    """
    Renders the public Contact page and handles the contact form submission.
    """
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message_text = request.POST.get("message", "").strip()

        if not all([name, email, subject, message_text]):
            messages.error(request, "Please fill in every field before sending.")
            return redirect("contact")

        Contact.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message_text,
        )

        messages.success(request, "Thanks for reaching out — we'll get back to you shortly.")
        return redirect("contact")

    return render(request, "contact.html")