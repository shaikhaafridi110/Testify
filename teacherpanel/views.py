from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse,HttpResponseRedirect, HttpResponse, Http404
import csv
import io
import json
from django.core.files.base import ContentFile
from django.urls import reverse
from adminpanel.views import parse_mcq_pdf_text
from adminpanel.models import Class, Exam, Question , QuestionOption
# ============================================================================
# Add these to teacher/views.py
# (adjust the model import below to match your actual app label — this
# assumes the models live in an app called "admin", same as in admin/models.py)
# ============================================================================





@login_required
def teacher_dashboard(request):
    return render(request, 'teacher/dashboard.html')


@login_required
def my_classes(request):
    if request.user.role != 'teacher':
        messages.error(request, "You don't have access to that page.")
        return redirect('login')

    classes_qs = Class.objects.filter(teacher=request.user).annotate(
        exam_count=Count('exams')
    ).order_by('-created_at')

    # ==============================
    # DASHBOARD COUNTS
    # ==============================
    total_classes = classes_qs.count()
    active_classes = classes_qs.filter(status='active').count()
    inactive_classes = classes_qs.filter(status='inactive').count()
    completed_classes = classes_qs.filter(status='completed').count()

    # ---- search ----
    search = request.GET.get('q', '').strip()
    if search:
        classes_qs = classes_qs.filter(
            Q(class_name__icontains=search) |
            Q(course__icontains=search) |
            Q(subject__icontains=search)
        )

    # ---- filter by status ----
    status = request.GET.get('status', '').strip()
    if status:
        classes_qs = classes_qs.filter(status=status)

    # ---- pagination ----
    paginator = Paginator(classes_qs, 10)
    page_number = request.GET.get('page', 1)
    classes = paginator.get_page(page_number)

    context = {
        'classes': classes,
        'search': search,
        'status': status,

        'total_classes': total_classes,
        'active_classes': active_classes,
        'inactive_classes': inactive_classes,
        'completed_classes': completed_classes,
    }
    return render(request, 'teacher/classes.html', context)


@login_required
def my_class_add(request):
    if request.user.role != 'teacher':
        messages.error(request, "You don't have access to that page.")
        return redirect('login')

    if request.method == 'POST':
        errors = {}

        class_name = request.POST.get('class_name', '').strip()
        if not class_name:
            errors['class_name'] = 'Class name is required.'

        subject = request.POST.get('subject', '').strip()
        if not subject:
            errors['subject'] = 'Subject is required.'

        course = request.POST.get('course', '').strip()
        semester = request.POST.get('semester', '').strip()
        academic_year = request.POST.get('academic_year', '').strip()
        description = request.POST.get('description', '').strip() or None

        status = request.POST.get('status', 'active').strip()
        if status not in dict(Class.STATUS_CHOICES):
            errors['status'] = 'Invalid status.'

        student_info = request.FILES.get('student_info')
        if not student_info:
            errors['student_info'] = 'Student info file is required.'

        if errors:
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('my_class_add')

        Class.objects.create(
            teacher=request.user,
            class_name=class_name,
            subject=subject,
            course=course,
            semester=semester,
            academic_year=academic_year,
            description=description,
            status=status,
            student_info=student_info,
        )

        messages.success(request, 'Class created successfully.')
        return redirect('my_classes')

    return render(request, 'teacher/class_add.html')


