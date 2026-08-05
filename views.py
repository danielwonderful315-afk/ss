from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.utils import timezone
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, BookUploadForm, StudyScheduleForm, ExamDateForm
from .models import Book, Bookmark, StudySchedule, ExamDate, Notification


# ─────────────────────────────────────────────
#  LANDING
# ─────────────────────────────────────────────

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


# ─────────────────────────────────────────────
#  AUTHENTICATION
# ─────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}! Your account has been created.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────

@login_required
def dashboard_view(request):
    # Only show THIS user's approved books
    recent_books = Book.objects.filter(
        uploader=request.user,
        status=Book.Status.APPROVED
    ).order_by('-upload_date')[:6]

    # Only this user's uploads (all statuses so they can see pending too)
    my_uploads = Book.objects.filter(
        uploader=request.user
    ).order_by('-upload_date')[:5]

    my_bookmarks = Bookmark.objects.filter(
        user=request.user
    ).select_related('book')[:5]

    unread_count = request.user.notifications.filter(is_read=False).count()
    quiz_count = Quiz.objects.filter(created_by=request.user).count()

    context = {
        'recent_books': recent_books,
        'my_uploads': my_uploads,
        'my_bookmarks': my_bookmarks,
        'unread_count': unread_count,
        'quiz_count': quiz_count,
    }
    return render(request, 'dashboard.html', context)


# ─────────────────────────────────────────────
#  PROFILE
# ─────────────────────────────────────────────

@login_required
def profile_view(request):
    form = ProfileUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user
    )
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    return render(request, 'auth/profile.html', {'form': form})


# ─────────────────────────────────────────────
#  BOOKS — PRIVATE PER USER
# ─────────────────────────────────────────────

@login_required
def book_list_view(request):
    """Show only the logged-in user's own approved books."""
    query = request.GET.get('q', '').strip()

    books = Book.objects.filter(
        uploader=request.user,
        status=Book.Status.APPROVED
    ).order_by('-upload_date')

    if query:
        books = books.filter(
            title__icontains=query
        ) | Book.objects.filter(
            uploader=request.user,
            status=Book.Status.APPROVED,
            course_code__icontains=query
        )

    return render(request, 'books/book_list.html', {'books': books, 'query': query})


@login_required
def book_upload_view(request):
    """Upload a new PDF book."""
    form = BookUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            book = form.save(commit=False)
            book.uploader = request.user
            book.status = Book.Status.PENDING
            book.save()
            messages.success(request, "Book uploaded successfully! It will be visible after admin approval.")
            return redirect('book_list')
        else:
            messages.error(request, "Please correct the errors below.")
    return render(request, 'books/book_upload.html', {'form': form})


@login_required
def book_detail_view(request, pk):
    """Book detail — only accessible by the uploader."""
    book = get_object_or_404(
        Book, pk=pk,
        uploader=request.user,
        status=Book.Status.APPROVED
    )
    bookmark, _ = Bookmark.objects.get_or_create(user=request.user, book=book)
    return render(request, 'books/book_detail.html', {
        'book': book,
        'bookmark': bookmark,
    })


@login_required
def book_read_view(request, pk):
    """PDF reader — only accessible by the uploader."""
    book = get_object_or_404(
        Book, pk=pk,
        uploader=request.user,
        status=Book.Status.APPROVED
    )
    bookmark, _ = Bookmark.objects.get_or_create(user=request.user, book=book)

    if request.method == 'POST':
        page = request.POST.get('page', 1)
        try:
            bookmark.page = int(page)
            bookmark.save()
        except (ValueError, TypeError):
            pass
        return redirect('book_read', pk=pk)

    return render(request, 'books/book_read.html', {
        'book': book,
        'bookmark': bookmark,
    })


@login_required
def my_books_view(request):
    """Shows the logged-in user's own uploaded books and their approval status."""
    my_books = Book.objects.filter(
        uploader=request.user
    ).order_by('-upload_date')
    return render(request, 'books/my_books.html', {'my_books': my_books})


