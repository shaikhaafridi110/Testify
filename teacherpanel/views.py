from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from adminpanel.models import Class, Exam, Question


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



