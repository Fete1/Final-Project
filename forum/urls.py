from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.forum_home_view, name='forum_home'),
    path('category/<slug:category_slug>/', views.category_detail_view, name='category_detail'),
    path('category/<slug:category_slug>/create_thread/', views.create_thread_view, name='create_thread'),
    path('category/<slug:category_slug>/thread/<slug:thread_slug>/', views.thread_detail_view, name='thread_detail'),
    # Add URLs for edit_post, delete_post, etc. later
]