# ─────────────────────────────────────────────
#  STUDY SCHEDULE
# ─────────────────────────────────────────────

@login_required
def schedule_view(request):
    today = timezone.now().date()
    schedules = StudySchedule.objects.filter(student=request.user).order_by('date', 'start_time')
    upcoming = schedules.filter(date__gte=today)
    past = schedules.filter(date__lt=today)
    form = StudyScheduleForm()
    return render(request, 'planner/schedule.html', {
        'upcoming': upcoming,
        'past': past,
        'form': form,
        'today': today,
    })


@login_required
def schedule_add(request):
    if request.method == 'POST':
        form = StudyScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.student = request.user
            schedule.save()
            messages.success(request, "Study session added successfully!")
        else:
            messages.error(request, "Please correct the errors below.")
    return redirect('schedule')


@login_required
def schedule_toggle(request, pk):
    schedule = get_object_or_404(StudySchedule, pk=pk, student=request.user)
    schedule.is_done = not schedule.is_done
    schedule.save()
    status = "completed" if schedule.is_done else "marked as pending"
    messages.success(request, f"Session {status}.")
    return redirect('schedule')


@login_required
def schedule_delete(request, pk):
    schedule = get_object_or_404(StudySchedule, pk=pk, student=request.user)
    schedule.delete()
    messages.success(request, "Study session deleted.")
    return redirect('schedule')


# ─────────────────────────────────────────────
#  EXAM DATES
# ─────────────────────────────────────────────

@login_required
def exam_list_view(request):
    today = timezone.now().date()
    upcoming_exams = ExamDate.objects.filter(
        student=request.user,
        exam_date__gte=today
    ).order_by('exam_date')
    past_exams = ExamDate.objects.filter(
        student=request.user,
        exam_date__lt=today
    ).order_by('-exam_date')
    form = ExamDateForm()
    return render(request, 'planner/exam_list.html', {
        'upcoming_exams': upcoming_exams,
        'past_exams': past_exams,
        'form': form,
        'today': today,
    })


@login_required
def exam_add(request):
    if request.method == 'POST':
        form = ExamDateForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.student = request.user
            exam.save()
            days = exam.days_until()
            Notification.objects.create(
                user=request.user,
                message=f"Exam registered: {exam.course_code} — {exam.course} on {exam.exam_date.strftime('%B %d, %Y')}.",
                notif_type=Notification.NotifType.EXAM_REMINDER,
            )
            messages.success(request, f"Exam date registered! {days} day(s) to go.")
        else:
            messages.error(request, "Please correct the errors below.")
    return redirect('exam_list')


@login_required
def exam_delete(request, pk):
    exam = get_object_or_404(ExamDate, pk=pk, student=request.user)
    exam.delete()
    messages.success(request, "Exam date removed.")
    return redirect('exam_list')


# ─────────────────────────────────────────────
#  NOTIFICATIONS
# ─────────────────────────────────────────────

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'planner/notifications.html', {
        'notifications': notifications,
    })


