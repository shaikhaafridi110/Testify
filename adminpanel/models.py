from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):

    # ==============================
    # CHOICES
    # ==============================

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('user', 'User'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
    ]

    OTP_PURPOSE_CHOICES = [
        ('email_verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
        ('login_verification', 'Login Verification'),
    ]

    # ==============================
    # REMOVE DEFAULT USER FIELDS
    # ==============================

    username = None
    first_name = None
    last_name = None

    # ==============================
    # BASIC INFORMATION
    # ==============================

    name = models.CharField(
        max_length=50
    )

    email = models.EmailField(
        max_length=50,
        unique=True
    )

    phone = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        unique=True
    )

    profile_image = models.ImageField(
        upload_to='profiles/',
        null=True,
        blank=True
    )

    # ==============================
    # USER ROLE
    # ==============================

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user'
    )

    # ==============================
    # OTP INFORMATION
    # ==============================

    otp = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    otp_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    otp_verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    otp_purpose = models.CharField(
        max_length=30,
        choices=OTP_PURPOSE_CHOICES,
        null=True,
        blank=True
    )

    otp_attempts = models.IntegerField(
        default=0
    )

    # ==============================
    # PASSWORD INFORMATION
    # ==============================

    password_changed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # ==============================
    # ACCOUNT STATUS
    # ==============================

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )

    # ==============================
    # TIMESTAMPS
    # ==============================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # ==============================
    # LOGIN SETTINGS
    # ==============================

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = ['name']

    # ==============================
    # DATABASE TABLE
    # ==============================

    class Meta:
        db_table = 'users'

    # ==============================
    # STRING REPRESENTATION
    # ==============================

    def __str__(self):
        return self.email




    # =======================================================================================================
    # Teacher
    # ==============================




class TeacherInfo(models.Model):

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_info'
    )

   

    college_name = models.CharField(
        max_length=150
    )

    college_phone = models.CharField(
        max_length=20
    )

    qualification = models.CharField(
        max_length=150
    )

    subject = models.CharField(
        max_length=100
    )

    experience = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    bio = models.TextField(
        null=True,
        blank=True
    )

    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'teacher_info'

    def __str__(self):
        return f"{self.user.name} - {self.approval_status}"




# =======================================================================================================
# Class
# =======================================================================================================

class Class(models.Model):

    # ==============================
    # CHOICES
    # ==============================

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
    ]

    # ==============================
    # TEACHER RELATIONSHIP
    # ==============================

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='classes'
    )

    # ==============================
    # BASIC CLASS INFORMATION
    # ==============================

    class_name = models.CharField(
        max_length=100
    )

    subject = models.CharField(
        max_length=100
    )

    course = models.CharField(
        max_length=100
    )

    semester = models.CharField(
        max_length=50
    )

    description = models.TextField(
        null=True,
        blank=True
    )

    academic_year = models.CharField(
        max_length=20
    )

    # ==============================
    # STUDENT INFORMATION FILE
    # ==============================

    student_info = models.FileField(
        upload_to='student_info/'
    )

    # ==============================
    # STUDENT INFORMATION BACKUP FILE
    # ==============================

    student_info_backup = models.FileField(
        upload_to='backup/student_info/',
        null=True,
        blank=True
    )

    # ==============================
    # CLASS STATUS
    # ==============================

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )

    # ==============================
    # TIMESTAMPS
    # ==============================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # ==============================
    # DATABASE TABLE
    # ==============================

    class Meta:
        db_table = 'classes'

    # ==============================
    # STRING REPRESENTATION
    # ==============================

    def __str__(self):
        return self.class_name




# =======================================================================================================
# Exam
# =======================================================================================================

class Exam(models.Model):

    # ==============================
    # CHOICES
    # ==============================

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
    ]

    # ==============================
    # EXAM CREATOR
    # ==============================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_exams'
    )

    # ==============================
    # CLASS
    # ==============================

    class_obj = models.ForeignKey(
        'Class',
        on_delete=models.CASCADE,
        related_name='exams',
        null=True,
        blank=True
    )

    # ==============================
    # BASIC EXAM INFORMATION
    # ==============================

    title = models.CharField(
        max_length=150
    )

    subject = models.CharField(
        max_length=100
    )

    description = models.TextField(
        null=True,
        blank=True
    )

    # ==============================
    # EXAM SETTINGS
    # ==============================

    duration_minutes = models.IntegerField()

    total_marks = models.IntegerField()

    passing_marks = models.IntegerField()

    # ==============================
    # TEACHER EXAM SCHEDULE
    # NULL FOR ADMIN PUBLIC EXAMS
    # ==============================

    start_datetime = models.DateTimeField(
        null=True,
        blank=True
    )

    end_datetime = models.DateTimeField(
        null=True,
        blank=True
    )

    # ==============================
    # EXAM STATUS
    # ==============================

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # ==============================
    # TIMESTAMPS
    # ==============================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # ==============================
    # DATABASE TABLE
    # ==============================

    class Meta:
        db_table = 'exams'

    # ==============================
    # STRING REPRESENTATION
    # ==============================

    def __str__(self):
        return self.title


#======================================================================================
#for quetiion
#======================================================================================
class Question(models.Model):

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    question_text = models.TextField()

    marks = models.IntegerField()

    question_order = models.IntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'questions'

    def __str__(self):
        return self.question_text



class QuestionOption(models.Model):

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options'
    )

    option_key = models.CharField(
        max_length=1
    )

    option_text = models.TextField()

    is_correct = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'question_options'

    def __str__(self):
        return f"{self.question.question_text} - {self.option_key}"




#======================================================================================
#user_enroll
#======================================================================================
class UserExamAttempt(models.Model):

    STATUS_CHOICES = [
        ('started', 'Started'),
        ('submitted', 'Submitted'),
        ('expired', 'Expired'),
    ]

    RESULT_STATUS_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ]

    exam = models.ForeignKey(
        'Exam',
        on_delete=models.CASCADE,
        related_name='user_attempts'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_attempts'
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='started'
    )

    score = models.IntegerField(
       null=True, blank=True
    )

    correct_answers = models.IntegerField(
       null=True, blank=True
    )

    wrong_answers = models.IntegerField(
      null=True, blank=True
    )

    skipped_answers = models.IntegerField(
       null=True, blank=True
    )

    percentage = models.DecimalField(
        max_digits=5,
    decimal_places=2,
    null=True,
    blank=True
    )

    result_status = models.CharField(
            max_length=10,
    choices=RESULT_STATUS_CHOICES,
    null=True,
    blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'user_exam_attempts'

    def __str__(self):
        return f"{self.user.name} - {self.exam.title}"


class UserExamAnswer(models.Model):

    attempt = models.ForeignKey(
        UserExamAttempt,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        related_name='user_answers'
    )

    selected_option = models.ForeignKey(
        'QuestionOption',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_by_users'
    )

    is_correct = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'user_exam_answers'

        constraints = [
            models.UniqueConstraint(
                fields=['attempt', 'question'],
                name='unique_user_answer_per_question'
            )
        ]

    def __str__(self):
        return f"{self.attempt.user.name} - {self.question.question_text}"