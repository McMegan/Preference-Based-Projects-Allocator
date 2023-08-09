from typing import Any
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.views.generic import CreateView, TemplateView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, resolve, reverse
from django.contrib.auth import login
from django.views.generic.edit import FormMixin


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


class StudentRegistrationView(FormMixin, TemplateView):
    form_class = forms.StudentUserRegistrationForm
    model = models.User
    template_name = 'registration/account_create.html'
    success_url = reverse_lazy('index')

    def get_queryset(self):
        return models.User.objects.all()

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        form = self.get_form()
        if form.is_valid():
            # Set as student
            form.instance.is_student = True
            user = form.save()
            # Add to enrolled units
            enrolled_student_objects = models.EnrolledStudent.objects.filter(
                student_id=form.instance.username)
            if enrolled_student_objects.exists():
                for enrolled_student in enrolled_student_objects:
                    enrolled_student.user = form.instance
                    enrolled_student.save()
            # Log user in
            login(request, user)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
