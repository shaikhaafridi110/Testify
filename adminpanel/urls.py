from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='admin_dashboard'),
    path('user/', views.user, name='admin_user'),  

   
    path('users/<int:user_id>/edit/', views.user_edit, name='admin_user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='admin_user_delete'),



    # ---------- Admin: Exam (admin-owned, no class — class_obj=NULL) ----------
    path('exam/', views.admin_exams, name='admin_exams'),
    path('exam/add/', views.admin_exam_add, name='admin_exam_add'),
    path('exam/<int:exam_id>/edit/', views.admin_exam_edit, name='admin_exam_edit'),
    path('exam/<int:exam_id>/delete/', views.admin_exam_delete, name='admin_exam_delete'),    



    # ---------- Admin: manage all teachers' classes ----------
    path('teacher/classes/', views.teacher_classes, name='teacher_classes'),
    path('teacher/classes/<int:class_id>/edit/', views.teacher_class_edit, name='teacher_class_edit'),
    path('teacher/classes/<int:class_id>/delete/', views.teacher_class_delete, name='teacher_class_delete'),

     # ---------- Admin: exams for a specific class ----------
    path('teacher/classes/<int:class_id>/exam/', views.teacher_class_exams, name='teacher_class_exams'),
    path('teacher/classes/<int:class_id>/exam/<int:exam_id>/edit/', views.teacher_exam_edit, name='teacher_exam_edit'),
    path('teacher/classes/<int:class_id>/csv/', views.teacher_class_csv_download, name='teacher_class_csv_download'),
    path('teacher/classes/<int:class_id>/exam/<int:exam_id>/delete/', views.teacher_exam_delete, name='teacher_exam_delete'),


    # ---------- Exam questions (MCQ) — works for admin exams and teacher exams ----------
    path('exam/<int:exam_id>/questions/', views.exam_questions, name='exam_questions'),
    path('exam/<int:exam_id>/questions/add/', views.question_add, name='question_add'),
    path('exam/<int:exam_id>/questions/add/manual/', views.question_add_manual, name='question_add_manual'),
    path('exam/<int:exam_id>/questions/add/csv/', views.question_add_csv, name='question_add_csv'),
    path('exam/<int:exam_id>/questions/add/pdf/', views.question_add_pdf, name='question_add_pdf'),
    path('exam/<int:exam_id>/questions/<int:question_id>/edit/', views.question_edit, name='question_edit'),
    path('exam/<int:exam_id>/questions/<int:question_id>/delete/', views.question_delete, name='question_delete'),

    # ---------- Admin: Results ----------
     path('results/', views.admin_results, name='admin_results'),
    path('results/<int:attempt_id>/', views.admin_result_view, name='admin_result_view'),
    path('results/<int:attempt_id>/delete/', views.admin_result_delete, name='admin_result_delete'),


    path('contacts/', views.admin_contacts, name='admin_contacts'),
    path('contacts/<int:contact_id>/', views.admin_contact_view, name='admin_contact_view'),
    path('contacts/<int:contact_id>/status/', views.admin_contact_status, name='admin_contact_status'),
    path('contacts/<int:contact_id>/reply/', views.admin_contact_reply, name='admin_contact_reply'),
    path('contacts/<int:contact_id>/delete/', views.admin_contact_delete, name='admin_contact_delete'),

        # ---------- Admin: Notifications ----------
    path('notifications/', views.admin_notifications, name='admin_notifications'),
    path('notifications/add/', views.admin_notification_add, name='admin_notification_add'),
    path('notifications/<int:notification_id>/', views.admin_notification_view, name='admin_notification_view'),
    path('notifications/<int:notification_id>/delete/', views.admin_notification_delete, name='admin_notification_delete'),

    path('profile/', views.admin_profile, name='admin_profile'),
    path('profile/update/', views.admin_profile_update, name='admin_profile_update'),
    path('profile/change-password/', views.admin_change_password, name='admin_change_password'),  
]