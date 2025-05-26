# ai_elearning_platform/courses/admin.py
from django.contrib import admin
from .models import *

# To allow inline editing of Modules within a Course, Lessons within a Module, etc.
class ContentInline(admin.TabularInline): # Or admin.StackedInline for a different layout
    model = Content
    extra = 1 # Number of empty forms to display for adding new content

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    show_change_link = True # Allows clicking to the Lesson's own admin page
    prepopulated_fields = {'slug': ('title',)} # Auto-populate slug from title

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    show_change_link = True

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'instructor__username')
    list_filter = ('instructor', 'created_at')
    prepopulated_fields = {'slug': ('title',)} # Auto-populate slug from title
    inlines = [ModuleInline] # Allows adding/editing modules directly on the course page

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    inlines = [LessonInline] # Allows adding/editing lessons directly on the module page
    list_editable = ('order',) # Allows editing 'order' directly in the list view

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')
    list_filter = ('module__course', 'module') # Filter by course, then by module
    search_fields = ('title', 'module__title')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ContentInline] # Allows adding/editing content directly on the lesson page
    list_editable = ('order',)

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('get_lesson_title', 'content_type', 'order')
    list_filter = ('lesson__module__course', 'lesson__module', 'content_type')
    search_fields = ('lesson__title', 'text_content', 'video_embed_url')
    list_editable = ('order',)

    def get_lesson_title(self, obj):
        return obj.lesson.title
    get_lesson_title.admin_order_field = 'lesson'  # Allows column sorting by lesson
    get_lesson_title.short_description = 'Lesson Title'  # Column header
@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'completed_at')
    list_filter = ('user', 'lesson__module__course', 'completed_at')
    search_fields = ('user__username', 'lesson__title')

class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 1 # Start with 1 empty choice form for MCQs
    # Only show this inline if the question_type is 'MCQ' (requires custom admin form logic or JavaScript)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text_shortened', 'quiz', 'question_type', 'order')
    list_filter = ('quiz', 'question_type')
    search_fields = ('question_text', 'quiz__title')
    inlines = [AnswerChoiceInline] # For adding choices to MCQs
    list_editable = ('order',)

    def question_text_shortened(self, obj):
        return obj.question_text[:75] + '...' if len(obj.question_text) > 75 else obj.question_text
    question_text_shortened.short_description = 'Question Text'

class QuestionInline(admin.StackedInline): # Or TabularInline
    model = Question
    extra = 1
    show_change_link = True
    # Might want to conditionally show AnswerChoiceInline within this if type is MCQ (advanced)

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson_link_display', 'created_at')
    list_filter = ('lesson__module__course', 'created_at')
    search_fields = ('title', 'description')
    inlines = [QuestionInline] # For adding questions to quizzes

    def lesson_link_display(self, obj):
        if obj.lesson:
            return obj.lesson.title
        return "Standalone Quiz"
    lesson_link_display.short_description = "Linked Lesson (if any)"


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ('choice_text', 'question_link', 'is_correct')
    list_filter = ('question__quiz', 'is_correct')
    search_fields = ('choice_text', 'question__question_text')

    def question_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:courses_question_change", args=[obj.question.id])
        return format_html('<a href="{}">{}</a>', link, obj.question.question_text[:50] + "...")
    question_link.short_description = 'Question'

# Admin for UserQuizAttempt and UserAnswer (mostly for viewing/debugging)
class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0 # Don't allow adding answers here, just viewing
    can_delete = False
    readonly_fields = ('question', 'selected_choice', 'short_answer_text') # Make fields read-only

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'completed_at')
    list_filter = ('user', 'quiz', 'completed_at')
    search_fields = ('user__username', 'quiz__title')
    inlines = [UserAnswerInline]
    readonly_fields = ('user', 'quiz', 'score', 'completed_at') # Make main fields read-only

  