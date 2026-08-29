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
]