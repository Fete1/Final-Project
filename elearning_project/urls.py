# ai_elearning_platform/elearning_project/urls.py
from django.contrib import admin
from django.urls import path, include # Add include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')), # Add this line for the core app
]