from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    path("otp/verify/", views.otp_verify, name="otp_verify"),


    path("teacher-register/", views.teacher_register, name="teacher_register"),
    path("check-email/", views.check_email, name="check_email"),

    path("otp/resend/", views.otp_resend, name="otp_resend"),


    path("profile/", views.profile, name="profile"),

    path("index/", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("features/", views.features, name="features"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),

    path("exams/", views.exams, name="exams"),

    path("exam/<int:exam_id>/enroll/", views.enroll_exam, name="enroll_exam"),
    path("exam/attempt/<int:attempt_id>/", views.exam_attempt, name="exam_attempt"),
    path("exam/attempt/<int:attempt_id>/result/", views.exam_result, name="exam_result"),
    path('exams/completed/', views.completed_exams, name='completed_exams'),

    path('leaderboard/', views.leaderboard, name='leaderboard'),

    path("contact/", views.contact, name="contact"),
    path("logout/", views.logout_view, name="logout"),


    path("notifications/", views.notifications, name="notifications"),
    path("notifications/mark-all-read/", views.notification_mark_all_read, name="notification_mark_all_read"),
    path("notifications/unread-count/", views.notification_unread_count, name="notification_unread_count"),
]