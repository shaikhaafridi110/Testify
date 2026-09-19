"""
adminpanel/utils.py — single source of truth for the CSV-driven exam
result flow. studentpanel and teacherpanel both import from here so the
CSV format logic isn't duplicated in three places.

CHANGED THIS PASS: q_option is now stored as a comma list of question
labels, e.g. teacher sets 5 questions -> "q1,q2,q3,q4,q5" (not just "5").
Matches the CSV column you screenshotted.
"""
import os
import pandas as pd
from django.conf import settings
from django.utils import timezone

# If Class / Exam / ExamResultFile / Question / QuestionOption live in a
# different app than adminpanel, change this one line everywhere it's used.
from .models import Class, Exam, ExamResultFile, Question, QuestionOption

RESULT_COLUMNS = [
    "enrollment",
    "student_status",   # not_enrolled | enrolled
    "q_option",          # "" or "q1,q2,...,qN"
    "total",
    "correct",
    "wrong",
    "skip",
    "percentage",
    "submitted_time",
    "result_status",     # pass | fail | ""
]


# ---------------------------------------------------------------- roster --

def read_class_roster(class_obj):
    """Read enrollment,div_rollno,name from Class.student_info CSV."""
    class_obj.student_info.open("rb")
    try:
        df = pd.read_csv(class_obj.student_info)
    finally:
        class_obj.student_info.close()
    df.columns = [c.strip().lower() for c in df.columns]
    if "enrollment" not in df.columns:
        raise ValueError("student_info CSV must have an 'enrollment' column")
    return df


def derive_password(enrollment_no):
    """Student password = last 7 characters of their enrollment number."""
    return str(enrollment_no).strip()[-7:]


# ----------------------------------------------------------- q_option fmt --

def build_q_option(n_questions):
    """5 -> 'q1,q2,q3,q4,q5'. 0/None -> '' (meaning: use all exam questions)."""
    if not n_questions:
        return ""
    return ",".join(f"q{i}" for i in range(1, int(n_questions) + 1))


def parse_q_option_count(q_option_value):
    """'q1,q2,q3,q4,q5' -> 5. Blank/NaN -> None (use all exam questions)."""
    if q_option_value is None:
        return None
    s = str(q_option_value).strip()
    if s in ("", "nan", "None"):
        return None
    return len([p for p in s.split(",") if p.strip()])


# --------------------------------------------------------- result file IO --

def get_result_file(exam):
    result_file = ExamResultFile.objects.filter(exam=exam).order_by("-id").first()
    if result_file is None:
        raise ValueError(f"No ExamResultFile exists yet for exam {exam.id}")
    return result_file


def _full_path(result_file):
    return os.path.join(settings.MEDIA_ROOT, result_file.file_path)


def _backup_full_path(result_file):
    """Mirrors the backup/ convention already used by Class.student_info_backup."""
    return os.path.join(settings.MEDIA_ROOT, "backup", "results", result_file.file_name)


def load_result_df(result_file):
    """
    dtype="object" (NOT dtype=str) forces every column to stay untyped,
    even when a column (submitted_time, q_option, result_status, etc.) is
    entirely empty right after generation — avoiding pandas inferring an
    all-empty column as float64 and rejecting a later string assignment.
    dtype=str maps to pandas' newer StringDtype on some versions, which is
    stricter and rejects plain ints (e.g. assigning `total = 5`); "object"
    is the classic loose dtype and accepts any Python value.
    """
    return pd.read_csv(_full_path(result_file), dtype="object")


def save_result_df(result_file, df):
    """
    Writes the primary CSV AND keeps a backup copy in sync — every call
    site (enroll, submit, set_q_option, generate) goes through this, so
    backup_file_path is never stale.
    """
    full_path = _full_path(result_file)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    df.to_csv(full_path, index=False)

    backup_path = _backup_full_path(result_file)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    df.to_csv(backup_path, index=False)

    rel_backup_path = os.path.join("backup", "results", result_file.file_name)
    if result_file.backup_file_path != rel_backup_path:
        result_file.backup_file_path = rel_backup_path
        result_file.save(update_fields=["backup_file_path"])


