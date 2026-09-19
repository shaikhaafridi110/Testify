from datetime import datetime, timezone as dt_timezone

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from adminpanel.models import Class, Exam, QuestionOption
from adminpanel.utils import (
    read_class_roster, derive_password, get_student_row,
    set_enrolled, record_submission, parse_q_option_count,
)

SESSION_EXPIRY_DAYS = 180  # roughly a semester


# --------------------------------------------------------------------------
# helpers
# (login checking now lives in studentpanel/middleware.py — views can rely on
#  request.student_enrollment being set for every page except login/logout)
# --------------------------------------------------------------------------

def _safe_student_row(exam, enrollment_no):
    """get_student_row() raises ValueError if no CSV exists yet — treat as None."""
    try:
        return get_student_row(exam, enrollment_no)
    except ValueError:
        return None


def _is_submitted(row):
    return row is not None and str(row["result_status"]) not in ("", "nan", "None")


def _format_submitted(value):
    """CSV stores an ISO timestamp; show it as '19 Sep 2026, 07:40 PM' in local time."""
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    if timezone.is_naive(dt):
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return timezone.localtime(dt).strftime("%d %b %Y, %I:%M %p")


# Field names an Exam might use for its closing date/time. The first one that
# exists on the model (and is set) is used — add yours here if it's different.
CLOSE_TIME_FIELDS = ("end_datetime", "end_time", "closes_at", "close_datetime", "end_date")


def _exam_close_time(exam):
    for field in CLOSE_TIME_FIELDS:
        value = getattr(exam, field, None)
        if value:
            return value
    return None


def _format_dt(dt):
    """datetime -> '25 Sep 2026, 06:00 PM' in local time ('' if not a datetime)."""
    if not hasattr(dt, "strftime"):
        return ""
    if hasattr(dt, "hour") and timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.strftime("%d %b %Y, %I:%M %p") if hasattr(dt, "hour") else dt.strftime("%d %b %Y")


# Columns in the student's CSV row that say whether they started the exam
# ("enrolled") or not ("not_enrolled"). First one found is used — add yours if different.
ENROLL_COLUMNS = ("enrollment_status", "enroll_status", "enrolled", "status")


def _is_enrolled(row):
    """True if the student started (enrolled in) the exam, False if never started."""
    if row is None:
        return False
    for col in ENROLL_COLUMNS:
        value = row.get(col)
        if value is not None and str(value).strip().lower() not in ("", "nan", "none"):
            return str(value).strip().lower() in ("enrolled", "true", "1", "yes")
    return False


def _is_past(value):
    """True if a close date/datetime has already passed."""
    if value is None:
        return False
    if hasattr(value, "hour"):                     # datetime
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        return value <= timezone.now()
    return value < timezone.localdate()            # plain date


def _creator_name(exam):
    creator = exam.created_by
    if not creator:
        return "Testify"
    return (getattr(creator, "name", "") or "").strip() or creator.email


def _question_count(exam, row):
    """Exam size, capped by this student's q_option (same rule take_exam uses)."""
    total = exam.questions.count()
    cap = parse_q_option_count(row.get("q_option")) if row is not None else None
    return min(total, cap) if cap else total


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------

def student_login(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id, status="active")

    # already signed in to this class -> straight to the exams page
    if request.student_enrollment:
        return redirect("studentpanel:exams", class_id=class_obj.id)

    if request.method == "POST":
        enrollment_no = request.POST.get("enrollment_no", "").strip()
        password = request.POST.get("password", "").strip()

        roster = read_class_roster(class_obj)
        match = roster[roster["enrollment"].astype(str) == enrollment_no]

        if match.empty or password != derive_password(enrollment_no):
            return render(request, "student/login.html", {
                "class_obj": class_obj,
                "error": "Invalid enrollment number or password.",
                "enrollment_no": enrollment_no,
            })

        name = match.iloc[0].get("name", "")
        name = "" if str(name).strip().lower() in ("nan", "none") else str(name).strip()

        request.session.cycle_key()  # new session id on login
        request.session["student_enrollment"] = enrollment_no
        request.session["student_class_id"] = class_obj.id
        request.session["student_name"] = name
        request.session.set_expiry(60 * 60 * 24 * SESSION_EXPIRY_DAYS)

        messages.success(request, f"Welcome{', ' + name if name else ''}! You're signed in.")
        return redirect("studentpanel:exams", class_id=class_obj.id)

    return render(request, "student/login.html", {"class_obj": class_obj})


