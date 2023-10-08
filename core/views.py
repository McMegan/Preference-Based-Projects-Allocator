from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin

from django_filters.views import FilterView

from . import models
from . import forms
from . import filters


def index_view(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student:index')
        if request.user.is_manager:
            return redirect('manager:index')
        if request.user.is_superuser:
            return redirect('admin:index')
    return redirect('login')


class IndexView(LoginRequiredMixin, UserPassesTestMixin, FilterView):
    model = models.Unit
    template_name = 'core/index.html'
    paginate_by = 10

    def get_filter_formhelper_class(self):
        if self.request.user.is_manager and self.request.path == reverse('manager:index'):
            return filters.ManagerUnitFilterFormHelper
        return filters.UnitFilterFormHelper

    def get_filterset_class(self):
        if self.request.user.is_manager and self.request.path == reverse('manager:index'):
            return filters.ManagerUnitFilter
        return filters.UnitFilter

    def get_filterset(self, filterset_class):
        kwargs = self.get_filterset_kwargs(filterset_class)
        filterset = filterset_class(**kwargs)
        filterset.form.helper = self.get_filter_formhelper_class()()
        return filterset

    def get_context_data(self, **kwargs):
        f = self.get_filterset(self.get_filterset_class())
        return {**super().get_context_data(**kwargs), 'filter': f, 'has_filter': any(
            field in self.request.GET for field in set(f.get_fields()))}

    def test_func(self):
        return self.request.user.is_manager or self.request.user.is_student


"""

Registration Views

"""


class AccountUpdateView(LoginRequiredMixin, FormMixin, TemplateView):
    template_name = 'registration/account_update.html'
    form_class = forms.AccountUpdateForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'user': self.request.user}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('index')


class StudentRegistrationView(FormMixin, TemplateView):
    form_class = forms.StudentUserRegistrationForm
    model = models.User
    template_name = 'registration/account_create.html'
    success_url = reverse_lazy('index')

    def get_queryset(self):
        return models.User.objects.all()

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            # Set as student
            form.instance.is_student = True
            user = form.save()
            # Add to enrolled units
            student_objects = models.Student.objects.filter(
                student_id=user.username)
            if student_objects.exists():
                for student in student_objects:
                    student.user = user
                    student.save()
            # Log user in
            login(request, user)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class LoginView(auth_views.LoginView):
    template_name = 'registration/login.html'
    authentication_form = forms.UserLoginForm


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = 'registration/password_change.html'
    form_class = forms.UserPasswordChangeForm

class PasswordResetView(auth_views.PasswordResetView):
    form_class=forms.UserPasswordResetForm

class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class=forms.UserPasswordSetForm