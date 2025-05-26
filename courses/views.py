# ai_elearning_platform/courses/views.py
from django.shortcuts import render, get_object_or_404, redirect # redirect is needed
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse # JsonResponse for AJAX later
from django.views.decorators.http import require_POST # To ensure this view only accepts POST
from django.contrib import messages
from .models import *
from core.ai_utils import get_saq_feedback
from django.db import transaction
from users.models import *
import re
# View to list all available courses
def course_list_view(request):
    courses = Course.objects.all().order_by('-created_at') # Get all courses, newest first
    context = {
        'courses': courses
    }
    return render(request, 'courses/course_list.html', context)

def course_detail_view(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    modules = course.modules.all().prefetch_related('lessons', 'lessons__user_progress')

    is_enrolled = False # Default to False
    completed_lessons_for_course_count = 0 # Initialize
    total_lessons_in_course = 0 # Initialize
    course_progress_percent = 0 # Initialize
    modules_with_progress = [] # Initialize

    if request.user.is_authenticated:
        # Determine if the user is "enrolled" (i.e., has started any lesson in this course)
        # This is our proxy for enrollment until a dedicated Enrollment model is made.
        is_enrolled = UserLessonProgress.objects.filter(
            user=request.user,
            lesson__module__course=course
        ).exists() # exists() is efficient for a boolean check

        # Get all lessons completed by the user in this course (for progress calculation)
        completed_lessons_ids_for_course = set(
            UserLessonProgress.objects.filter(
                user=request.user,
                lesson__module__course=course
            ).values_list('lesson_id', flat=True)
        )
        first_uncompleted_lesson = None
        all_lessons_in_course = Lesson.objects.filter(module__course=course).order_by('module__order', 'order')
        for lesson_obj in all_lessons_in_course:
            if lesson_obj.id not in completed_lessons_ids_for_course:
                first_uncompleted_lesson = lesson_obj
                break
# ... add first_uncompleted_lesson to context
        
        completed_lessons_for_course_count = len(completed_lessons_ids_for_course)
        
        # Calculate progress for each module and overall course progress
        # This logic was already in your student_dashboard_view, let's adapt it here
        for module in modules: # Use the prefetched modules
            current_module_total_lessons = module.lessons.count()
            total_lessons_in_course += current_module_total_lessons
            
            module_lessons_with_completion_status = []
            module_completed_lessons_count = 0

            for lesson in module.lessons.all(): # Access prefetched lessons
                is_lesson_completed = lesson.id in completed_lessons_ids_for_course
                if is_lesson_completed:
                    module_completed_lessons_count += 1
                
                module_lessons_with_completion_status.append({
                    'lesson': lesson,
                    'is_completed': is_lesson_completed
                })
            
            module_progress_percent = (module_completed_lessons_count / current_module_total_lessons * 100) if current_module_total_lessons > 0 else 0
            modules_with_progress.append({
                'module': module,
                'lessons_with_status': module_lessons_with_completion_status,
                'completed_count': module_completed_lessons_count,
                'total_lessons': current_module_total_lessons,
                'progress_percent': round(module_progress_percent)
            })

        if total_lessons_in_course > 0:
            course_progress_percent = (completed_lessons_for_course_count / total_lessons_in_course) * 100

    else: # For anonymous users, we still need to prepare modules_with_progress for display
        for module in modules:
            module_lessons_with_completion_status = []
            for lesson in module.lessons.all():
                module_lessons_with_completion_status.append({
                    'lesson': lesson,
                    'is_completed': False # Anonymous users haven't completed anything
                })
            total_lessons_in_course += module.lessons.count() # Still count total lessons
            modules_with_progress.append({
                'module': module,
                'lessons_with_status': module_lessons_with_completion_status,
                'completed_count': 0,
                'total_lessons': module.lessons.count(),
                'progress_percent': 0
            })


    context = {
        'course': course,
        'modules_with_progress': modules_with_progress, # Use this instead of just 'modules'
        'is_enrolled': is_enrolled, # Crucial: This is now correctly set
        'total_lessons_in_course': total_lessons_in_course,
        'completed_lessons_in_course_count': completed_lessons_for_course_count,
        'course_progress_percent': round(course_progress_percent)
    }
    context['first_uncompleted_lesson'] = first_uncompleted_lesson
    return render(request, 'courses/course_detail.html', context)

# View to display a single lesson's content
@login_required
def lesson_detail_view(request, course_slug, lesson_slug):
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, slug=lesson_slug, module__course=course)
    contents = lesson.contents.all().order_by('order')
    previous_lesson = lesson.get_previous_lesson()
    next_lesson = lesson.get_next_lesson()
    # Check if the user has completed the lesson
    lesson_completed = lesson.user_progress.filter(user=request.user).exists()

    context = {
        'course': course,
        'lesson': lesson,
        'contents': contents,
        'current_module': lesson.module,
        'lesson_completed': lesson_completed,
        'previous_lesson': previous_lesson,
        'next_lesson': next_lesson,  
    }
    return render(request, 'courses/lesson_detail.html', context)

