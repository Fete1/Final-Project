from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required # For views that require login

from .forms import  UserUpdateForm, ProfileUpdateForm # Add new forms
from .models import Profile # If not already imported
from django.contrib.auth import logout, login # For logout and login functionality
from .utils import send_verification_email # Import your email utility
import uuid # For parsing token in verify_email_view
from django.conf import settings # For site domain and other settings
from django.utils import timezone # For handling time-related checks
from users.models import UserBadge # Import UserBadge model
# Import models from courses app
from .models import CustomUser # Import your custom user model
from django.contrib.auth import get_user_model # To get the custom user model
from .forms import CustomUserCreationForm, ProfileUpdateForm # Import forms
from courses.models import Course, Lesson, Module, UserLessonProgress, UserQuizAttempt
@login_required # Decorator to ensure only logged-in users can access
def profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES, # For file uploads like profile picture
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('users:profile') # Redirect to profile page
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile.html', context)

def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home') 

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # Use custom form
        if form.is_valid():
            new_user = form.save(commit=False) # Don't save yet
            # is_active is already False by default in CustomUser model
            new_user.save() # Now save the user

            # Profile signal will create the profile and generate token
            # We just need to send the email if profile was created successfully
            if hasattr(new_user, 'profile'):
                # Check if it's a superuser being created via manage.py createsuperuser
                # (though that flow doesn't hit this view typically)
                # For regular signups, they shouldn't be superusers.
                if not new_user.is_superuser: 
                    if send_verification_email(new_user.profile):
                        messages.success(request, f'Account created for {new_user.email}! Please check your email to verify your account.')
                    else:
                        messages.error(request, 'Account created, but we had trouble sending a verification email.')
                else: # Superuser created via some other means (e.g. admin form) might hit here
                    messages.success(request, f'Superuser account {new_user.email} created.')
            else:
                messages.error(request, "Profile setup failed. Contact support.")
            return redirect('users:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form, 'page_title': 'Sign Up'})
 

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from django.db.models import Q

# You might want to move get_tfidf_data to a shared utils or services.py
# For now, let's assume it's accessible or re-defined here if it was global in core/views.py
# (It's better to make get_tfidf_data a utility function callable from anywhere)

# --- Re-integrate or call get_tfidf_data() here ---
# Global or cached TF-IDF (from previous core/views.py, needs to be accessible)
# This part might need refactoring if TFIDF_VECTORIZER etc. were global in core/views.py
# Let's assume for now we have a utility function like core.recommendation_utils.get_tfidf_data()
# Or, for simplicity here, we'll redefine it briefly. Ideally, refactor to a common place.


_TFIDF_VECTORIZER = None
_TFIDF_MATRIX = None
_TFIDF_COURSE_IDS = []

def _get_dashboard_tfidf_data():
    global _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS
    # In a real app, add cache invalidation if courses are updated
    if _TFIDF_VECTORIZER is None or _TFIDF_MATRIX is None: # or some cache check
        
        # MODIFIED LINE: Fetch all courses, or courses with non-empty descriptions
        # We don't need to filter by the 'embedding' field for TF-IDF
        all_courses_qs = Course.objects.all() 
        # Optionally, filter for courses that have a description:
        # all_courses_qs = Course.objects.filter(description__isnull=False).exclude(description__exact='')

        all_courses_list = list(all_courses_qs) # Convert to list for consistent indexing
        
        if not all_courses_list:
            _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS = None, None, []
            print("TF-IDF: No courses found to build matrix.") # Debug
            return _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS

        _TFIDF_COURSE_IDS = [course.id for course in all_courses_list]
        
        corpus = []
        valid_course_indices = [] # Keep track of courses that actually have content
        temp_course_ids_map = []

        for i, course in enumerate(all_courses_list):
            content = course.get_content_for_embedding() # This method should just get text
            if content and content.strip(): # Ensure content is not empty
                corpus.append(content)
                valid_course_indices.append(i) # Store original index
                temp_course_ids_map.append(course.id) # Store ID of valid course
            # else:
                # print(f"TF-IDF: Course '{course.title}' (ID: {course.id}) has no content for TF-IDF, skipping.")

        if not corpus: # If no courses had valid content
            _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS = None, None, []
            print("TF-IDF: No valid content found in any course to build matrix.") # Debug
            return _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS

        _TFIDF_COURSE_IDS = temp_course_ids_map # Update with IDs of courses actually in the corpus

        _TFIDF_VECTORIZER = TfidfVectorizer(stop_words='english', max_df=0.85, min_df=1, ngram_range=(1,2))
        _TFIDF_MATRIX = _TFIDF_VECTORIZER.fit_transform(corpus)
        print(f"TF-IDF Matrix computed/recomputed for dashboard. Shape: {_TFIDF_MATRIX.shape}") # Debug
        
    return _TFIDF_VECTORIZER, _TFIDF_MATRIX, _TFIDF_COURSE_IDS
@login_required
def student_dashboard_view(request):
    user = request.user

    # 1. Courses interacted with (proxy for enrolled)
    interacted_course_ids = UserLessonProgress.objects.filter(user=user)\
                                                  .values_list('lesson__module__course_id', flat=True)\
                                                  .distinct()
    interacted_courses = Course.objects.filter(id__in=interacted_course_ids)
    num_interacted_courses = interacted_courses.count()

    # 2. Total lessons completed by the user
    total_lessons_completed = UserLessonProgress.objects.filter(user=user).count()

    # 3. Overall progress calculation (average progress across interacted courses)
    total_progress_percentage_sum = 0
    courses_with_progress_count = 0
    detailed_course_progress = []  # To show progress for each course

    for course in interacted_courses.prefetch_related('modules__lessons'):
        course_total_lessons = 0
        for module in course.modules.all():
            course_total_lessons += module.lessons.count()

        # Get lessons completed by the user specifically for this course
        course_completed_lessons = UserLessonProgress.objects.filter(
            user=user,
            lesson__module__course=course
        ).count()

        if course_total_lessons > 0:
            progress_percent = (course_completed_lessons / course_total_lessons) * 100
            total_progress_percentage_sum += progress_percent
            courses_with_progress_count += 1
            detailed_course_progress.append({
                'course': course,
                'progress_percent': round(progress_percent),
                'completed_lessons': course_completed_lessons,
                'total_lessons': course_total_lessons,
            })
        else:
            detailed_course_progress.append({
                'course': course,
                'progress_percent': 0,
                'completed_lessons': 0,
                'total_lessons': 0,
            })

    overall_average_progress = (total_progress_percentage_sum / courses_with_progress_count) if courses_with_progress_count > 0 else 0

    # 4. Recently completed lessons
    recent_lessons_completed = UserLessonProgress.objects.filter(user=user)\
                                                         .select_related('lesson', 'lesson__module__course')\
                                                         .order_by('-completed_at')[:5]
    # --- Recommendation Logic for Dashboard ---
    recommended_courses_for_dashboard = []
    vectorizer, tfidf_matrix, course_ids_map = _get_dashboard_tfidf_data() # Use the (potentially local) TF-IDF getter

    if vectorizer and tfidf_matrix is not None and course_ids_map:
        interacted_course_ids_set = set(
            UserLessonProgress.objects.filter(user=user)
                                    .values_list('lesson__module__course_id', flat=True)
                                    .distinct()
        )

        if interacted_course_ids_set:
            user_profile_indices = [i for i, course_id in enumerate(course_ids_map) if course_id in interacted_course_ids_set]
            if user_profile_indices:
                user_interacted_vectors = tfidf_matrix[user_profile_indices]
                user_profile_vector_tf = np.mean(user_interacted_vectors.toarray(), axis=0)

                if user_profile_vector_tf.any():
                    similarities = cosine_similarity(user_profile_vector_tf.reshape(1, -1), tfidf_matrix)[0]
                    rec_candidates = []
                    for i, course_id in enumerate(course_ids_map):
                        if course_id not in interacted_course_ids_set:
                            rec_candidates.append({'course_id': course_id, 'similarity': similarities[i]})
                    rec_candidates.sort(key=lambda x: x['similarity'], reverse=True)
                    top_n_ids = [rec['course_id'] for rec in rec_candidates[:3]] # Top 3 for dashboard

                    if top_n_ids:
                        courses_dict = {c.id: c for c in Course.objects.filter(id__in=top_n_ids)}
                        recommended_courses_for_dashboard = [courses_dict[id] for id in top_n_ids if id in courses_dict]
    
    # Fallback recommendations for dashboard if AI ones fail or not enough data
    #if not recommended_courses_for_dashboard:
        #fallback_ids_to_exclude = interacted_course_ids_set
        #recommended_courses_for_dashboard = list(
            #ourse.objects.exclude(id__in=fallback_ids_to_exclude).order_by('?')[:3] # Random 3 as fallback
        #)
    # --- End Recommendation Logic ---

    # 5. Gamification Data — fetch actual badges and points
    user_profile = user.profile
    badges_earned = UserBadge.objects.filter(user_profile=user_profile).select_related('badge')
    total_points = user_profile.points
    level_info = user_profile.current_level_info
    
    # 6. Recent quiz attempts
    recent_quiz_attempts = UserQuizAttempt.objects.filter(user=user)\
                                                  .select_related('quiz')\
                                                  .order_by('-completed_at')[:3]

    context = {
        'recommended_courses_dashboard': recommended_courses_for_dashboard,
        'num_interacted_courses': num_interacted_courses,
        'total_lessons_completed': total_lessons_completed,
        'overall_average_progress': round(overall_average_progress),
        'detailed_course_progress': detailed_course_progress,
        'recent_lessons_completed': recent_lessons_completed,
        'badges_earned': badges_earned,
        'total_points': total_points,
        'level_info': level_info,
        'recent_quiz_attempts': recent_quiz_attempts,
        'page_title': f'Welcome back, {user.email}!',
    }
    return render(request, 'users/student_dashboard.html', context)
# users/views.py
# ... (other imports) ...

def verify_email_view(request, token):
    try:
        token_uuid = uuid.UUID(str(token)) # Ensure token is treated as string before UUID conversion
        profile = get_object_or_404(Profile, email_verification_token=token_uuid)
    except (ValueError, TypeError, Profile.DoesNotExist): # Catch more potential errors with UUID conversion
        messages.error(request, 'The verification link is invalid or has already been used.')
        return redirect('users:login') # Or a more specific error page

    user_to_verify = profile.user

    # --- Optional: Implement Token Expiry ---
    # This requires `email_verification_sent_at` to be set when the token is generated/sent.
    # And `EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS` in settings.py
    token_expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24) # Default to 24 hours
    if profile.email_verification_sent_at and \
       (timezone.now() > profile.email_verification_sent_at + timezone.timedelta(hours=token_expiry_hours)):
        messages.error(request, 'The verification link has expired. Please request a new one or try registering again.')
        # Optionally, offer a way to resend the verification email here if the user is identifiable
        # For now, just redirect to login. User might need to re-register or use a "forgot password" flow that also verifies.
        # You could also regenerate and resend the token here automatically if desired,
        # but that might have security implications if the email was compromised.
        profile.generate_email_verification_token() # Generate a new token
        # from .utils import send_verification_email # Avoid circular import if utils imports views
        # send_verification_email(profile) # Resend (careful with potential loops or abuse)
        return redirect('users:login') 
    # --- End Token Expiry Check ---

    if user_to_verify.is_active and profile.email_verified:
        messages.info(request, 'Your email address has already been verified. Please log in.')
        return redirect('users:login')
    
    if not user_to_verify.is_active and not profile.email_verified:
        user_to_verify.is_active = True
        user_to_verify.save(update_fields=['is_active'])

        profile.email_verified = True
        profile.email_verification_token = None # Invalidate token after use
        # profile.email_verification_sent_at = None # Clearing this might not be necessary, could be useful for audit
        profile.save(update_fields=['email_verified', 'email_verification_token'])
        
        messages.success(request, 'Thank you for verifying your email address! Your account is now active.')
        
        # --- Auto-Login User After Verification ---
        # This is a good user experience.
        # Ensure 'django.contrib.auth.backends.ModelBackend' is in your AUTHENTICATION_BACKENDS
        login(request, user_to_verify, backend='django.contrib.auth.backends.ModelBackend')
        messages.info(request, f"Welcome, {user_to_verify.first_name}! You are now logged in.")
        return redirect(settings.LOGIN_REDIRECT_URL) # Redirect to their dashboard or intended page
    
    elif user_to_verify.is_active and not profile.email_verified:
        # This case is unusual: user is active but email not marked verified.
        # Could happen if is_active was manually set, or if a previous verification attempt partially failed.
        # Let's just mark email as verified and clear token.
        profile.email_verified = True
        profile.email_verification_token = None
        profile.save(update_fields=['email_verified', 'email_verification_token'])
        messages.info(request, 'Your email has now been marked as verified. You can log in if you are not already.')
        if not request.user.is_authenticated: # If somehow they weren't auto-logged in
             login(request, user_to_verify, backend='django.contrib.auth.backends.ModelBackend')
             return redirect(settings.LOGIN_REDIRECT_URL)
        # If they were already logged in (e.g. admin activated them), just message.
        return redirect(settings.LOGIN_REDIRECT_URL if request.user.is_authenticated else 'users:login')

    else:
        # Should not be reached if other conditions are met.
        messages.error(request, 'An unexpected error occurred during email verification. Please contact support.')
        return redirect('users:login')


# Optional: View to resend verification email
@login_required # User must be logged in but inactive to access this
def resend_verification_email_view(request):
    user = request.user
    if user.is_active and hasattr(user, 'profile') and user.profile.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('users:student_dashboard') # Or core:home
    
    if hasattr(user, 'profile'):
        user.profile.generate_email_verification_token() # Generates a new token
        if send_verification_email(user.profile):
            messages.success(request, f"A new verification email has been sent to {user.email}. Please check your inbox.")
        else:
            messages.error(request, "There was an issue sending the verification email. Please try again or contact support.")
    else:
        messages.error(request, "Could not find your profile to resend verification email.")
        
    return redirect('users:login') # Or a page confirming email was resent
def logout_view(request):
    logout(request)
    return redirect('users:login')