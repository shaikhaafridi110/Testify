import json

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from adminpanel.models import Exam
from adminpanel.utils import set_q_option


@require_POST
@login_required
def set_exam_q_option(request, exam_id):
    """
    Teacher sets how many MCQs to score students on for this exam.
    Body: {"n_questions": 5, "enrollments": ["21CE001", "21CE002"]}
    Stored in the CSV as "q1,q2,q3,q4,q5".
    - n_questions = 0  -> "" in the CSV, meaning use ALL exam questions.
    - Omit "enrollments" (or send null) to apply to the whole class roster.
    """
    try:
        exam = Exam.objects.get(id=exam_id, created_by=request.user)
    except Exam.DoesNotExist:
        return JsonResponse({"detail": "Exam not found"}, status=404)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Invalid JSON body"}, status=400)

    n_questions = body.get("n_questions")
    if n_questions is None:
        return JsonResponse({"detail": "n_questions is required"}, status=400)

    # must be a non-negative integer
    try:
        n_questions = int(n_questions)
        if n_questions < 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse(
            {"detail": "n_questions must be a non-negative integer"}, status=400
        )

    # can't ask for more questions than the exam has
    total_q = exam.questions.count()
    if n_questions > total_q:
        return JsonResponse(
            {"detail": f"Exam only has {total_q} questions"}, status=400
        )

    enrollments = body.get("enrollments")  # optional list, None = everyone
    if enrollments is not None and not isinstance(enrollments, list):
        return JsonResponse({"detail": "enrollments must be a list"}, status=400)

    try:
        updated = set_q_option(exam, n_questions, enrollments=enrollments)
    except ValueError as e:
        # e.g. no result CSV generated yet for this exam
        return JsonResponse({"detail": str(e)}, status=500)

    return JsonResponse({
        "detail": "Updated",
        "students_updated": updated,
        "q_option": f"q1..q{n_questions}" if n_questions else "",
    })