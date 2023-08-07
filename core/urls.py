from django.urls import path, re_path, include
from django.contrib.auth import views as auth_views
from . import views
from . import forms

print(auth_views)

urlpatterns = [
    path('', views.index_view, name='index'),

    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html',
         authentication_form=forms.UserLoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html', form_class=forms.UserPasswordResetForm), name='password_reset'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html', form_class=forms.UserPasswordChangeForm), name='password_change'),


    # CUSTOMISE THESE
    path('', include('django.contrib.auth.urls')),
]
