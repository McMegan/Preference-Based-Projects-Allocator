from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from core import forms

admin.site.site_header = 'Capstone Projects Allocator - Admin'
admin.site.site_title = 'Capstone Projects Allocator - Admin'
admin.site.index_title = 'Site Administration'


urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    # path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls'), name='core'),


    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html',
         authentication_form=forms.UserLoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html', form_class=forms.UserPasswordResetForm), name='password_reset'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html', form_class=forms.UserPasswordChangeForm), name='password_change'),


    path('__debug__/', include('debug_toolbar.urls')),
    path('__reload__/', include('django_browser_reload.urls')),
]