@login_required
def notification_delete(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.delete()
    return redirect('notifications')


@login_required
def notifications_clear(request):
    Notification.objects.filter(user=request.user).delete()
    messages.success(request, "All notifications cleared.")
    return redirect('notifications')

import json
import pdfplumber
import anthropic
from django.conf import settings
from django.views.decorators.http import require_POST
from .models import Quiz, Question, QuizAttempt, QuizAnswer

@login_required
def quiz_list_view(request):
    quizzes = Quiz.objects.filter(created_by=request.user).prefetch_related('questions').order_by('-created_at')
    for quiz in quizzes:
        attempts = QuizAttempt.objects.filter(student=request.user, quiz=quiz)
        quiz.attempt_count = attempts.count()
        quiz.best_score = max([a.percentage for a in attempts], default=None)
    return render(request, 'quizzes/quiz_list.html', {'quizzes': quizzes})

@login_required
def quiz_generate_view(request):
    books = Book.objects.filter(uploader=request.user, status='approved').order_by('-upload_date')
    return render(request, 'quizzes/quiz_generate.html', {'books': books})

@login_required
def quiz_delete_view(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
    quiz.delete()
    messages.success(request, "Quiz deleted.")
    return redirect('quiz_list')

@login_required
def quiz_history_view(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
    attempts = QuizAttempt.objects.filter(student=request.user, quiz=quiz).order_by('-taken_at')
    return render(request, 'quizzes/quiz_history.html', {'quiz': quiz, 'attempts': attempts})

@login_required
def quiz_result_view(request, pk):
    attempt = get_object_or_404(QuizAttempt, pk=pk, student=request.user)
    answers = attempt.answers.select_related('question').all()
    return render(request, 'quizzes/quiz_result.html', {'attempt': attempt, 'answers': answers})

@login_required
def quiz_take_view(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
    questions = quiz.questions.all()
    if not questions:
        messages.error(request, "This quiz has no questions yet.")
        return redirect('quiz_list')
    if request.method == 'POST':
        score = 0
        total = questions.count()
        attempt = QuizAttempt.objects.create(student=request.user, quiz=quiz, score=0, total=total)
        for question in questions:
            chosen = request.POST.get(f'question_{question.pk}', '')
            is_correct = chosen == question.correct_option
            if is_correct:
                score += 1
            QuizAnswer.objects.create(attempt=attempt, question=question, chosen=chosen, is_correct=is_correct)
        attempt.score = score
        attempt.save()
        messages.success(request, f"Quiz submitted! You scored {score}/{total} ({attempt.percentage}%)")
        return redirect('quiz_result', pk=attempt.pk)
    return render(request, 'quizzes/quiz_take.html', {'quiz': quiz, 'questions': questions})

@login_required
@require_POST
def quiz_generate_process(request):
    book_id = request.POST.get('book_id')
    num_questions = int(request.POST.get('num_questions', 10))
    num_questions = max(5, min(num_questions, 15))
    book = get_object_or_404(Book, pk=book_id, uploader=request.user, status='approved')
    try:
        pdf_path = book.file.path
        text = ""
        with pdfplumber.open(pdf_path) as doc:
            for page in doc.pages:
                text += page.extract_text() or ""
        text = text[:8000]
        if len(text.strip()) < 100:
            messages.error(request, "Could not extract enough text from this PDF.")
            return redirect('quiz_generate')
    except Exception as e:
        messages.error(request, f"Error reading PDF: {str(e)}")
        return redirect('quiz_generate')
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        prompt = f"""You are an academic quiz generator. Based on the following study material, generate exactly {num_questions} multiple-choice questions.

STUDY MATERIAL:
{text}

Respond with ONLY a valid JSON array. No markdown, no explanation, just the JSON.

Format:
[
  {{
    "question": "Question text here?",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_option": "A",
    "explanation": "Brief explanation of why A is correct"
  }}
]"""
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        questions_data = json.loads(response_text)
    except json.JSONDecodeError:
        messages.error(request, "AI returned unexpected format. Please try again.")
        return redirect('quiz_generate')
    except Exception as e:
        messages.error(request, f"AI generation failed: {str(e)}")
        return redirect('quiz_generate')
    try:
        quiz = Quiz.objects.create(
            title=f"{book.title} — AI Quiz",
            course_code=book.course_code,
            book=book,
            created_by=request.user,
            is_ai_generated=True
        )
        for q in questions_data:
            Question.objects.create(
                quiz=quiz,
                question_text=q.get('question', ''),
                option_a=q.get('option_a', ''),
                option_b=q.get('option_b', ''),
                option_c=q.get('option_c', ''),
                option_d=q.get('option_d', ''),
                correct_option=q.get('correct_option', 'A').upper(),
                explanation=q.get('explanation', '')
            )
        messages.success(request, f"AI generated {quiz.questions.count()} questions from '{book.title}'!")
        return redirect('quiz_take', pk=quiz.pk)
    except Exception as e:
        messages.error(request, f"Error saving quiz: {str(e)}")
        return redirect('quiz_generate')