from django.contrib.auth import login
from django.db import models
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin


from . import models
from . import forms


def index_view(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student:index')
        if request.user.is_manager:
            return redirect('manager:index')
        if request.user.is_superuser:
            return redirect('admin:index')
    return redirect('login')


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
