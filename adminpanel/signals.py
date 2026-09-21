from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from .models import UserExamAnswer, UserExamAttempt


def recalculate_attempt(attempt):
    answers = attempt.answers.select_related('question')

    total_questions = attempt.exam.questions.count()
    correct_answers = answers.filter(is_correct=True).count()
    answered_count = answers.exclude(selected_option__isnull=True).count()
    wrong_answers = answered_count - correct_answers
    skipped_answers = total_questions - answered_count

    score = answers.filter(is_correct=True).aggregate(
        total=Sum('question__marks')
    )['total'] or 0

    total_marks = attempt.exam.total_marks or 0
    percentage = round((score / total_marks) * 100, 2) if total_marks else 0
    result_status = 'pass' if score >= attempt.exam.passing_marks else 'fail'

    UserExamAttempt.objects.filter(pk=attempt.pk).update(
        score=score,
        correct_answers=correct_answers,
        wrong_answers=wrong_answers,
        skipped_answers=skipped_answers,
        percentage=percentage,
        result_status=result_status,
    )


@receiver(post_save, sender=UserExamAnswer)
def on_answer_saved(sender, instance, **kwargs):
    recalculate_attempt(instance.attempt)


@receiver(post_delete, sender=UserExamAnswer)
def on_answer_deleted(sender, instance, **kwargs):
    recalculate_attempt(instance.attempt)








from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Exam, Question
from .utils import generate_result_csv, fill_default_q_option


@receiver(post_save, sender=Exam)
def create_result_file_on_exam_create(sender, instance, created, **kwargs):
    """
    Fires the moment a teacher/admin creates an Exam tied to a Class.
    Auto-builds the matching ExamResultFile + CSV (enrollment, status,
    q_option, ...).
    """
    if created:
        generate_result_csv(instance)
    else:
        fill_default_q_option(instance)


@receiver(post_save, sender=Question)
def on_question_saved(sender, instance, **kwargs):
    if instance.exam:
        fill_default_q_option(instance.exam)


@receiver(post_delete, sender=Question)
def on_question_deleted(sender, instance, **kwargs):
    if instance.exam:
        fill_default_q_option(instance.exam)