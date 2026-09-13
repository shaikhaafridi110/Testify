from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from adminpanel.models import User, Exam, UserExamAttempt, Contact

from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.http import Http404
from adminpanel.models import Exam, Question, QuestionOption, UserExamAttempt, UserExamAnswer
from adminpanel.signals import recalculate_attempt


@login_required
def logout_view(request):
    """
    Logs the current user out and sends them back to the login page.
    GET is enough here since this is only ever reached via a link/button
    click, not a form — no sensitive data is being submitted.
    """
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")


def login_view(request):
    """
    Handles login for admin / teacher / user in one form.
    USERNAME_FIELD on the custom User model is 'email', so
    authenticate() is called with username=email.

    Redirect rules:
      - admin   -> 'admin_dashboard'
      - teacher -> no teacher UI yet, so send to the same place as 'user'
      - user    -> 'userpanel:dashboard'
    """
    if request.user.is_authenticated:
        if request.user.role == "admin":
            return redirect("admin_dashboard")
        return redirect("index")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.status != "active":
                messages.error(request, "Your account is not active. Please contact support.")
                return redirect("login")

            login(request, user)

            if user.role == "admin":
                return redirect("admin_dashboard")

            # teacher has no dedicated dashboard template yet,
            # so fall through to the regular user dashboard
            return redirect("index")

        messages.error(request, "Invalid email or password.")
        return redirect("login")

    return render(request, "login.html")


def _platform_stats():
    """
    Shared stat numbers for the public marketing pages (homepage + about).
    Pulled live from the DB rather than hardcoded:
      - students -> role='user'
      - teachers -> role='teacher' AND approved (unapproved/rejected
        applicants shouldn't be counted as "teachers on the platform")
      - exams    -> every exam ever created (admin-owned + teacher-owned)
      - attempts -> every exam attempt ever started, used in place of a
        fabricated "uptime %" — this schema has no uptime/monitoring data,
        so attempts is a real number instead of a made-up one.
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
    """
    Renders the public homepage with live platform stats (same numbers
    shown on About — see _platform_stats for what each counts).
    """
    return render(request, "index.html", _platform_stats())


def about(request):
    """
    Renders the public About page with live platform stats (see
    _platform_stats for what each counts).
    """
    return render(request, "about.html", _platform_stats())


def features(request):
    """
    Renders the public Features page. Fully static — no context, no db.
    """
    return render(request, "features.html")


def how_it_works(request):
    """
    Renders the public How It Works page. Fully static — no context, no db.
    """
    return render(request, "how-it-works.html")





@login_required
def exams(request):
    """
    Public Exams page, split into two sections for a logged-in user:
      - completed_exams: attempt.status == 'submitted' -> View Result
      - exams (paginated, as before): everything else -> enroll/resume,
        plus the existing upcoming / closed-with-no-attempt / sign-in states.
    Anonymous users only ever see the second section.
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

    my_attempts = {}
    if request.user.is_authenticated:
        my_attempts = {
            a.exam_id: a
            for a in UserExamAttempt.objects.filter(user=request.user)
        }

    available_list = []
    completed_list = []

    for exam_obj in qs:
        if exam_obj.status == "closed":
            display_status = "completed"
        elif exam_obj.start_datetime and exam_obj.start_datetime > now:
            display_status = "upcoming"
        else:
            display_status = "available"

        if status_filter and display_status != status_filter:
            continue

        exam_obj.display_status = display_status
        attempt = my_attempts.get(exam_obj.id)
        exam_obj.my_attempt = attempt

        if attempt and attempt.status == "submitted":
            completed_list.append(exam_obj)
        else:
            available_list.append(exam_obj)

    paginator = Paginator(available_list, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "exams.html", {
        "exams": page_obj,
        "completed_exams": completed_list,
        "search": search,
        "status_filter": status_filter,
    })



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from adminpanel.models import Exam, Question, QuestionOption, UserExamAttempt, UserExamAnswer
from adminpanel.signals import recalculate_attempt


@login_required
def dashboard(request):
    return render(request, "userpanel/dashboard.html")


@login_required
def enroll_exam(request, exam_id):
    """
    - No attempt yet -> create one (status='started'), go to question 1.
    - Attempt exists and 'submitted' -> already finished, go to result.
    - Attempt exists and 'started' -> resume at the first question that
      has no UserExamAnswer row yet (never visited). Skipped questions
      DO have a row (selected_option=None), so they're correctly treated
      as "visited" and not re-shown as the resume point.
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

    Every visited question leaves behind exactly one UserExamAnswer row:
      - answered  -> selected_option is set
      - skipped   -> selected_option is explicitly None
      - unvisited -> no row at all
    This is what makes Attempted / Skipped / Remaining three accurate,
    non-overlapping counts.

    - Previous: saves a selection if one was made (does NOT create a skip
      row on its own), then steps back.
    - Skip: writes a row with selected_option=None, steps forward.
      Not offered on the last question — a spoofed skip POST there is
      just ignored and re-renders the same question.
    - Next: requires a selection — without one it re-renders with an error.
    - Submit / submit_confirm: only reachable on the last question.
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
    correct / incorrect / skipped status. Summary numbers (score,
    correct/wrong/skipped, percentage, result_status) come straight off
    the attempt row via adminpanel.signals.
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



def contact(request):
    """
    Renders the public Contact page and handles the contact form submission.

    On POST: validates required fields, saves a Contact record (status
    defaults to 'new' per the model), shows a success message, and
    redirects back to the contact page (redirect-after-post, so a
    refresh doesn't resubmit the form).
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