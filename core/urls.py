# ai_elearning_platform/core/urls.py
from django.urls import path
from . import views # import views from the current directory (core app)

app_name = 'core' # Namespace for this app's URLs

urlpatterns = [
    path('', views.home_view, name='home'),
]