@login_required
def my_class_edit(request, class_id):
    if request.user.role != 'teacher':
        messages.error(request, "You don't have access to that page.")
        return redirect('login')

    # teacher=request.user in the lookup keeps a teacher from editing
    # another teacher's class just by guessing an id in the URL.
    class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':
        errors = {}

        new_class_name = class_obj.class_name
        new_subject = class_obj.subject
        new_course = class_obj.course
        new_semester = class_obj.semester
        new_academic_year = class_obj.academic_year
        new_description = class_obj.description
        new_status = class_obj.status

        if 'class_name' in request.POST:
            new_class_name = request.POST.get('class_name', '').strip()
            if not new_class_name:
                errors['class_name'] = 'Class name is required.'

        if 'subject' in request.POST:
            new_subject = request.POST.get('subject', '').strip()
            if not new_subject:
                errors['subject'] = 'Subject is required.'

        if 'course' in request.POST:
            new_course = request.POST.get('course', '').strip()

        if 'semester' in request.POST:
            new_semester = request.POST.get('semester', '').strip()

        if 'academic_year' in request.POST:
            new_academic_year = request.POST.get('academic_year', '').strip()

        if 'description' in request.POST:
            new_description = request.POST.get('description', '').strip() or None

        if 'status' in request.POST:
            new_status = request.POST.get('status', '').strip()
            if new_status not in dict(Class.STATUS_CHOICES):
                errors['status'] = 'Invalid status.'

        if request.FILES.get('student_info'):
            class_obj.student_info = request.FILES['student_info']

        if errors:
            first_error = next(iter(errors.values()))
            if is_ajax:
                return JsonResponse({'error': first_error, 'errors': errors}, status=400)
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('my_class_edit', class_id=class_obj.id)

        class_obj.class_name = new_class_name
        class_obj.subject = new_subject
        class_obj.course = new_course
        class_obj.semester = new_semester
        class_obj.academic_year = new_academic_year
        class_obj.description = new_description
        class_obj.status = new_status
        class_obj.save()

        if is_ajax:
            return JsonResponse({
                'success': True,
                'status': class_obj.status,
                'status_display': class_obj.get_status_display(),
            })

        messages.success(request, 'Class updated successfully.')
        return redirect('my_classes')

    return render(request, 'teacher/class_edit.html', {'class_obj': class_obj})


@login_required
def my_class_delete(request, class_id):
    if request.user.role != 'teacher':
        return JsonResponse({'error': "You don't have access to that action."}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)
    class_obj.delete()

    return JsonResponse({'success': True})







@login_required
def my_exams(request):
    exams_qs = Exam.objects.filter(
        class_obj__teacher=request.user
    ).select_related('class_obj').order_by('-created_at')
 
    # ==============================
    # DASHBOARD COUNTS
    # ==============================
 
    total_exams = exams_qs.count()
    draft_exams = exams_qs.filter(status='draft').count()
    published_exams = exams_qs.filter(status='published').count()
    closed_exams = exams_qs.filter(status='closed').count()
 
    # ---- search ----
    search = request.GET.get('q', '').strip()
    if search:
        exams_qs = exams_qs.filter(
            Q(title__icontains=search) |
            Q(subject__icontains=search) |
            Q(class_obj__class_name__icontains=search)
        )
 
    # ---- filter by status ----
    status = request.GET.get('status', '').strip()
    if status:
        exams_qs = exams_qs.filter(status=status)
 
    # ---- filter by class ----
    class_id = request.GET.get('class', '').strip()
    if class_id:
        exams_qs = exams_qs.filter(class_obj_id=class_id)
 
    # ---- pagination ----
    paginator = Paginator(exams_qs, 10)
    page_number = request.GET.get('page', 1)
    exams = paginator.get_page(page_number)
 
    my_classes = Class.objects.filter(teacher=request.user).order_by('class_name')
 
    context = {
        'exams': exams,
        'search': search,
        'status': status,
        'class_id': class_id,
        'my_classes': my_classes,
 
        'total_exams': total_exams,
        'draft_exams': draft_exams,
        'published_exams': published_exams,
        'closed_exams': closed_exams,
    }
    return render(request, 'teacher/exams.html', context)
 

# ==============================================================================
# TEACHER — ADD EXAM
# ==============================================================================
 


