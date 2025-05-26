# ai_elearning_platform/core/urls.py
from django.urls import path
from . import views 

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('api/chatbot_stream/', views.chatbot_api_stream_view, name='chatbot_api_stream'), 
]