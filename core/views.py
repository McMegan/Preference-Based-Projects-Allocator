from django.db import models
from django.views.generic import CreateView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, resolve, reverse

from . import models
from . import forms


def index_view(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student-index')
        if request.user.is_manager:
            return redirect('manager-index')
        if request.user.is_superuser:
            return redirect('admin')
    return redirect('login')


class StudentRegistrationView(CreateView):
    form_class = forms.StudentUserRegistrationForm
    model = models.User
    template_name = 'registration/account_create.html'
    success_url = reverse_lazy('index')

    def get_queryset(self):
        return models.User.objects.all()
