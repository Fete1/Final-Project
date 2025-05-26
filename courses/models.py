from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Course(models.Model):
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_taught')
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    embedding = models.JSONField(null=True, blank=True, help_text="Embedding vector for course content.")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    def get_content_for_embedding(self):
        parts = [self.title, self.description]
        return " ".join(filter(None, parts))


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - Module {self.order}: {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
    
    def get_previous_lesson(self):
        """Returns the previous lesson in the same module based on order, or None."""
        previous_lessons = Lesson.objects.filter(
            module=self.module,
            order__lt=self.order
        ).order_by('-order') # Get lessons before this one, highest order first
        return previous_lessons.first()

    def get_next_lesson(self):
        """Returns the next lesson in the same module based on order, or None."""
        next_lessons = Lesson.objects.filter(
            module=self.module,
            order__gt=self.order
        ).order_by('order') # Get lessons after this one, lowest order first
        return next_lessons.first()

    def __str__(self):
        return f"{self.module.title} - Lesson {self.order}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            unique_slug = base_slug
            num = 1
            while Lesson.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{base_slug}-{num}'
                num += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)


class Quiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Quizzes"


class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice Question'),
        ('SAQ', 'Short Answer Question'),
    ]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=3, choices=QUESTION_TYPE_CHOICES, default='MCQ')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."


class AnswerChoice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.choice_text} ({'Correct' if self.is_correct else 'Incorrect'})"


class UserQuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # NEW
        on_delete=models.CASCADE, 
        related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s attempt on {self.quiz.title} - Score: {self.score or 'Not graded'}"

    def calculate_score(self):
        total_mcq = self.quiz.questions.filter(question_type='MCQ').count()
        if total_mcq == 0:
            self.score = None
            self.save()
            return
        correct = 0
        for answer in self.user_answers.filter(question__question_type='MCQ'):
            if answer.selected_choice and answer.selected_choice.is_correct:
                correct += 1
        self.score = (correct / total_mcq) * 100
        self.save()


class UserAnswer(models.Model):
    attempt = models.ForeignKey(UserQuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(AnswerChoice, on_delete=models.SET_NULL, null=True, blank=True)
    short_answer_text = models.TextField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True, help_text="AI generated feedback for SAQ.") 
    ai_score = models.PositiveSmallIntegerField(null=True, blank=True, help_text="AI generated score for SAQ (0-10).")
    needs_review = models.BooleanField(default=False, help_text="Flag indicating if the SAQ needs human review.") 

    def __str__(self):
        if self.question.question_type == 'MCQ' and self.selected_choice:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.selected_choice.choice_text[:30]}...'"
        elif self.question.question_type == 'SAQ' and self.short_answer_text:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.short_answer_text[:30]}...'"
        return f"Answer for Q: {self.question.id} in Attempt: {self.attempt.id}"
    def __str__(self):
        if self.question.question_type == 'MCQ' and self.selected_choice:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.selected_choice.choice_text[:30]}...'"
        elif self.question.question_type == 'SAQ' and self.short_answer_text:
            return f"Answer to '{self.question.question_text[:30]}...' -> '{self.short_answer_text[:30]}...'"
        return f"Answer for Q: {self.question.id} in Attempt: {self.attempt.id}"


CONTENT_TYPE_CHOICES = [
    ('text', 'Text Content'),
    ('video', 'Video Embed URL'),
    ('file', 'File Upload'),
    ('quiz', 'Quiz Link'),
]


class Content(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    order = models.PositiveIntegerField(default=0)

    text_content = models.TextField(blank=True, null=True)
    video_embed_url = models.URLField(blank=True, null=True)
    file_upload = models.FileField(upload_to='lesson_files/', blank=True, null=True)
    quiz_link = models.ForeignKey(Quiz, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Content for {self.lesson.title} ({self.get_content_type_display()}) - Order: {self.order}"


class UserLessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')
        verbose_name_plural = "User Lesson Progress Entries"

    def __str__(self):
        return f"{self.user.username} completed {self.lesson.title}"
