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
    Stored in the CSV as "q1,q2,q3,q4,q5". Omit "enrollments" (or send
    null) to apply to the whole class roster.
    """
    try:
        exam = Exam.objects.get(id=exam_id, created_by=request.user)
    except Exam.DoesNotExist:
        return JsonResponse({"detail": "Exam not found"}, status=404)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"detail": "Invalid JSON body"}, status=400)

    n_questions = body.get("n_questions")
    if n_questions is None:
        return JsonResponse({"detail": "n_questions is required"}, status=400)

    enrollments = body.get("enrollments")  # optional list, None = everyone
    try:
        updated = set_q_option(exam, n_questions, enrollments=enrollments)
    except ValueError as e:
        return JsonResponse({"detail": str(e)}, status=500)

    return JsonResponse({
        "detail": "Updated",
        "students_updated": updated,
        "q_option": f"q1..q{n_questions}" if n_questions else "",
    })