# ai_elearning_platform/courses/urls.py
from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list_view, name='course_list'),

    # Quiz URLs — placed before slug-based routes to avoid conflict
    path('quiz/<int:quiz_id>/', views.quiz_detail_view, name='quiz_detail'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz_view, name='submit_quiz'),
    path('quiz/result/<int:attempt_id>/', views.quiz_result_view, name='quiz_result'),

    # Enrollment
    path('enroll/<slug:course_slug>/', views.enroll_course_view, name='enroll_course'),

    # Lesson completion
    path('lesson/complete/<slug:lesson_slug>/', views.mark_lesson_completed_view, name='mark_lesson_completed'),

    # Course and lesson detail — placed after all fixed paths
    path('<slug:course_slug>/', views.course_detail_view, name='course_detail'),
    path('<slug:course_slug>/<slug:lesson_slug>/', views.lesson_detail_view, name='lesson_detail'),
]
