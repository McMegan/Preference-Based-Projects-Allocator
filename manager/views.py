from typing import Any, Dict, Optional
from django.db import models
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.db.models import Count
from django.views.generic.edit import FormMixin
from django.db.models import Q

import csv
from io import StringIO


from core import models
from . import forms


def get_context_for_sidebar(pk_unit):
    unit_queryset = models.Unit.objects.filter(pk=pk_unit).prefetch_related(
        'projects').prefetch_related('enrolled_students').annotate(students_count=Count('enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))
    unit = unit_queryset.first()
    nav_links = [
        {'url': reverse('manager-unit-detail',
                        kwargs={'pk': pk_unit}), 'label': unit, 'classes': ''},
        # Students
        {'url': reverse('manager-unit-students',
                        kwargs={'pk_unit': pk_unit}), 'label': f'Student List ({unit.students_count})', 'classes': 'ms-3'},
        {'url': reverse('manager-unit-students-new-list',
                        kwargs={'pk_unit': pk_unit}), 'label': 'Upload Student List', 'classes': 'ms-5'},
        {'url': reverse('manager-unit-students-new',
                        kwargs={'pk_unit': pk_unit}), 'label': 'Add Student', 'classes': 'ms-5'},
        {'url': reverse('manager-unit-students-clear',
                        kwargs={'pk_unit': pk_unit}), 'label': 'Clear Student List', 'classes': 'ms-5 link-danger'},
        # Projects
        {'url': reverse('manager-unit-projects',
                        kwargs={'pk_unit': pk_unit}), 'label': f'Project List ({unit.projects_count})', 'classes': 'ms-3'},
        {'url': reverse('manager-unit-projects-new-list',
                        kwargs={'pk_unit': pk_unit}), 'label': 'Upload Project List', 'classes': 'ms-5'},
        {'url': reverse('manager-unit-projects-new',
                        kwargs={'pk_unit': pk_unit}), 'label': 'Add Project', 'classes': 'ms-5'},
        {'url': reverse('manager-unit-projects-clear',
                        kwargs={'pk_unit': pk_unit}), 'label': 'Clear Project List', 'classes': 'ms-5 link-danger'},

        # Preferences
        {'url': reverse('manager-unit-preferences',
                        kwargs={'pk_unit': pk_unit}), 'label': 'Submitted Preferences', 'classes': 'ms-3'},

        # Allocation
        {'url': '#', 'label': 'Allocation', 'classes': 'ms-3'},

        # Delete unit
        {'url': reverse('manager-unit-delete',
                        kwargs={'pk': pk_unit}), 'label': 'Delete Unit', 'classes': 'ms-3 link-danger'},

    ]
    return {'unit_queryset': unit_queryset, 'unit': unit, 'nav_links': nav_links}


def user_is_manager(user):
    return user.is_manager


def user_manages_unit(user, queryset):
    return queryset.filter(manager_id=user.id).exists()


def user_manages_unit_pk(user, pk):
    return user.managed_units.filter(pk=pk).exists()


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.Unit
    template_name = 'core/index.html'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.managed_units.all()

    def test_func(self):
        return user_is_manager(self.request.user)

# Unit Views


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


class UnitDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_confirm_delete.html'

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk'])}

    def get_queryset(self):
        return self.request.user.managed_units.all()

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit(self.request.user, self.get_queryset())


class UnitDetailView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Unit
    form_class = forms.UnitForm
    template_name = 'manager/unit_form.html'

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk'])}

    def get_success_url(self):
        return self.request.path

    def get_initial(self):
        initial = super().get_initial()
        object_dict = self.get_object().__dict__
        for field in self.form_class.Meta.fields:
            if field in object_dict:
                initial[field] = object_dict[field]
        return initial

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.kwargs['pk']).prefetch_related(
            'projects').prefetch_related('enrolled_students').annotate(students_count=Count('enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit(self.request.user, self.get_queryset())


# Unit student views


class UnitStudentsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
        List of students in unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_students.html'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).prefetch_related('user').prefetch_related(Prefetch('user__project_preferences', queryset=models.ProjectPreference.objects.filter(unit_id=self.kwargs['pk_unit'])))

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentsCreateView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Add a single student to the unit's student list
    """
    form_class = forms.StudentForm
    template_name = 'manager/students/unit_students_new.html'

    def get_success_url(self):
        return reverse('manager-unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['pk_unit'] = self.kwargs['pk_unit']
        return kwargs

    def post(self, request: HttpRequest, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            # Check if user account exists for student
            user = models.User.objects.filter(
                username=form.cleaned_data.get('student_id'))
            if user.exists():
                form.instance.user_id = user.first().id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def get_queryset(self):
        return super().get_queryset().prefetch_related('user').filter(unit=self.kwargs['pk_unit'])

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentUploadListView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Upload list of students to a unit
    """
    form_class = forms.StudentListForm
    template_name = 'manager/students/unit_students_new_list.html'

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
                StringIO(file.read().decode('utf-8-sig')), delimiter=',')
            student_id_column = form.cleaned_data.get('student_id_column')

            enrolled_students = []
            for row in csv_data:
                enrolled_student = models.EnrolledStudent()
                enrolled_student.student_id = row[student_id_column]
                enrolled_student.unit_id = self.kwargs['pk_unit']
                # Check if user account exists for student
                user = models.User.objects.filter(
                    username=row[student_id_column])
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
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentsDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
        View a single student in a unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_students_detail.html'

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().prefetch_related('user').prefetch_related('user__project_preferences')

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
        Remove a single student from a unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_student_confirm_delete.html'

    def get_success_url(self):
        return reverse('manager-unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitStudentsClearView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Clear the student list of a unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_students_confirm_delete.html'
    form_class = forms.StudentListClearForm

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            models.EnrolledStudent.objects.filter(
                unit_id=self.kwargs['pk_unit']).delete()

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('manager-unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])

# Unit project views


class UnitProjectsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
        List of projects in unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_projects.html'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def get_queryset(self):
        return super().get_queryset().prefetch_related('unit').filter(unit=self.kwargs['pk_unit'])

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitProjectsCreateView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    form_class = forms.ProjectForm
    template_name = 'manager/projects/unit_projects_new.html'

    def get_success_url(self):
        return reverse('manager-unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['pk_unit'] = self.kwargs['pk_unit']
        return kwargs

    def post(self, request: HttpRequest, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit'])

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitProjectUploadListView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Upload list of projects
    """
    form_class = forms.ProjectListForm
    template_name = 'manager/projects/unit_projects_new_list.html'

    def get_success_url(self):
        return reverse('manager-unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request: HttpRequest, *args, **kwargs):
        # form = self.get_form()
        form = forms.ProjectListForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('list_override'):
                # Clear previous enrolled projects
                models.Project.objects.filter(
                    unit_id=self.kwargs['pk_unit']).delete()

            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            csv_data = csv.DictReader(
                StringIO(file.read().decode('utf-8-sig')), delimiter=',')
            number_column = form.cleaned_data.get('number_column')
            name_column = form.cleaned_data.get('name_column')
            min_students_column = form.cleaned_data.get('min_students_column')
            max_students_column = form.cleaned_data.get('max_students_column')
            description_column = form.cleaned_data.get('description_column')

            project_list = []
            for row in csv_data:
                project = models.Project()
                project.number = row[number_column]
                project.name = row[name_column]
                project.min_students = row[min_students_column]
                project.max_students = row[max_students_column]
                if description_column != '':
                    project.description = row[description_column]
                project.unit_id = self.kwargs['pk_unit']
                project_list.append(project)

            models.Project.objects.bulk_create(
                project_list,
                update_conflicts=True,
                update_fields=['number', 'name'],
            )

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitProjectsUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = forms.ProjectForm
    model = models.Project
    template_name = 'manager/projects/unit_projects_detail.html'

    def get_success_url(self):
        return reverse('manager-unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitProjectDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
        Remove a single project from a unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_project_confirm_delete.html'

    def get_success_url(self):
        return reverse('manager-unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


class UnitProjectsClearView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Clear the project list of a unit
    """
    template_name = 'manager/projects/unit_projects_confirm_delete.html'
    form_class = forms.StudentListClearForm

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            models.Project.objects.filter(
                unit_id=self.kwargs['pk_unit']).delete()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('manager-unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **get_context_for_sidebar(self.kwargs['pk_unit'])}

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])


# Unit Preference Views


class UnitPreferencesListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
        List of preferences for projects in unit
    """
    model = models.ProjectPreference
    template_name = 'manager/preferences/unit_preferences.html'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context_data = get_context_for_sidebar(self.kwargs['pk_unit'])
        return {**super().get_context_data(**kwargs), **context_data, 'unit': context_data['unit_queryset'].annotate(
            submitted_prefs_students_count=Count('student_project_preferences__student', distinct=True)).first()}

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).prefetch_related(Prefetch('student__enrollments', queryset=models.EnrolledStudent.objects.filter(unit_id=self.kwargs['pk_unit'])))

    def test_func(self):
        return user_is_manager(self.request.user) and user_manages_unit_pk(self.request.user, self.kwargs['pk_unit'])