def student_logout(request, class_id):
    # Logout itself is handled by StudentAuthMiddleware (it clears the student
    # session, adds the message and redirects). This view only exists so the
    # "studentpanel:logout" URL resolves.
    return redirect("studentpanel:login", class_id=class_id)


# --------------------------------------------------------------------------
# exams
# --------------------------------------------------------------------------

def exams_list(request, class_id):
    enrollment_no = request.student_enrollment

    class_obj = get_object_or_404(Class, id=class_id, status="active")
    exams = (
        Exam.objects.filter(class_obj=class_obj)
        .select_related("created_by")
        .order_by("-created_at")
    )

    available, upcoming, closed, completed = [], [], [], []
    for exam in exams:
        row = _safe_student_row(exam, enrollment_no)
        exam.creator_name = _creator_name(exam)
        exam.question_count = _question_count(exam, row)
        close_time = _exam_close_time(exam)
        exam.closes_display = _format_dt(close_time)

        # A submitted result always wins — even if the exam got closed
        # after the student finished, it still belongs in Completed.
        if _is_submitted(row):
            completed.append({
                "exam": exam,
                "submitted_display": _format_submitted(row.get("submitted_time")),
            })
            continue

        # Not submitted: "enrolled" (started) and "not_enrolled" both belong in
        # Available so the student can start/continue. Only the exam's own
        # status decides Available vs Upcoming.
        # Closed = the admin closed it, or its close time has passed.
        # Not submitted + closed: was_enrolled tells "started but never
        # submitted" apart from "never started".
        is_closed = exam.status == "closed" or (
            exam.status == "published" and _is_past(close_time)
        )
        if is_closed:
            exam.was_enrolled = _is_enrolled(row)
            closed.append(exam)
        elif exam.status == "published":
            available.append(exam)
        else:
            upcoming.append(exam)

    return render(request, "student/exams.html", {
        "class_obj": class_obj,
        "available": available,
        "upcoming": upcoming,
        "closed": closed,
        "completed": completed,
        "student_name": request.student_name,
    })


