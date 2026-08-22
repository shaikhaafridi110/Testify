from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse

from .models import User, TeacherInfo
import uuid
import os

def dashboard(request):
    return render(request, 'admin/dashboard.html')


def user(request):
    users_qs = User.objects.all().order_by('-created_at')

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
    }
    return render(request, 'admin/user.html', context)


def user_edit(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    # Existing teacher profile, if any -- used both to pre-fill the form on
    # GET and to know whether we're updating vs. creating on POST.
    teacher_info = TeacherInfo.objects.filter(user=user_obj).first()

    if request.method == 'POST':
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