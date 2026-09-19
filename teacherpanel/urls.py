from django.urls import path
from . import views
from .views_q_option import set_exam_q_option

urlpatterns = [
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),



    path("exams/<int:exam_id>/q-option/", set_exam_q_option, name="exam-set-q-option"),

     # ---------- Teacher: own classes ----------
    path('classes/', views.my_classes, name='my_classes'),
    path('classes/add/', views.my_class_add, name='my_class_add'),
    path('classes/<int:class_id>/edit/', views.my_class_edit, name='my_class_edit'),
    path('classes/<int:class_id>/delete/', views.my_class_delete, name='my_class_delete'),



      # ---------- Teacher: student CSV open/edit (per class) ----------
    path('classes/<int:class_id>/students/open/', views.my_class_student_csv_open, name='my_class_student_csv_open'),
    path('classes/<int:class_id>/students/edit/', views.my_class_student_csv_edit, name='my_class_student_csv_edit'),
    path('classes/<int:class_id>/students/save/', views.my_class_student_csv_save, name='my_class_student_csv_save'),
    
        # ---------- Teacher: own exams ----------
    path('exams/', views.my_exams, name='my_exams'),
    path('exams/add/', views.my_exam_add, name='my_exam_add'),
    path('exams/<int:exam_id>/edit/', views.my_exam_edit, name='my_exam_edit'),
    path('exams/<int:exam_id>/delete/', views.my_exam_delete, name='my_exam_delete'),
 
    # ---------- Teacher: exam questions (MCQ) -- own exams only ----------
    path('exams/<int:exam_id>/questions/', views.my_exam_questions, name='my_exam_questions'),
    path('exams/<int:exam_id>/questions/add/', views.my_question_add, name='my_question_add'),
    path('exams/<int:exam_id>/questions/add/manual/', views.my_question_add_manual, name='my_question_add_manual'),
    path('exams/<int:exam_id>/questions/add/csv/', views.my_question_add_csv, name='my_question_add_csv'),
    path('exams/<int:exam_id>/questions/add/pdf/', views.my_question_add_pdf, name='my_question_add_pdf'),
    path('exams/<int:exam_id>/questions/<int:question_id>/edit/', views.my_question_edit, name='my_question_edit'),
    path('exams/<int:exam_id>/questions/<int:question_id>/delete/', views.my_question_delete, name='my_question_delete'),
]