login_required
def my_exam_add(request):
    my_classes = Class.objects.filter(teacher=request.user).order_by('class_name')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    # If we arrived here from a class-filtered exam list (?class=<id>),
    # pre-select that class on the form.
    preselect_class_id = request.GET.get('class', '').strip()
 
    if request.method == 'POST':
        errors = {}
 
        class_id = request.POST.get('class_obj', '').strip()
        title = request.POST.get('title', '').strip()
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip() or None
        duration_minutes = request.POST.get('duration_minutes', '').strip()
        total_marks = request.POST.get('total_marks', '').strip()
        passing_marks = request.POST.get('passing_marks', '').strip()
        start_datetime = request.POST.get('start_datetime') or None
        end_datetime = request.POST.get('end_datetime') or None
        status = request.POST.get('status', 'draft').strip()
 
        # Class must belong to this teacher -- never trust the posted id alone.
        class_obj = my_classes.filter(id=class_id).first()
        if not class_obj:
            errors['class_obj'] = 'Select one of your classes.'
 
        if not title:
            errors['title'] = 'Title is required.'
        if not subject:
            errors['subject'] = 'Subject is required.'
 
        if not duration_minutes or not duration_minutes.isdigit():
            errors['duration_minutes'] = 'Duration must be a whole number of minutes.'
 
        if not total_marks or not total_marks.isdigit():
            errors['total_marks'] = 'Total marks must be a whole number.'
 
        if not passing_marks or not passing_marks.isdigit():
            errors['passing_marks'] = 'Passing marks must be a whole number.'
        elif total_marks.isdigit() and int(passing_marks) > int(total_marks):
            errors['passing_marks'] = "Passing marks can't be more than total marks."
 
        if status not in dict(Exam.STATUS_CHOICES):
            errors['status'] = 'Invalid status.'
 
        # Same class can't have two exams with the same title + subject combo.
        if class_obj and title and subject and not errors.get('title') and not errors.get('subject'):
            duplicate_exists = Exam.objects.filter(
                class_obj=class_obj,
                title__iexact=title,
                subject__iexact=subject,
            ).exists()
            if duplicate_exists:
                errors['subject'] = 'This class already has an exam with this title and subject.'
 
        if errors:
            first_error = next(iter(errors.values()))
            if is_ajax:
                return JsonResponse({'error': first_error, 'errors': errors}, status=400)
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('my_exam_add')
 
        exam = Exam.objects.create(
            created_by=request.user,
            class_obj=class_obj,
            title=title,
            subject=subject,
            description=description,
            duration_minutes=int(duration_minutes),
            total_marks=int(total_marks),
            passing_marks=int(passing_marks),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status=status,
        )
 
        if is_ajax:
            return JsonResponse({
                'success': True,
                'exam_id': exam.id,
                'redirect_url': reverse('my_question_add_manual', args=[exam.id]),
            })
 
        messages.success(request, 'Exam created. Now add its questions.')
        # Straight into the (teacher-scoped) question builder for the exam
        # that was just created -- an exam with no questions yet isn't
        # really usable.
        return redirect('my_question_add', exam_id=exam.id)
 
    return render(request, 'teacher/exam_add.html', {
        'my_classes': my_classes,
        'preselect_class_id': preselect_class_id,
    })
 
# ==============================================================================
# TEACHER — EDIT EXAM
# ==============================================================================
 
@login_required