# Placeholder for enrollment view - we'll keep it simple for now
@login_required
def enroll_course_view(request, course_slug): # This view is currently a placeholder
    course = get_object_or_404(Course, slug=course_slug)

    # Check if user has already made any progress in this course
    already_started = UserLessonProgress.objects.filter(
        user=request.user,
        lesson__module__course=course
    ).exists()

    if already_started:
        messages.info(request, f"You are already making progress in '{course.title}'. Keep it up!")
    else:
        # This is where a real Enrollment object would be created.
        # For now, the first lesson completion will "enroll" them for tracking.
        messages.success(request, f"Great choice! You're ready to start '{course.title}'. Dive into the first lesson!")
        # Optionally, redirect to the first lesson of the course if it exists
        first_lesson = Lesson.objects.filter(module__course=course).order_by('module__order', 'order').first()
        if first_lesson:
            return redirect('courses:lesson_detail', course_slug=course.slug, lesson_slug=first_lesson.slug)

    return redirect('courses:course_detail', course_slug=course.slug)


@login_required
@require_POST
def mark_lesson_completed_view(request, lesson_slug):
    lesson = get_object_or_404(Lesson, slug=lesson_slug)
    progress, created = UserLessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

    if created:
        messages.success(request, f"Lesson '{lesson.title}' marked as completed!")
        # Award points for completing a lesson
        points_for_lesson = 10  # Define or make configurable
        request.user.profile.award_points(points_for_lesson, reason=f"Completed Lesson: {lesson.title}")
        messages.info(request, f"You earned {points_for_lesson} points!")

        # Check for course completion
        course = lesson.module.course
        total_lessons_in_course = Lesson.objects.filter(module__course=course).count()
        completed_lessons_in_course = UserLessonProgress.objects.filter(user=request.user, lesson__module__course=course).count()

        if total_lessons_in_course > 0 and completed_lessons_in_course == total_lessons_in_course:
            # Avoid duplicate awarding by checking PointLog reason
            course_completion_reason = f"Completed Course: {course.title}"
            if not PointLog.objects.filter(user_profile=request.user.profile, reason=course_completion_reason).exists():
                points_for_course_completion = 50  # Define course completion points
                request.user.profile.award_points(points_for_course_completion, reason=course_completion_reason)
                messages.success(request, f"Congratulations! You completed the course '{course.title}' and earned {points_for_course_completion} points!")

                # Award specific course completion badge if exists
                try:
                    course_completer_badge = Badge.objects.get(slug=f'completed-{course.slug}')  # Dynamic slug
                    if not UserBadge.objects.filter(user_profile=request.user.profile, badge=course_completer_badge).exists():
                        UserBadge.objects.create(user_profile=request.user.profile, badge=course_completer_badge)
                except Badge.DoesNotExist:
                    # Fallback: award generic course completion badge if exists
                    try:
                        generic_course_badge = Badge.objects.get(slug='course-conqueror')
                        UserBadge.objects.get_or_create(user_profile=request.user.profile, badge=generic_course_badge)
                    except Badge.DoesNotExist:
                        pass
    else:
        messages.info(request, f"Lesson '{lesson.title}' was already completed.")

    return redirect('courses:lesson_detail', course_slug=lesson.module.course.slug, lesson_slug=lesson.slug)
    # Alternative: redirect('courses:course_detail', course_slug=lesson.module.course.slug)
    # Alternative: redirect to next lesson if exists
