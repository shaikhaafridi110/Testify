from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404, HttpResponseRedirect
from decimal import Decimal, ROUND_HALF_UP

from .models import User, TeacherInfo, Class, Exam, Question, QuestionOption ,UserExamAttempt,UserExamAnswer
import uuid
import os
import csv
import io
import re
from django.views.decorators.http import require_POST




def dashboard(request):
    return render(request, 'admin/dashboard.html')

def user(request):
    # select_related('teacher_info') lets the template read
    # admin_user.teacher_info.approval_status without an extra query per row.
    # Admins aren't managed from this list -- only ordinary users and teachers.
    users_qs = User.objects.filter(role__in=['user', 'teacher']).select_related('teacher_info').order_by('-created_at')

    # ==============================
    # DASHBOARD COUNTS
    # ==============================

    total_users = User.objects.filter(role='user').count()

    total_teachers = User.objects.filter(role='teacher').count()

    active_user = User.objects.filter(
        role='user',
        status='active'
            ).count()

    active_teacher = User.objects.filter(
    role='teacher',
    status='active'
    ).count()
    inactive_user = User.objects.filter(
        role='user',
        status='inactive'
            ).count()

    inactive_teacher = User.objects.filter(
    role='teacher',
    status='inactive'
    ).count()

    # ---- search ----
    search = request.GET.get('q', '').strip()
    if search:
        users_qs = users_qs.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )

    # ---- filter by status ----
    status = request.GET.get('status', '').strip()
    if status:
        users_qs = users_qs.filter(status=status)

    # ---- filter by role ----
    role = request.GET.get('role', '').strip()
    if role:
        users_qs = users_qs.filter(role=role)

    # ---- pagination ----
    paginator = Paginator(users_qs, 10)  # 10 users per page
    page_number = request.GET.get('page', 1)
    users = paginator.get_page(page_number)

    context = {
        'users': users,
        'search': search,
        'status': status,
        'role': role,

        'total_users': total_users,
        'total_teachers': total_teachers,

        'active_users':active_user,
        'active_teachers':active_teacher,
        'inactive_teachers':inactive_teacher,
        'inactive_users':inactive_user,
        'active_count':active_user+active_teacher,
        'inactive_count':inactive_user+inactive_teacher
    }
    return render(request, 'admin/user.html', context)


