from django.urls import path
from django.contrib.auth import views as auth_views # Django's built-in auth views
from . import views as user_views # Your custom views
from . import views
from .forms import EmailLoginForm
app_name = 'users'

urlpatterns = [
    path('register/', user_views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(
                            template_name='users/login.html',
                            authentication_form=EmailLoginForm # Use your custom form
                            ), name='login'),
    path('logout/', views.logout_view, name='logout'),
  path('verify-email/<uuid:token>/', user_views.verify_email_view, name='verify_email'),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(template_name='users/password_reset.html',email_template_name='users/password_reset_email.html', ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
         name='password_reset_complete'),
    path('profile/', user_views.profile_view, name='profile'),
    path('dashboard/', user_views.student_dashboard_view, name='student_dashboard'),
]