@login_required
def quiz_detail_view(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions', 'questions__choices'), pk=quiz_id)
    # Check if user has already attempted this quiz (can allow multiple attempts later)
    existing_attempt = UserQuizAttempt.objects.filter(user=request.user, quiz=quiz).order_by('-completed_at').first()

    # For simplicity, let's prevent re-attempts for now or show the last attempt's result
    # This can be made more flexible (e.g., allow N attempts, show best score)
    if existing_attempt and existing_attempt.score is not None: # If graded
         messages.info(request, f"You have already completed this quiz. Your score was {existing_attempt.score}%.")
         return redirect('courses:quiz_result', attempt_id=existing_attempt.id)

    context = {
        'quiz': quiz,
        'questions': quiz.questions.all(), # questions are prefetched
    }
    return render(request, 'courses/quiz_detail.html', context)

    return redirect('courses:quiz_result', attempt_id=attempt.id)



from django.db.models import Q

@login_required
def quiz_result_view(request, attempt_id):
    attempt = get_object_or_404(
        UserQuizAttempt.objects.select_related('user', 'quiz')
                               .prefetch_related('user_answers',
                                                 'user_answers__question',
                                                 'user_answers__question__choices',
                                                 'user_answers__selected_choice'),
        pk=attempt_id
    )

    # Ensure the user viewing the result is the one who took the quiz or an admin/instructor
    if not (request.user == attempt.user or request.user.is_staff):
        messages.error(request, "You do not have permission to view these results.")
        return redirect('courses:course_list')

    quiz = attempt.quiz
    has_saq = quiz.questions.filter(question_type='SAQ').exists()

    context = {
        'attempt': attempt,
        'quiz': quiz,
        'user_answers': attempt.user_answers.all().order_by('question__order'),
        'has_saq': has_saq,
    }
    return render(request, 'courses/quiz_result.html', context)

 # Import the new utility
@login_required
@require_POST # Ensure this view is only called via POST
@transaction.atomic # Ensure all database operations in this view are atomic
def submit_quiz_view(request, quiz_id):
    quiz = get_object_or_404(Quiz.objects.prefetch_related('questions__choices'), pk=quiz_id)
    print(f"--- SUBMIT QUIZ VIEW CALLED for Quiz ID: {quiz_id}, User: {request.user.username} ---")

    # --- Check for existing graded attempts ---
    existing_graded_attempt = UserQuizAttempt.objects.filter(
        user=request.user, 
        quiz=quiz, 
        score__isnull=False # Check if a score has been recorded
    ).order_by('-completed_at').first()

    if existing_graded_attempt:
        messages.error(request, "You have already submitted this quiz and it has been graded.")
        return redirect('courses:quiz_result', attempt_id=existing_graded_attempt.id)

    # --- Create a new attempt ---
    attempt = UserQuizAttempt.objects.create(user=request.user, quiz=quiz)
    print(f"New UserQuizAttempt created: ID {attempt.id} for User '{request.user.username}', Quiz '{quiz.title}'")

    total_mcq_questions_in_quiz = 0
    correct_mcq_answers_count = 0
    
    # Determine if there are any SAQs in this quiz structure upfront
    has_saq_questions_in_quiz = quiz.questions.filter(question_type='SAQ').exists()
    print(f"Quiz '{quiz.title}' has SAQ questions: {has_saq_questions_in_quiz}")

    print(f"--- Starting Question Processing for Attempt ID: {attempt.id} ---")
    for question in quiz.questions.all(): # .all() will use the prefetched choices
        user_answer = UserAnswer(attempt=attempt, question=question)
        print(f"\nProcessing Question ID: {question.id}, Type: {question.question_type}, Text: '{question.question_text[:50]}...'")

        if question.question_type == 'MCQ':
            total_mcq_questions_in_quiz += 1
            form_field_name = f'question_{question.id}'
            selected_choice_id_str = request.POST.get(form_field_name)
            
            print(f"  MCQ: Looking for POST key: '{form_field_name}'")
            print(f"  MCQ: Value from POST for '{form_field_name}': '{selected_choice_id_str}' (Type: {type(selected_choice_id_str)})")

            if selected_choice_id_str and selected_choice_id_str.strip():
                try:
                    choice_pk = int(selected_choice_id_str)
                    selected_choice_obj = AnswerChoice.objects.get(pk=choice_pk, question=question)
                    user_answer.selected_choice = selected_choice_obj
                    print(f"    -> Found and assigned AnswerChoice: '{selected_choice_obj.choice_text}' (ID: {selected_choice_obj.id}, Correct: {selected_choice_obj.is_correct})")
                    if selected_choice_obj.is_correct:
                        correct_mcq_answers_count += 1
                except AnswerChoice.DoesNotExist:
                    print(f"    -> ERROR: AnswerChoice.DoesNotExist for pk={selected_choice_id_str} (int: {choice_pk if 'choice_pk' in locals() else 'N/A'}) and question_id={question.id}")
                    messages.warning(request, f"Invalid choice for question: '{question.question_text[:30]}...'")
                except ValueError:
                    print(f"    -> ERROR: ValueError converting choice_id '{selected_choice_id_str}' to int for question_id={question.id}")
                    messages.warning(request, f"Invalid choice format for: '{question.question_text[:30]}...'")
            else:
                print(f"  MCQ: No choice submitted or empty value for question_id={question.id}.")
        
        elif question.question_type == 'SAQ':
            form_field_name_saq = f'question_{question.id}_saq_text'
            saq_text = request.POST.get(form_field_name_saq, '').strip()
            user_answer.short_answer_text = saq_text
            print(f"  SAQ (QID {question.id}): User text: '{saq_text[:50]}...'")

            MIN_SAQ_LENGTH = getattr(settings, 'SAQ_MIN_LENGTH', 15)
            
            if saq_text and len(saq_text) >= MIN_SAQ_LENGTH:
                print(f"    Calling get_saq_feedback for QID {question.id} (text length: {len(saq_text)})...")
                # ideal_keywords = question.ideal_keywords_list_from_model # If you implement ideal keywords on Question model
                ai_raw_response = get_saq_feedback(question.question_text, saq_text) #, ideal_answer_keywords=ideal_keywords)
                print(f"    Raw AI Response for QID {question.id}: '{ai_raw_response[:200]}...'")
                
                parsed_feedback = ai_raw_response 
                parsed_score = None
                needs_review_flag = True 

                score_match = re.search(r"Preliminary Score:\s*(\d{1,2})/10", ai_raw_response, re.IGNORECASE)
                if score_match:
                    try:
                        ai_score_val = int(score_match.group(1))
                        if 0 <= ai_score_val <= 10:
                            parsed_score = ai_score_val
                            needs_review_flag = False # Assume AI is somewhat confident if score parsed
                            # If score is very low (e.g., < 4), you might still set needs_review_flag = True
                            if parsed_score < 4: # Example threshold for review
                                needs_review_flag = True
                                print(f"      AI Score {parsed_score}/10 is low, flagging for review.")
                            else:
                                print(f"      Parsed AI Score: {parsed_score}/10")
                            parsed_feedback = re.sub(r"Preliminary Score:.*", "", ai_raw_response, flags=re.IGNORECASE).strip()
                        else:
                            print(f"      AI Score {ai_score_val} out of range (0-10). Flagging for review.")
                    except ValueError:
                        print(f"      ERROR: Could not convert parsed score '{score_match.group(1)}' to int. Flagging for review.")
                else:
                    print(f"      Score pattern 'Preliminary Score: X/10' not found in AI response. Flagging for review.")
                
                user_answer.feedback = parsed_feedback
                user_answer.ai_score = parsed_score
                user_answer.needs_review = needs_review_flag
            
            elif not saq_text:
                print(f"    SAQ (QID {question.id}): No answer text provided. Setting score to 0.")
                user_answer.ai_score = 0
                user_answer.feedback = "No answer was provided for this question."
                user_answer.needs_review = False # Or True, if you want admins to see blanks
            else: # Answer was too short
                print(f"    SAQ (QID {question.id}): Answer text too short ('{saq_text}'). Flagging for review.")
                user_answer.feedback = "The provided answer was too short for an effective AI evaluation. Please provide a more detailed response."
                user_answer.needs_review = True
                # user_answer.ai_score = 0 # Optionally score 0 for too short answers
        
        user_answer.save()
        print(f"  Saved UserAnswer (ID: {user_answer.id}): selected_choice_id='{user_answer.selected_choice_id}', "
              f"saq_text='{str(user_answer.short_answer_text)[:20]}...', ai_score={user_answer.ai_score}, "
              f"needs_review={user_answer.needs_review}, feedback='{str(user_answer.feedback)[:30]}...'")

    # --- Calculate final attempt.score ---
    # This example keeps attempt.score based ONLY on MCQs.
    # SAQ scores are stored per UserAnswer.
    # You would need a more complex logic if you want to combine them into one attempt.score.
    
    if total_mcq_questions_in_quiz > 0:
        attempt.score = (correct_mcq_answers_count / total_mcq_questions_in_quiz) * 100
        print(f"Final MCQ Score for Attempt: {attempt.score}% ({correct_mcq_answers_count}/{total_mcq_questions_in_quiz})")
    elif not has_saq_questions_in_quiz: # No MCQs and no SAQs in the quiz
        attempt.score = 0 
        print(f"Quiz has no MCQs and no SAQs. Attempt score set to 0.")
    else: # Only SAQs in the quiz, or MCQs=0 but SAQs exist
        attempt.score = None 
        print(f"Quiz has SAQs and no graded MCQs (or 0 MCQs). Attempt score is None (pending SAQ review for overall grade if applicable).")

    attempt.save() # Save the attempt with the calculated score (or None)
    print(f"Saved UserQuizAttempt ID: {attempt.id} with final score: {attempt.score}")

    # --- Determine user-facing messages ---
    if has_saq_questions_in_quiz:
        if total_mcq_questions_in_quiz > 0 and attempt.score is not None:
             messages.success(request, f"Quiz submitted! Your MCQ score is {attempt.score:.0f}%. Short answers have been evaluated by AI and may be reviewed by an instructor.")
        else: # Only SAQs, or score is None because no MCQs
            messages.info(request, "Your short answers have been submitted and evaluated by AI. They may be reviewed by an instructor.")
    elif attempt.score is not None: # Only MCQs scored (and no SAQs in quiz)
        messages.success(request, f"Quiz submitted! Your score is {attempt.score:.0f}%.")
    else: # Should ideally not be reached if logic is sound, but as a catch-all
        messages.info(request, "Quiz submitted. Awaiting grading or review.")

    return redirect('courses:quiz_result', attempt_id=attempt.id)