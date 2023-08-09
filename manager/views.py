from django.db import models
from django.http import HttpRequest
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.db.models import Count
from django.views.generic.edit import FormMixin

import csv
from io import StringIO


from core import models
from . import forms


def user_is_manager(user):
    return user.is_manager


def user_manages_unit(user, queryset):
    return queryset.filter(manager_id=user.id).exists()


def user_manages_unit_pk(user, pk):
    return user.managed_units.filter(pk=pk).exists()


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.Unit
    template_name = 'manager/index.html'

    def get_queryset(self):
        return self.request.user.managed_units.all()

    def test_func(self):
        return user_is_manager(self.request.user)


class UnitCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = forms.UnitForm
    template_name = 'manager/unit_new.html'
    success_url = reverse_lazy('manager-index')

    def post(self, request: HttpRequest, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.manager_id = request.user.id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_queryset(self):
        return self.request.user.managed_units.all()

    def test_func(self):
        return user_is_manager(self.request.user)


class UnitDetailView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Unit
    form_class = forms.UnitForm
    # success_url = reverse_lazy('index')
    template_name = 'manager/unit_form.html'

    def get_success_url(self):
        return self.request.path

    def get_initial(self):
        initial = super().get_initial()
        object_dict = self.get_object().__dict__
        for field in self.form_class.Meta.fields:
            if field in object_dict:
                initial[field] = object_dict[field]
        return initial

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().filter(pk=self.kwargs['pk']).prefetch_related(
            'projects').prefetch_related('enrolled_students').annotate(students_count=Count('enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit(self.request.user, self.get_queryset())


class UnitDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_confirm_delete.html'

    def get_queryset(self):
        return self.request.user.managed_units.all()

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit(self.request.user, self.get_queryset())


class UnitStudentsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
        List of students in unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/unit_students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.request.user.managed_units.get(
            pk=self.kwargs['pk_unit'])
        return context

    def get_queryset(self):
        return super().get_queryset().prefetch_related('user').filter(unit=self.kwargs['pk_unit'])

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentsCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = forms.StudentForm
    template_name = 'manager/unit_students_new.html'

    def get_success_url(self):
        return reverse('manager-unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request: HttpRequest, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.request.user.managed_units.get(
            pk=self.kwargs['pk_unit'])
        return context

    def get_queryset(self):
        return super().get_queryset().prefetch_related('user').filter(unit=self.kwargs['pk_unit'])

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentUploadListView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Upload list of students
    """
    form_class = forms.StudentListForm
    template_name = 'manager/unit_students_new_list.html'

    def get_success_url(self):
        return reverse('manager-unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request: HttpRequest, *args, **kwargs):
        # form = self.get_form()
        form = forms.StudentListForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('list_override'):
                # Clear previous enrolled students
                models.EnrolledStudent.objects.filter(
                    unit_id=self.kwargs['pk_unit']).delete()

            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            csv_data = csv.DictReader(
                StringIO(file.read().decode('utf-8')), delimiter=',')
            column_name = form.cleaned_data.get('column_name')

            enrolled_students = []
            for row in csv_data:
                enrolled_student = models.EnrolledStudent()
                enrolled_student.student_id = row[column_name]
                enrolled_student.unit_id = self.kwargs['pk_unit']
                # Check if user account exists for student
                user = models.User.objects.filter(username=row[column_name])
                if user.exists():
                    enrolled_student.user_id = user.first().id
                enrolled_students.append(enrolled_student)

            models.EnrolledStudent.objects.bulk_create(
                enrolled_students,
                update_conflicts=True,
                update_fields=['student_id', 'unit_id'],
            )

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.request.user.managed_units.get(
            pk=self.kwargs['pk_unit'])
        return context

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentsDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = models.EnrolledStudent
    template_name = 'manager/unit_students_detail.html'

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().prefetch_related('user').prefetch_related('user__project_preferences')

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentsDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_student_confirm_delete.html'

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])