def get_student_row(exam, enrollment_no):
    """Return this student's roster row as a pandas Series, or None."""
    result_file = get_result_file(exam)
    df = load_result_df(result_file)
    row = df[df["enrollment"].astype(str) == str(enrollment_no)]
    return None if row.empty else row.iloc[0]


# --------------------------------------------------- CSV generation (admin)

def generate_result_csv(exam):
    """
    Build a fresh result CSV for `exam` from its class roster and attach it
    to a new ExamResultFile row. Called from the post_save signal on Exam.
    Safe to call more than once — returns the existing file instead of
    duplicating it.
    """
    class_obj = exam.class_obj
    if class_obj is None:
        return None  # admin public exam with no class -> nothing to generate

    existing = ExamResultFile.objects.filter(exam=exam).order_by("-id").first()
    if existing is not None:
        return existing

    roster = read_class_roster(class_obj)

    result_df = pd.DataFrame({
        "enrollment": roster["enrollment"],
        "student_status": "not_enrolled",
        "q_option": "",
        "total": None,
        "correct": None,
        "wrong": None,
        "skip": None,
        "percentage": None,
        "submitted_time": None,
        "result_status": None,
    })[RESULT_COLUMNS]

    file_name = f"exam_{exam.id}_results.csv"

    result_file = ExamResultFile(
        exam=exam,
        teacher=exam.created_by,
        class_obj=class_obj,
        file_name=file_name,
        total_students=len(result_df),
        status="generated",
    )
    result_file.file_path = os.path.join("results", file_name)
    result_file.save()

    # FIX: save_result_df now also writes the backup copy and sets
    # backup_file_path, instead of leaving it NULL.
    save_result_df(result_file, result_df)

    return result_file


# --------------------------------------------------------- teacher actions

def set_q_option(exam, n_questions, enrollments=None):
    """
    Teacher sets how many MCQs count for scoring, stored as 'q1,...,qN'.
    - enrollments=None -> apply to every student on the roster.
    - enrollments=[...] -> apply only to those enrollment numbers.
    """
    result_file = get_result_file(exam)
    df = load_result_df(result_file)

    if enrollments:
        mask = df["enrollment"].astype(str).isin([str(e) for e in enrollments])
    else:
        mask = df["enrollment"].notna()

    df.loc[mask, "q_option"] = build_q_option(n_questions)
    save_result_df(result_file, df)
    return int(mask.sum())


# --------------------------------------------------------- student actions

def set_enrolled(exam, enrollment_no):
    """Flip not_enrolled -> enrolled. No-op if already enrolled/submitted."""
    result_file = get_result_file(exam)
    df = load_result_df(result_file)

    mask = df["enrollment"].astype(str) == str(enrollment_no)
    if not mask.any():
        raise ValueError("Enrollment not found in this exam's roster")

    if df.loc[mask, "student_status"].iloc[0] == "not_enrolled":
        df.loc[mask, "student_status"] = "enrolled"
        save_result_df(result_file, df)
    return True


def record_submission(exam, enrollment_no, total, correct, wrong, skip, percentage, passed):
    """Rewrite one student's row after they submit the MCQ exam."""
    result_file = get_result_file(exam)
    df = load_result_df(result_file)

    mask = df["enrollment"].astype(str) == str(enrollment_no)
    if not mask.any():
        raise ValueError("Enrollment not found in this exam's roster")

    df.loc[mask, "total"] = total
    df.loc[mask, "correct"] = correct
    df.loc[mask, "wrong"] = wrong
    df.loc[mask, "skip"] = skip
    df.loc[mask, "percentage"] = round(percentage, 2)
    df.loc[mask, "submitted_time"] = timezone.now().isoformat()
    df.loc[mask, "result_status"] = "pass" if passed else "fail"

    save_result_df(result_file, df)

    result_file.status = "processed"
    result_file.save(update_fields=["status"])
    return True