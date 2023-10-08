from django.contrib.auth import views as auth_views
from django.urls import path, include

from . import views


urlpatterns = [
    path('', views.index_view, name='index'),

    path('register/', views.StudentRegistrationView.as_view(), name='register'),

    path('account/', views.AccountUpdateView.as_view(), name='account'),

    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),

    path('password_change/', views.PasswordChangeView.as_view(),
         name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(),
         name='password_change_done',),

    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm',),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(),
         name='password_reset_complete',),

    path('', include('django.contrib.auth.urls')),
]