def user_edit(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    # Existing teacher profile, if any -- used both to pre-fill the form on
    # GET and to know whether we're updating vs. creating on POST.
    teacher_info = TeacherInfo.objects.filter(user=user_obj).first()

    if request.method == 'POST':

        # ------------------------------------------------------------
        # Teacher approve / reject (sent from the Users list page).
        # This is a separate action from the normal field-by-field
        # save below, so it's handled first and returns immediately.
        # ------------------------------------------------------------
        if 'approval_action' in request.POST:
            action = request.POST.get('approval_action')

            if user_obj.role != 'teacher':
                error = 'Only teacher accounts can be approved or rejected.'
                if is_ajax:
                    return JsonResponse({'error': error}, status=400)
                messages.error(request, error)
                return redirect('admin_user')

            teacher_info, _ = TeacherInfo.objects.get_or_create(user=user_obj)

            if teacher_info.approval_status != 'pending':
                error = 'This teacher has already been reviewed.'
                if is_ajax:
                    return JsonResponse({'error': error}, status=400)
                messages.error(request, error)
                return redirect('admin_user')

            if action == 'approve':
                teacher_info.approval_status = 'approved'
                user_obj.status = 'active'
            elif action == 'reject':
                teacher_info.approval_status = 'rejected'
                user_obj.status = 'blocked'
            else:
                error = 'Invalid approval action.'
                if is_ajax:
                    return JsonResponse({'error': error}, status=400)
                messages.error(request, error)
                return redirect('admin_user')

            teacher_info.save()
            user_obj.save()

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'status': user_obj.status,
                    'status_display': user_obj.get_status_display(),
                    'approval_status': teacher_info.approval_status,
                })

            messages.success(request, f"Teacher {action}d successfully.")
            return redirect('admin_user')

        # ------------------------------------------------------------
        # Normal field-by-field edit (from the Edit User page).
        # ------------------------------------------------------------
        errors = {}

        # Only touch fields that were actually sent, so a partial update
        # (e.g. status-only from the users list) doesn't wipe other fields.
        new_name = user_obj.name
        new_email = user_obj.email
        new_phone = user_obj.phone
        new_role = user_obj.role
        new_status = user_obj.status
        new_profile_image = user_obj.profile_image

        if 'name' in request.POST:
            new_name = request.POST.get('name', '').strip()
            if not new_name:
                errors['name'] = 'Name is required.'

        if 'email' in request.POST:
            new_email = request.POST.get('email', '').strip()
            if not new_email:
                errors['email'] = 'Email is required.'
            elif User.objects.exclude(id=user_obj.id).filter(email__iexact=new_email).exists():
                errors['email'] = 'This email is already in use by another user.'

        if 'phone' in request.POST:
            new_phone = request.POST.get('phone', '').strip() or None
            if new_phone and User.objects.exclude(id=user_obj.id).filter(phone=new_phone).exists():
                errors['phone'] = 'This phone number is already in use by another user.'

        if 'role' in request.POST:
            new_role = request.POST.get('role', user_obj.role)
            if new_role not in dict(User.ROLE_CHOICES):
                errors['role'] = 'Invalid role.'

        if 'status' in request.POST:
            new_status = request.POST.get('status', '').strip()
            if new_status not in dict(User.STATUS_CHOICES):
                errors['status'] = 'Invalid status.'

        # ---- profile image (all users) ----
        if request.FILES.get('profile_image'):
            new_profile_image = request.FILES['profile_image']
            extension = os.path.splitext(new_profile_image.name)[1]
            new_profile_image.name = f"{uuid.uuid4()}{extension}"
            user_obj.profile_image = new_profile_image

        # ---- teacher info (only when the user is/becomes a teacher and the
        # teacher section of the form was actually submitted) ----
        teacher_fields = None
        if new_role == 'teacher' and 'college_name' in request.POST:
            teacher_fields = {
                'college_name': request.POST.get('college_name', '').strip(),
                'college_phone': request.POST.get('college_phone', '').strip(),
                'qualification': request.POST.get('qualification', '').strip(),
                'subject': request.POST.get('subject', '').strip(),
                'experience': request.POST.get('experience', '').strip() or None,
                'bio': request.POST.get('bio', '').strip() or None,
                'approval_status': request.POST.get('approval_status', 'pending').strip(),
            }

            if not teacher_fields['college_name']:
                errors['college_name'] = 'College name is required.'
            if not teacher_fields['college_phone']:
                errors['college_phone'] = 'College phone is required.'
            if not teacher_fields['qualification']:
                errors['qualification'] = 'Qualification is required.'
            if not teacher_fields['subject']:
                errors['subject'] = 'Subject is required.'
            if teacher_fields['approval_status'] not in dict(TeacherInfo.APPROVAL_STATUS_CHOICES):
                errors['approval_status'] = 'Invalid approval status.'

        if errors:
            first_error = next(iter(errors.values()))
            if is_ajax:
                return JsonResponse({'error': first_error, 'errors': errors}, status=400)
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('admin_user_edit', user_id=user_obj.id)

        user_obj.name = new_name
        user_obj.email = new_email
        user_obj.phone = new_phone
        user_obj.role = new_role
        user_obj.status = new_status
        user_obj.profile_image = new_profile_image
        user_obj.save()

        if teacher_fields is not None:
            teacher_info, _ = TeacherInfo.objects.get_or_create(user=user_obj)
            for field, value in teacher_fields.items():
                setattr(teacher_info, field, value)
            teacher_info.save()
        elif new_role != 'teacher' and teacher_info is not None:
            # Role was switched away from teacher -- leave the TeacherInfo
            # row in place (history/approval record) rather than deleting it.
            pass

        if is_ajax:
            return JsonResponse({
                'success': True,
                'status': user_obj.status,
                'status_display': user_obj.get_status_display(),
            })

        messages.success(request, 'User updated successfully.')
        return redirect('admin_user')

    return render(request, 'admin/user_edit.html', {
        'user_obj': user_obj,
        'teacher_info': teacher_info,
    })


