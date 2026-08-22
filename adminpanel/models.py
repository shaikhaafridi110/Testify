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