def my_exam_edit(request, exam_id):
    # Scoped to this teacher's own classes -- a teacher can't open/edit
    # another teacher's exam just by guessing an id.
    exam = get_object_or_404(Exam, id=exam_id, class_obj__teacher=request.user)
    my_classes = Class.objects.filter(teacher=request.user).order_by('class_name')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
 
    if request.method == 'POST':
        errors = {}
 
        new_title = exam.title
        new_subject = exam.subject
        new_description = exam.description
        new_duration = exam.duration_minutes
        new_total_marks = exam.total_marks
        new_passing_marks = exam.passing_marks
        new_start = exam.start_datetime
        new_end = exam.end_datetime
        new_status = exam.status
 
        if 'title' in request.POST:
            new_title = request.POST.get('title', '').strip()
            if not new_title:
                errors['title'] = 'Title is required.'
 
        if 'subject' in request.POST:
            new_subject = request.POST.get('subject', '').strip()
            if not new_subject:
                errors['subject'] = 'Subject is required.'
 
        if 'description' in request.POST:
            new_description = request.POST.get('description', '').strip() or None
 
        if 'duration_minutes' in request.POST:
            raw = request.POST.get('duration_minutes', '').strip()
            if not raw or not raw.isdigit():
                errors['duration_minutes'] = 'Duration must be a whole number of minutes.'
            else:
                new_duration = int(raw)
 
        if 'total_marks' in request.POST:
            raw = request.POST.get('total_marks', '').strip()
            if not raw or not raw.isdigit():
                errors['total_marks'] = 'Total marks must be a whole number.'
            else:
                new_total_marks = int(raw)
 
        if 'passing_marks' in request.POST:
            raw = request.POST.get('passing_marks', '').strip()
            if not raw or not raw.isdigit():
                errors['passing_marks'] = 'Passing marks must be a whole number.'
            else:
                new_passing_marks = int(raw)
 
        if not errors.get('total_marks') and not errors.get('passing_marks'):
            if new_passing_marks > new_total_marks:
                errors['passing_marks'] = "Passing marks can't be more than total marks."
 
        if 'start_datetime' in request.POST:
            new_start = request.POST.get('start_datetime') or None
 
        if 'end_datetime' in request.POST:
            new_end = request.POST.get('end_datetime') or None
 
        if 'status' in request.POST:
            new_status = request.POST.get('status', '').strip()
            if new_status not in dict(Exam.STATUS_CHOICES):
                errors['status'] = 'Invalid status.'
 
        # Guard: total_marks can't be reduced below marks already assigned
        # to this exam's questions.
        if 'total_marks' in request.POST and not errors.get('total_marks'):
            current_marks_added = sum(q.marks for q in Question.objects.filter(exam=exam))
            if new_total_marks < current_marks_added:
                errors['total_marks'] = (
                    f"Total marks can't be less than the {current_marks_added} "
                    f"mark(s) already assigned to questions in this exam."
                )
 
        if errors:
            first_error = next(iter(errors.values()))
            if is_ajax:
                return JsonResponse({'error': first_error, 'errors': errors}, status=400)
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('my_exam_edit', exam_id=exam.id)
 
        exam.title = new_title
        exam.subject = new_subject
        exam.description = new_description
        exam.duration_minutes = new_duration
        exam.total_marks = new_total_marks
        exam.passing_marks = new_passing_marks
        exam.start_datetime = new_start
        exam.end_datetime = new_end
        exam.status = new_status
        exam.save()
 
        if is_ajax:
            return JsonResponse({
                'success': True,
                'status': exam.status,
                'status_display': exam.get_status_display(),
            })
 
        messages.success(request, 'Exam updated successfully.')
        return redirect('my_exams')
 
    return render(request, 'teacher/exam_edit.html', {'exam': exam, 'my_classes': my_classes})
 
 
# ==============================================================================
# TEACHER — DELETE EXAM
# ==============================================================================
 