def take_exam(request, class_id, exam_id):
    """
    One question per page — GET ?q=<position> shows a question, POST with
    action=prev/skip/next/submit/submit_confirm navigates or finalizes.
    In-progress answers live in the session (no DB attempt row, since
    students aren't real User rows). Final submit writes the CSV.
    """
    enrollment_no = request.student_enrollment

    exam = Exam.objects.filter(id=exam_id, class_obj_id=class_id).first()
    if exam is None or exam.status not in ("published", "closed"):
        messages.error(request, "That exam isn't available right now.")
        return redirect("studentpanel:exams", class_id=class_id)

    # Closed by the admin -> always blocked. Close time passed -> blocked unless
    # the student already started (in-progress answers in the session), so
    # someone mid-exam can still finish and submit.
    in_progress = f"exam_progress_{exam_id}" in request.session
    if exam.status == "closed" or (_is_past(_exam_close_time(exam)) and not in_progress):
        messages.error(request, f"“{exam.title}” has closed and can no longer be started.")
        return redirect("studentpanel:exams", class_id=class_id)

    row = _safe_student_row(exam, enrollment_no)
    if row is None:
        messages.error(request, "You aren't listed for this exam. Please contact your teacher.")
        return redirect("studentpanel:exams", class_id=class_id)
    if _is_submitted(row):
        messages.info(request, "You've already submitted this exam.")
        return redirect("studentpanel:exams", class_id=class_id)

    set_enrolled(exam, enrollment_no)

    q_cap = parse_q_option_count(row.get("q_option"))
    questions = list(exam.questions.order_by("question_order").prefetch_related("options"))
    if q_cap:
        questions = questions[:q_cap]
    if not questions:
        messages.error(request, "This exam has no questions yet.")
        return redirect("studentpanel:exams", class_id=class_id)

    total_questions = len(questions)
    question_ids = [q.id for q in questions]

    session_key = f"exam_progress_{exam_id}"
    progress = request.session.get(session_key)
    if not progress or progress.get("question_ids") != question_ids:
        progress = {
            "question_ids": question_ids,
            "answers": {},  # {str(question_id): option_id (str) or None}
            "started_at": timezone.now().isoformat(),
        }
        request.session[session_key] = progress
        request.session.modified = True

    try:
        position = int(request.GET.get("q", 1))
    except ValueError:
        position = 1
    position = max(1, min(position, total_questions))

    if request.method == "POST":
        action = request.POST.get("action")
        selected = request.POST.get("selected_option")
        current_qid = str(questions[position - 1].id)

        if action == "skip":
            progress["answers"][current_qid] = None
        elif selected:
            progress["answers"][current_qid] = selected
        else:
            progress["answers"].setdefault(current_qid, None)

        request.session[session_key] = progress
        request.session.modified = True

        if action == "prev":
            return redirect(f"{request.path}?q={position - 1}")

        if action in ("skip", "next") and position < total_questions:
            return redirect(f"{request.path}?q={position + 1}")

        if action in ("submit", "submit_confirm"):
            answered = progress["answers"]
            skipped_count = sum(1 for v in answered.values() if v is None) \
                + (total_questions - len(answered))
            if action == "submit" and skipped_count > 0:
                # re-render this position; needs_confirm_submit will now be True
                return redirect(f"{request.path}?q={position}")
            return _finalize_submission(exam, enrollment_no, questions, progress, request, session_key, class_id)

    answers = progress["answers"]
    answered_count = sum(1 for v in answers.values() if v is not None)
    skipped_count = sum(1 for v in answers.values() if v is None)
    remaining_count = total_questions - len(answers)

    question = questions[position - 1]
    selected_raw = answers.get(str(question.id))
    selected_option_id = int(selected_raw) if selected_raw else None

    try:
        started_at = datetime.fromisoformat(progress["started_at"])
        elapsed = (timezone.now() - started_at).total_seconds()
    except (ValueError, TypeError):
        elapsed = 0
    remaining_seconds = max(0, exam.duration_minutes * 60 - int(elapsed))

    is_last_question = position == total_questions
    needs_confirm_submit = is_last_question and skipped_count > 0

    return render(request, "student/exam.html", {
        "exam": exam,
        "class_id": class_id,
        "question": question,
        "position": position,
        "total_questions": total_questions,
        "answered_count": answered_count,
        "skipped_count": skipped_count,
        "remaining_count": remaining_count,
        "selected_option_id": selected_option_id,
        "is_last_question": is_last_question,
        "needs_confirm_submit": needs_confirm_submit,
        "remaining_seconds": remaining_seconds,
        "error": None,
    })


def _finalize_submission(exam, enrollment_no, questions, progress, request, session_key, class_id):
    """Score against DB Question/QuestionOption, write the CSV row, clear session state."""
    answers = progress["answers"]
    correct = wrong = skip = 0
    marks_earned = 0
    max_possible = sum(q.marks for q in questions)

    for q in questions:
        selected_id = answers.get(str(q.id))
        if not selected_id:
            skip += 1
            continue
        try:
            option = QuestionOption.objects.get(id=selected_id, question=q)
        except QuestionOption.DoesNotExist:
            skip += 1
            continue
        if option.is_correct:
            correct += 1
            marks_earned += q.marks
        else:
            wrong += 1

    total = len(questions)
    percentage = (marks_earned / max_possible * 100) if max_possible else 0
    passing_threshold = (
        exam.passing_marks * (max_possible / exam.total_marks)
        if exam.total_marks else exam.passing_marks
    )
    passed = marks_earned >= passing_threshold

    record_submission(exam, enrollment_no, total, correct, wrong, skip, percentage, passed)

    if session_key in request.session:
        del request.session[session_key]
        request.session.modified = True

    messages.success(request, f"“{exam.title}” submitted successfully.")

    return redirect("studentpanel:exams", class_id=class_id)