from django.urls import path
from django.views.generic import RedirectView
from . import views
from django.contrib.auth import views as auth_views

app_name = 'quiz'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='quiz:login'), name='logout'),
    path('next/', views.next_question_view, name='next_question'),
    path('question/<int:question_id>/', views.question_detail_view, name='question_detail'),
    path('', RedirectView.as_view(pattern_name='quiz:login'), name='quiz_redirect'),
]