@login_required
def my_exam_delete(request, exam_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
 
    exam = get_object_or_404(Exam, id=exam_id, class_obj__teacher=request.user)
    exam.delete()
 
    return JsonResponse({'success': True})


 
OPTION_KEYS = ['A', 'B', 'C', 'D', 'E', 'F']
 
 
def _get_owned_exam(request, exam_id):
    """An exam that belongs to one of THIS teacher's own classes -- 404s
    (not a permission error) for anything else, so a bad id doesn't
    confirm whether the exam exists at all."""
    return get_object_or_404(Exam, id=exam_id, class_obj__teacher=request.user)
 
 
def _marks_remaining(exam, exclude_question_id=None):
    qs = Question.objects.filter(exam=exam)
    if exclude_question_id is not None:
        qs = qs.exclude(id=exclude_question_id)
    marks_used = sum(q.marks for q in qs)
    return exam.total_marks - marks_used
 
 
def _redirect_add(exam, tab):
    """Back to the combined Add Questions page, on a specific tab."""
    return HttpResponseRedirect(reverse('my_question_add', args=[exam.id]) + f'?tab={tab}')
 
 
# ==============================================================================
# TEACHER — EXAM QUESTIONS (list)
# ==============================================================================
 
@login_required
def my_exam_questions(request, exam_id):
    exam = _get_owned_exam(request, exam_id)
    questions_qs = Question.objects.filter(exam=exam).prefetch_related('options').order_by('question_order', 'id')
 
    total_questions = questions_qs.count()
    total_marks_added = sum(q.marks for q in questions_qs)
    marks_remaining = exam.total_marks - total_marks_added
 
    context = {
        'exam': exam,
        'questions': questions_qs,
        'total_questions': total_questions,
        'total_marks_added': total_marks_added,
        'marks_remaining': marks_remaining,
    }
    return render(request, 'teacher/exam_questions.html', context)
 
 
# ==============================================================================
# TEACHER — COMBINED "ADD QUESTIONS" PAGE (Manual / CSV / PDF tabs)
# ==============================================================================
 
@login_required
def my_question_add(request, exam_id):
    exam = _get_owned_exam(request, exam_id)
    marks_remaining = _marks_remaining(exam)
 
    if marks_remaining <= 0:
        messages.error(
            request,
            f'All {exam.total_marks} mark(s) for this exam have already been added to questions.'
        )
        return redirect('my_exam_questions', exam_id=exam.id)
 
    return render(request, 'teacher/question_add.html', {
        'exam': exam,
        'marks_remaining': marks_remaining,
    })
 
 
# ------------------------------------------------------------
# 1) ADD MANUALLY
# ------------------------------------------------------------
 
@login_required
def my_question_add_manual(request, exam_id):
    exam = _get_owned_exam(request, exam_id)
 
    if request.method == 'POST':
        errors = {}
 
        question_text = request.POST.get('question_text', '').strip()
        marks = request.POST.get('marks', '').strip()
        option_texts = [o.strip() for o in request.POST.getlist('option_text[]')]
        correct_index = request.POST.get('correct_option', '')
 
        filled_options = [(i, text) for i, text in enumerate(option_texts) if text]
 
        marks_remaining = _marks_remaining(exam)
 
        if not question_text:
            errors['question_text'] = 'Question text is required.'
 
        if not marks or not marks.isdigit():
            errors['marks'] = 'Marks must be a whole number.'
        elif marks_remaining <= 0:
            errors['marks'] = f'All {exam.total_marks} mark(s) for this exam have already been added.'
        elif int(marks) > marks_remaining:
            errors['marks'] = (
                f'Only {marks_remaining} mark{"s" if marks_remaining != 1 else ""} left for this exam '
                f'-- lower the marks or free some up first.'
            )
 
        if len(filled_options) < 2:
            errors['options'] = 'Add at least 2 options.'
        if correct_index == '' or not any(str(i) == correct_index for i, _ in filled_options):
            errors['correct_option'] = 'Select which option is correct.'
 
        if errors:
            first_error = next(iter(errors.values()))
            messages.error(request, first_error)
            return _redirect_add(exam, 'manual')
 
        next_order = Question.objects.filter(exam=exam).count() + 1
        question = Question.objects.create(
            exam=exam,
            question_text=question_text,
            marks=int(marks),
            question_order=next_order,
        )
 
        for key_idx, (original_idx, text) in enumerate(filled_options):
            QuestionOption.objects.create(
                question=question,
                option_key=OPTION_KEYS[key_idx],
                option_text=text,
                is_correct=(str(original_idx) == correct_index),
            )
 
        messages.success(request, 'Question added.')
 
        if 'save_add_another' in request.POST:
            if _marks_remaining(exam) <= 0:
                messages.success(request, f'All {exam.total_marks} mark(s) for this exam are now assigned.')
                return redirect('my_exam_questions', exam_id=exam.id)
            return _redirect_add(exam, 'manual')
        return redirect('my_exam_questions', exam_id=exam.id)
 
    return _redirect_add(exam, 'manual')
 
 
# ------------------------------------------------------------
# 2) ADD VIA CSV
# ------------------------------------------------------------
 
@login_required
def my_question_add_csv(request, exam_id):
    exam = _get_owned_exam(request, exam_id)
 
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
 
        if not csv_file:
            messages.error(request, 'Choose a CSV file first.')
            return _redirect_add(exam, 'csv')
 
        if not csv_file.name.lower().endswith('.csv'):
            messages.error(request, 'File must be a .csv file.')
            return _redirect_add(exam, 'csv')
 
        try:
            decoded = csv_file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            messages.error(request, 'Could not read that file. Save it as UTF-8 CSV and try again.')
            return _redirect_add(exam, 'csv')
 
        reader = csv.DictReader(io.StringIO(decoded))
        headers = {(h or '').strip().lower() for h in (reader.fieldnames or [])}
        required_cols = {'question_text', 'marks', 'option_a', 'option_b', 'correct_option'}
 
        if not required_cols.issubset(headers):
            messages.error(request, 'CSV is missing required columns. Check the example format below.')
            return _redirect_add(exam, 'csv')
 
        option_cols = ['option_a', 'option_b', 'option_c', 'option_d', 'option_e', 'option_f']
 
        next_order = Question.objects.filter(exam=exam).count()
        marks_remaining = _marks_remaining(exam)
        created_count = 0
        skipped_rows = []
        over_budget_rows = []
 
        for row_num, raw_row in enumerate(reader, start=2):
            if marks_remaining <= 0:
                break
 
            row = {(k or '').strip().lower(): (v or '').strip() for k, v in raw_row.items()}
 
            question_text = row.get('question_text', '')
            marks = row.get('marks', '')
            correct_letter = row.get('correct_option', '').upper()
            options = [row.get(col, '') for col in option_cols]
            options = [o for o in options if o]
 
            valid = (
                question_text and marks.isdigit() and len(options) >= 2
                and correct_letter in OPTION_KEYS[:len(options)]
            )
            if not valid:
                skipped_rows.append(row_num)
                continue
 
            if int(marks) > marks_remaining:
                over_budget_rows.append(row_num)
                continue
 
            next_order += 1
            question = Question.objects.create(
                exam=exam,
                question_text=question_text,
                marks=int(marks),
                question_order=next_order,
            )
            for idx, text in enumerate(options):
                QuestionOption.objects.create(
                    question=question,
                    option_key=OPTION_KEYS[idx],
                    option_text=text,
                    is_correct=(OPTION_KEYS[idx] == correct_letter),
                )
            created_count += 1
            marks_remaining -= int(marks)
 
        if created_count:
            summary = f'{created_count} question(s) imported from CSV.'
            if skipped_rows:
                summary += f' Skipped invalid row(s): {", ".join(str(r) for r in skipped_rows)}.'
            if over_budget_rows:
                summary += (
                    f' Row(s) exceeding the exam\'s remaining marks were skipped: '
                    f'{", ".join(str(r) for r in over_budget_rows)}.'
                )
            messages.success(request, summary)
        elif over_budget_rows:
            messages.error(
                request,
                'No rows imported -- every remaining row would exceed the marks left for this exam.'
            )
        else:
            messages.error(request, 'No valid rows found in that CSV. Check the example format below.')
 
        return redirect('my_exam_questions', exam_id=exam.id)
 
    return _redirect_add(exam, 'csv')
 
 
# ------------------------------------------------------------
# 3) ADD VIA PDF
# ------------------------------------------------------------
 
@login_required
def my_question_add_pdf(request, exam_id):
    exam = _get_owned_exam(request, exam_id)
 
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')
 
        if not pdf_file:
            messages.error(request, 'Choose a PDF file first.')
            return _redirect_add(exam, 'pdf')
 
        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, 'File must be a .pdf file.')
            return _redirect_add(exam, 'pdf')
 
        try:
            from pypdf import PdfReader
        except ImportError:
            messages.error(request, 'PDF import needs the "pypdf" package on the server. Run: pip install pypdf')
            return _redirect_add(exam, 'pdf')
 
        try:
            reader = PdfReader(pdf_file)
            full_text = '\n'.join((page.extract_text() or '') for page in reader.pages)
        except Exception:
            messages.error(request, 'Could not read that PDF. Make sure it has selectable text (not a scanned image).')
            return _redirect_add(exam, 'pdf')
 
        questions_data = parse_mcq_pdf_text(full_text)
 
        if not questions_data:
            messages.error(request, 'No questions could be found. Match the format shown in the example below.')
            return _redirect_add(exam, 'pdf')
 
        next_order = Question.objects.filter(exam=exam).count()
        marks_remaining = _marks_remaining(exam)
        created_count = 0
        skipped_over_budget = 0
 
        for q in questions_data:
            if marks_remaining <= 0:
                break
 
            if q['marks'] > marks_remaining:
                skipped_over_budget += 1
                continue
 
            next_order += 1
            question = Question.objects.create(
                exam=exam,
                question_text=q['text'],
                marks=q['marks'],
                question_order=next_order,
            )
            for idx, opt in enumerate(q['options']):
                QuestionOption.objects.create(
                    question=question,
                    option_key=OPTION_KEYS[idx],
                    option_text=opt['text'],
                    is_correct=opt['is_correct'],
                )
            created_count += 1
            marks_remaining -= q['marks']
 
        if created_count:
            summary = f'{created_count} question(s) imported from PDF.'
            if skipped_over_budget:
                summary += f' {skipped_over_budget} question(s) skipped -- over the marks remaining for this exam.'
            messages.success(request, summary)
        elif skipped_over_budget:
            messages.error(
                request,
                'No questions imported -- they would all exceed the marks remaining for this exam.'
            )
        else:
            messages.error(request, 'No questions could be found. Match the format shown in the example below.')
 
        return redirect('my_exam_questions', exam_id=exam.id)
 
    return _redirect_add(exam, 'pdf')
 
 