def user_delete(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    user_obj = get_object_or_404(User, id=user_id)
    user_obj.delete()

    return JsonResponse({'success': True})

# ==============================
# ADMIN — ALL TEACHERS' CLASSES
# ==============================

def teacher_classes(request):
    classes_qs = Class.objects.select_related('teacher').annotate(
        exam_count=Count('exams')
    ).order_by('-created_at')

    # ==============================
    # DASHBOARD COUNTS
    # ==============================

    total_classes = Class.objects.count()
    active_classes = Class.objects.filter(status='active').count()
    inactive_classes = Class.objects.filter(status='inactive').count()
    completed_classes = Class.objects.filter(status='completed').count()

    # ---- search ----
    search = request.GET.get('q', '').strip()
    if search:
        classes_qs = classes_qs.filter(
            Q(class_name__icontains=search) |
            Q(course__icontains=search) |
            Q(subject__icontains=search) |
            Q(teacher__name__icontains=search)
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
    return render(request, 'admin/classes.html', context)


def teacher_class_edit(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
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
            return redirect('teacher_class_edit', class_id=class_obj.id)

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
        return redirect('teacher_classes')

    return render(request, 'admin/class_edit.html', {'class_obj': class_obj})


def teacher_class_delete(request, class_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    class_obj = get_object_or_404(Class, id=class_id)
    class_obj.delete()

    return JsonResponse({'success': True})


# ==============================
# ADMIN — DOWNLOAD CLASS CSV (forces attachment, not inline open)
# ==============================

def teacher_class_csv_download(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)

    if not class_obj.student_info:
        raise Http404("No CSV file uploaded for this class.")

    file_handle = class_obj.student_info.open('rb')
    filename = class_obj.student_info.name.split('/')[-1]

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=filename,
        content_type='text/csv',
    )
    return response


# ==============================
# ADMIN — EXAMS (nested under a class, any teacher)
# ==============================

def teacher_class_exams(request, class_id):
    class_obj = get_object_or_404(Class.objects.select_related('teacher'), id=class_id)
    exams_qs = Exam.objects.filter(class_obj=class_obj).select_related('created_by').order_by('-created_at')

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
            Q(subject__icontains=search)
        )

    # ---- filter by status ----
    status = request.GET.get('status', '').strip()
    if status:
        exams_qs = exams_qs.filter(status=status)

    # ---- pagination ----
    paginator = Paginator(exams_qs, 10)
    page_number = request.GET.get('page', 1)
    exams = paginator.get_page(page_number)

    context = {
        'class_obj': class_obj,
        'exams': exams,
        'search': search,
        'status': status,

        'total_exams': total_exams,
        'draft_exams': draft_exams,
        'published_exams': published_exams,
        'closed_exams': closed_exams,
    }
    return render(request, 'admin/class_exams.html', context)


def teacher_exam_edit(request, class_id, exam_id):
    class_obj = get_object_or_404(Class, id=class_id)
    exam = get_object_or_404(Exam, id=exam_id, class_obj=class_obj)
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
            new_duration = request.POST.get('duration_minutes', '').strip()

        if 'total_marks' in request.POST:
            new_total_marks = request.POST.get('total_marks', '').strip()

        if 'passing_marks' in request.POST:
            new_passing_marks = request.POST.get('passing_marks', '').strip()

        if 'start_datetime' in request.POST:
            new_start = request.POST.get('start_datetime') or None

        if 'end_datetime' in request.POST:
            new_end = request.POST.get('end_datetime') or None

        if 'status' in request.POST:
            new_status = request.POST.get('status', '').strip()
            if new_status not in dict(Exam.STATUS_CHOICES):
                errors['status'] = 'Invalid status.'

        if errors:
            first_error = next(iter(errors.values()))
            if is_ajax:
                return JsonResponse({'error': first_error, 'errors': errors}, status=400)
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('teacher_exam_edit', class_id=class_obj.id, exam_id=exam.id)

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
        return redirect('teacher_class_exams', class_id=class_obj.id)

    return render(request, 'admin/exam_edit.html', {'exam': exam, 'class_obj': class_obj})


def teacher_exam_delete(request, class_id, exam_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    class_obj = get_object_or_404(Class, id=class_id)
    exam = get_object_or_404(Exam, id=exam_id, class_obj=class_obj)
    exam.delete()

    return JsonResponse({'success': True})



# ==============================
# ADMIN — PUBLIC EXAMS (admin-owned, class_obj is NULL)
#
# These are exams the admin creates directly, not tied to any
# teacher's class. The model already supports this: Exam.class_obj
# is nullable, and start/end datetime are nullable ("NULL FOR ADMIN
# PUBLIC EXAMS" per the model comment).
# ==============================
 
def admin_exams(request):
    # Scopes the list to exams created by this admin only.
    admin_id = request.user.id
 
    exams_qs = Exam.objects.filter(
        class_obj__isnull=True,
        created_by_id=admin_id,
    ).select_related('created_by').order_by('-created_at')
 
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
            Q(subject__icontains=search)
        )
 
    # ---- filter by status ----
    status = request.GET.get('status', '').strip()
    if status:
        exams_qs = exams_qs.filter(status=status)
 
    # ---- pagination ----
    paginator = Paginator(exams_qs, 10)
    page_number = request.GET.get('page', 1)
    exams = paginator.get_page(page_number)
 
    context = {
        'exams': exams,
        'search': search,
        'status': status,
 
        'total_exams': total_exams,
        'draft_exams': draft_exams,
        'published_exams': published_exams,
        'closed_exams': closed_exams,
    }
    return render(request, 'admin/exam.html', context)
 
 
def admin_exam_add(request):
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
 
    if request.method == 'POST':
        errors = {}
 
        title = request.POST.get('title', '').strip()
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip() or None
        duration_minutes = request.POST.get('duration_minutes', '').strip()
        total_marks = request.POST.get('total_marks', '').strip()
        passing_marks = request.POST.get('passing_marks', '').strip()
        start_datetime = request.POST.get('start_datetime') or None
        end_datetime = request.POST.get('end_datetime') or None
        status = request.POST.get('status', 'draft').strip()
 
        if not title:
            errors['title'] = 'Title is required.'
        if not subject:
            errors['subject'] = 'Subject is required.'
        if not duration_minutes:
            errors['duration_minutes'] = 'Duration is required.'
        if not total_marks:
            errors['total_marks'] = 'Total marks is required.'
        if not passing_marks:
            errors['passing_marks'] = 'Passing marks is required.'
        if status not in dict(Exam.STATUS_CHOICES):
            errors['status'] = 'Invalid status.'
 
        # Same admin can't create two admin-owned exams with the same
        # title + subject combo (case-insensitive). Different admins,
        # or exams under a teacher's class, aren't affected.
        if title and subject and not errors.get('title') and not errors.get('subject'):
            duplicate_exists = Exam.objects.filter(
                created_by_id=request.user.id,
                class_obj__isnull=True,
                title__iexact=title,
                subject__iexact=subject,
            ).exists()
            if duplicate_exists:
                errors['subject'] = 'You already have an exam with this title and subject.'
 
        if errors:
            first_error = next(iter(errors.values()))
            if is_ajax:
                return JsonResponse({'error': first_error, 'errors': errors}, status=400)
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('admin_exam_add')
 
        exam = Exam.objects.create(
            created_by_id=request.user.id,
            class_obj=None,
            title=title,
            subject=subject,
            description=description,
            duration_minutes=duration_minutes,
            total_marks=total_marks,
            passing_marks=passing_marks,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status=status,
        )
 
        if is_ajax:
            return JsonResponse({
                'success': True,
                'exam_id': exam.id,
                'redirect_url': reverse('question_add_manual', args=[exam.id]),
            })
 
        messages.success(request, 'Exam created. Now add its questions.')
        # Straight into the MCQ builder for the exam that was just created,
        # instead of back to the exam list -- an exam with no questions
        # yet isn't really usable.
        return redirect('question_add', exam_id=exam.id)
 
    return render(request, 'admin/exam_add.html')
 
 
def admin_exam_edit(request, exam_id):
    # Editing doesn't need request.user.id because ownership already lives
    # on the row (exam.created_by, set when it was created); the uniqueness
    # check below scopes off that, not off "who's currently logged in".
    exam = get_object_or_404(Exam, id=exam_id, class_obj__isnull=True)
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
            new_duration = request.POST.get('duration_minutes', '').strip()
 
        if 'total_marks' in request.POST:
            new_total_marks = request.POST.get('total_marks', '').strip()
 
        if 'passing_marks' in request.POST:
            new_passing_marks = request.POST.get('passing_marks', '').strip()
 
        if 'start_datetime' in request.POST:
            new_start = request.POST.get('start_datetime') or None
 
        if 'end_datetime' in request.POST:
            new_end = request.POST.get('end_datetime') or None
 
        if 'status' in request.POST:
            new_status = request.POST.get('status', '').strip()
            if new_status not in dict(Exam.STATUS_CHOICES):
                errors['status'] = 'Invalid status.'
 
        # Same admin can't have two admin-owned exams with the same
        # title + subject combo (case-insensitive). Scoped to the exam's
        # original creator, excluding this exam itself.
        if ('title' in request.POST or 'subject' in request.POST) and not errors.get('title') and not errors.get('subject'):
            duplicate_exists = Exam.objects.filter(
                created_by=exam.created_by,
                class_obj__isnull=True,
                title__iexact=new_title,
                subject__iexact=new_subject,
            ).exclude(id=exam.id).exists()
            if duplicate_exists:
                errors['subject'] = 'This admin already has an exam with this title and subject.'
 
        if errors:
            first_error = next(iter(errors.values()))
            if is_ajax:
                return JsonResponse({'error': first_error, 'errors': errors}, status=400)
            for field_error in errors.values():
                messages.error(request, field_error)
            return redirect('admin_exam_edit', exam_id=exam.id)
 
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
        return redirect('admin_exams')
 
    return render(request, 'admin/exam_edit_admin.html', {'exam': exam})
 
 
def admin_exam_delete(request, exam_id):
    # NOTE: no admin login/session yet -- see admin_exam_add's TODO. Deleting
    # doesn't need "who's browsing" either; it just needs the exam to exist
    # and be admin-owned (class_obj is NULL).
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
 
    exam = get_object_or_404(Exam, id=exam_id, class_obj__isnull=True)
    exam.delete()
 
    return JsonResponse({'success': True})
 

# =======================================================================================================
# ADMIN — EXAM QUESTIONS (MCQ) — add / edit / delete
#
# Works for both admin-owned exams (class_obj=NULL) and teacher exams
# (class_obj set) -- the exam_id is enough to find the exam either way,
# so these views aren't duplicated per exam type.
# =======================================================================================================

OPTION_KEYS = ['A', 'B', 'C', 'D', 'E', 'F']


def _redirect_add(exam, tab):
    """Back to the combined Add Questions page, on a specific tab."""
    return HttpResponseRedirect(reverse('question_add', args=[exam.id]) + f'?tab={tab}')


def exam_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    questions_qs = Question.objects.filter(exam=exam).prefetch_related('options').order_by('question_order', 'id')

    total_questions = questions_qs.count()
    total_marks_added = sum(q.marks for q in questions_qs)

    context = {
        'exam': exam,
        'class_obj': exam.class_obj,
        'questions': questions_qs,
        'total_questions': total_questions,
        'total_marks_added': total_marks_added,
    }
    return render(request, 'admin/exam_questions.html', context)


# ------------------------------------------------------------
# Combined "Add Questions" page -- one page, three tabs
# (Manual / CSV / PDF). Each tab's form posts to its own
# handler below; this view only renders the shell.
# ------------------------------------------------------------

def question_add(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    return render(request, 'admin/question_add.html', {'exam': exam})


# ------------------------------------------------------------
# 1) ADD MANUALLY -- one question + its options via a plain form
# ------------------------------------------------------------

def question_add_manual(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == 'POST':
        errors = {}

        question_text = request.POST.get('question_text', '').strip()
        marks = request.POST.get('marks', '').strip()
        option_texts = [o.strip() for o in request.POST.getlist('option_text[]')]
        correct_index = request.POST.get('correct_option', '')

        # Drop blank option rows (the form always renders 4, user may not
        # fill all of them), but keep track of original positions so the
        # "correct_option" radio index still lines up.
        filled_options = [(i, text) for i, text in enumerate(option_texts) if text]

        if not question_text:
            errors['question_text'] = 'Question text is required.'
        if not marks or not marks.isdigit():
            errors['marks'] = 'Marks must be a whole number.'
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
            return _redirect_add(exam, 'manual')
        return redirect('exam_questions', exam_id=exam.id)

    return _redirect_add(exam, 'manual')


# ------------------------------------------------------------
# 2) ADD VIA CSV -- bulk import, one question per row
# ------------------------------------------------------------

def question_add_csv(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

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
        created_count = 0
        skipped_rows = []

        for row_num, raw_row in enumerate(reader, start=2):  # row 1 is the header
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

        if created_count:
            summary = f'{created_count} question(s) imported from CSV.'
            if skipped_rows:
                summary += f' Skipped row(s): {", ".join(str(r) for r in skipped_rows)}.'
            messages.success(request, summary)
        else:
            messages.error(request, 'No valid rows found in that CSV. Check the example format below.')

        return redirect('exam_questions', exam_id=exam.id)

    return _redirect_add(exam, 'csv')


# ------------------------------------------------------------
# 3) ADD VIA PDF -- bulk import, parsed from plain text in the PDF
# ------------------------------------------------------------

def parse_mcq_pdf_text(text):
    """
    Parses questions out of PDF text laid out like:

        Q1. What is the capital of France? [2]
        A) London
        B) Paris *
        C) Berlin
        D) Madrid

    - A new question starts on any line beginning with a number, e.g.
      "Q1." or "1)". Blank lines between questions are NOT required --
      real PDF text extraction (pypdf) often collapses vertical
      whitespace, so relying on blank-line separation would silently
      drop every question. Splitting on the question marker itself is
      robust either way.
    - "[2]" after the question text sets the marks (defaults to 1 if omitted).
    - A trailing "*" on an option line marks it as the correct answer.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    blocks = []
    current = []
    for line in lines:
        if re.match(r'^Q?\s*\d+[\.\)]\s*\S', line, re.IGNORECASE):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)

    questions = []
    for block_lines in blocks:
        q_match = re.match(r'^Q?\s*\d+[\.\)]\s*(.+)$', block_lines[0], re.IGNORECASE)
        if not q_match:
            continue

        question_line = q_match.group(1).strip()
        marks_match = re.search(r'\[(\d+)\]\s*$', question_line)
        marks = int(marks_match.group(1)) if marks_match else 1
        question_text = re.sub(r'\[\d+\]\s*$', '', question_line).strip()

        options = []
        for line in block_lines[1:]:
            opt_match = re.match(r'^[A-Fa-f][\.\)]\s*(.+)$', line)
            if not opt_match:
                continue
            opt_text = opt_match.group(1).strip()
            is_correct = opt_text.endswith('*')
            if is_correct:
                opt_text = opt_text.rstrip('*').strip()
            if opt_text:
                options.append({'text': opt_text, 'is_correct': is_correct})

        if question_text and len(options) >= 2 and any(o['is_correct'] for o in options):
            questions.append({'text': question_text, 'marks': marks, 'options': options})

    return questions


def question_add_pdf(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

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
        created_count = 0

        for q in questions_data:
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

        messages.success(request, f'{created_count} question(s) imported from PDF.')
        return redirect('exam_questions', exam_id=exam.id)

    return _redirect_add(exam, 'pdf')


# ------------------------------------------------------------
# EDIT / DELETE a single question
# ------------------------------------------------------------

def question_edit(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    options = list(question.options.all().order_by('option_key'))

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
        if not correct_option_id:
            errors['correct_option'] = 'Select which option is correct.'

        if errors:
            first_error = next(iter(errors.values()))
            messages.error(request, first_error)
            return redirect('question_edit', exam_id=exam.id, question_id=question.id)

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
        return redirect('exam_questions', exam_id=exam.id)

    return render(request, 'admin/question_edit.html', {
        'exam': exam,
        'question': question,
        'options': options,
    })


def question_delete(request, exam_id, question_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    exam = get_object_or_404(Exam, id=exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    question.delete()

    return JsonResponse({'success': True})






#====================================================
#resul
#====================================================
#====================================================
#resul
#====================================================
def admin_results(request):
    attempts_qs = UserExamAttempt.objects.select_related('user', 'exam').order_by('-created_at')

    # ==============================
    # DASHBOARD COUNTS
    # ==============================

    total_attempts = UserExamAttempt.objects.count()
    submitted_attempts = UserExamAttempt.objects.filter(status='submitted').count()
    passed_attempts = UserExamAttempt.objects.filter(result_status='pass').count()
    failed_attempts = UserExamAttempt.objects.filter(result_status='fail').count()

    # ---- search (student name/email or exam title) ----
    search = request.GET.get('q', '').strip()
    if search:
        attempts_qs = attempts_qs.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(exam__title__icontains=search)
        )

    # ---- filter by attempt status ----
    status = request.GET.get('status', '').strip()
    if status:
        attempts_qs = attempts_qs.filter(status=status)

    # ---- filter by pass/fail ----
    result_status = request.GET.get('result', '').strip()
    if result_status:
        attempts_qs = attempts_qs.filter(result_status=result_status)

    # ---- filter by exam subject ----
    subject = request.GET.get('subject', '').strip()
    if subject:
        attempts_qs = attempts_qs.filter(exam__subject=subject)

    # distinct subjects for the filter dropdown (from exams that actually have attempts)
    subjects = (
        Exam.objects.filter(user_attempts__isnull=False)
        .values_list('subject', flat=True)
        .distinct()
        .order_by('subject')
    )

    # ---- sort by score ----
    sort = request.GET.get('sort', '').strip()
    if sort == 'score_desc':
        attempts_qs = attempts_qs.order_by('-score', '-created_at')
    elif sort == 'score_asc':
        attempts_qs = attempts_qs.order_by('score', '-created_at')
    # else: keep default -created_at ordering already applied above

    # ---- pagination ----
    paginator = Paginator(attempts_qs, 10)
    page_number = request.GET.get('page', 1)
    attempts = paginator.get_page(page_number)

    context = {
        'attempts': attempts,
        'search': search,
        'status': status,
        'result_status': result_status,
        'subject': subject,
        'subjects': subjects,
        'sort': sort,

        'total_attempts': total_attempts,
        'submitted_attempts': submitted_attempts,
        'passed_attempts': passed_attempts,
        'failed_attempts': failed_attempts,
    }
    return render(request, 'admin/results.html', context)

def admin_result_view(request, attempt_id):
    """Read-only breakdown of one attempt: every question, the student's
    selected option, and the correct option. Returns JSON so the results
    page can render it in a modal without a full page reload."""
    attempt = get_object_or_404(
        UserExamAttempt.objects.select_related('user', 'exam'),
        id=attempt_id
    )

    answers = (
        UserExamAnswer.objects
        .filter(attempt=attempt)
        .select_related('selected_option', 'question')
        .prefetch_related('question__options')
        .order_by('question__question_order')
    )

    answer_rows = []
    for ans in answers:
        correct_option = None
        for opt in ans.question.options.all():
            if opt.is_correct:
                correct_option = opt.option_key
                break

        answer_rows.append({
            'question_text': ans.question.question_text,
            'question_order': ans.question.question_order,
            'marks': ans.question.marks,
            'selected_option': ans.selected_option.option_key if ans.selected_option else None,
            'correct_option': correct_option,
            'is_correct': ans.is_correct,
        })

    payload = {
        'id': attempt.id,
        'user_name': attempt.user.name,
        'user_email': attempt.user.email,
        'exam_title': attempt.exam.title,
        'exam_total_marks': attempt.exam.total_marks,
        'score': attempt.score,
        'percentage': str(attempt.percentage),
        'correct_answers': attempt.correct_answers,
        'wrong_answers': attempt.wrong_answers,
        'skipped_answers': attempt.skipped_answers,
        'status': attempt.status,
        'result_status': attempt.result_status,
        'started_at': attempt.started_at.isoformat() if attempt.started_at else None,
        'submitted_at': attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        'answers': answer_rows,
    }

    return JsonResponse({'success': True, 'attempt': payload})


def admin_result_delete(request, attempt_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    attempt = get_object_or_404(UserExamAttempt, id=attempt_id)
    attempt.delete()

    return JsonResponse({'success': True})