# ------------------------------------------------------------
# EDIT / DELETE a single question
# ------------------------------------------------------------
 
@login_required
def my_question_edit(request, exam_id, question_id):
    exam = _get_owned_exam(request, exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    options = list(question.options.all().order_by('option_key'))
 
    marks_remaining = _marks_remaining(exam, exclude_question_id=question.id)
 
    if request.method == 'POST':
        errors = {}
 
        question_text = request.POST.get('question_text', '').strip()
        marks = request.POST.get('marks', '').strip()
        option_ids = request.POST.getlist('option_id[]')
        option_texts = request.POST.getlist('option_text[]')
        correct_option_id = request.POST.get('correct_option', '')
 
        if not question_text:
            errors['question_text'] = 'Question text is required.'
 
        if not marks or not marks.isdigit():
            errors['marks'] = 'Marks must be a whole number.'
        elif int(marks) > marks_remaining:
            errors['marks'] = (
                f'Only {marks_remaining} mark{"s" if marks_remaining != 1 else ""} available '
                f'for this question given the exam\'s total marks.'
            )
 
        if not correct_option_id:
            errors['correct_option'] = 'Select which option is correct.'
 
        if errors:
            first_error = next(iter(errors.values()))
            messages.error(request, first_error)
            return redirect('my_question_edit', exam_id=exam.id, question_id=question.id)
 
        question.question_text = question_text
        question.marks = int(marks)
        question.save()
 
        for opt_id, opt_text in zip(option_ids, option_texts):
            opt_text = opt_text.strip()
            if not opt_text:
                continue
            QuestionOption.objects.filter(id=opt_id, question=question).update(
                option_text=opt_text,
                is_correct=(opt_id == correct_option_id),
            )
 
        messages.success(request, 'Question updated.')
        return redirect('my_exam_questions', exam_id=exam.id)
 
    return render(request, 'teacher/question_edit.html', {
        'exam': exam,
        'question': question,
        'options': options,
        'marks_remaining': marks_remaining,
    })
 
 
@login_required
def my_question_delete(request, exam_id, question_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
 
    exam = _get_owned_exam(request, exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    question.delete()
 
    return JsonResponse({'success': True})





# ============================================================================
# Add these to teacher/views.py.
#
# Replaces the plain "Download current CSV" link on class_edit.html with:
#   1. my_class_student_csv_open   -- serves the file inline (not a forced
#      download) so the browser opens it directly instead of "Save As".
#   2. my_class_student_csv_edit   -- an editable table view of the CSV.
#   3. my_class_student_csv_save   -- autosave endpoint the edit page POSTs
#      to; rewrites the file in place.
#
# Note on "open with the OS's default app": a webpage cannot force that --
# it's a browser sandbox restriction, not something any server code can get
# around. Content-Disposition: inline is the real equivalent -- it tells
# the browser "you decide how to show this" instead of forcing a download
# dialog. Some browsers will hand a CSV off to the OS handler from there,
# most will just display it as text/a new tab; there's no further lever to
# pull from the server side.
# ============================================================================




 
def _get_owned_class(request, class_id):
    """A class that belongs to THIS teacher -- 404s for anything else."""
    return get_object_or_404(Class, id=class_id, teacher=request.user)


 

def _read_class_csv(class_obj):
    """Returns (headers, rows) parsed from the class's student_info file.
    Empty lists if there's no file or it's empty."""
    if not class_obj.student_info:
        return [], []
 
    class_obj.student_info.open('rb')
    try:
        decoded = class_obj.student_info.read().decode('utf-8-sig')
    finally:
        class_obj.student_info.close()
 
    all_rows = list(csv.reader(io.StringIO(decoded)))
    if not all_rows:
        return [], []
    return all_rows[0], all_rows[1:]
 

# ==============================================================================
# TEACHER — OPEN the raw CSV directly (inline, not a forced download)
# ==============================================================================


@login_required
def my_class_student_csv_open(request, class_id):
    class_obj = _get_owned_class(request, class_id)
    if not class_obj.student_info:
        raise Http404('No student info file uploaded for this class.')
 
    class_obj.student_info.open('rb')
    try:
        content = class_obj.student_info.read()
    finally:
        class_obj.student_info.close()
 
    file_name = class_obj.student_info.name.rsplit('/', 1)[-1]
    # text/plain, not text/csv -- browsers have a native renderer for
    # plain text and will actually display it inline. text/csv has no
    # built-in renderer in any major browser, so even with
    # Content-Disposition: inline it gets downloaded instead (Chrome/Edge/
    # Firefox all fall back to "download it" for types they can't show).
    # The visible trade-off: it renders as raw comma-separated text, not
    # a formatted table -- for that, use "Edit Student List" instead.
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'inline; filename="{file_name}"'
    return response
 
# ==============================================================================
# TEACHER — EDITABLE TABLE VIEW of the CSV
# ==============================================================================


@login_required
def my_class_student_csv_edit(request, class_id):
    class_obj = _get_owned_class(request, class_id)
    headers, rows = _read_class_csv(class_obj)
 
    return render(request, 'teacher/class_student_csv_edit.html', {
        'class_obj': class_obj,
        'headers': headers,
        'rows': rows,
    })
# ==============================================================================
# TEACHER — AUTOSAVE the edited table back into the CSV file
# ==============================================================================

@login_required

def my_class_student_csv_save(request, class_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
 
    class_obj = _get_owned_class(request, class_id)
 
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid data.'}, status=400)
 
    headers = payload.get('headers') or []
    rows = payload.get('rows') or []
 
    if not headers or not any(h.strip() for h in headers):
        return JsonResponse({'error': 'CSV must have at least one column header.'}, status=400)
 
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        # Skip fully-blank rows (e.g. a row the user added then left empty).
        if not any(str(cell).strip() for cell in row):
            continue
        # Pad/truncate to the header length so a ragged edit never
        # corrupts the file's column count.
        row = (list(row) + [''] * len(headers))[:len(headers)]
        writer.writerow(row)
 
    csv_bytes = buffer.getvalue().encode('utf-8')
 
    if class_obj.student_info:
        # Overwrite the existing file *in place*, same name -- avoids
        # Django's default FileField.save() behavior of appending a random
        # suffix and leaving the old version orphaned on disk every autosave.
        storage = class_obj.student_info.storage
        name = class_obj.student_info.name
        with storage.open(name, 'wb') as f:
            f.write(csv_bytes)
    else:
        # No file existed yet (shouldn't normally happen -- the edit page
        # is only reachable when one does -- but handle it defensively).
        class_obj.student_info.save(
            f'class_{class_obj.id}_students.csv',
            ContentFile(csv_bytes),
            save=True,
        )
 
    return JsonResponse({'success': True})


