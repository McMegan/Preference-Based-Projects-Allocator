import csv
from io import StringIO
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count, Sum, F, Avg, Min, Max
from django.db.models.functions import Round
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormMixin


from django_filters.views import FilterView, FilterMixin
from django_tables2 import SingleTableMixin, MultiTableMixin


from core import models
from . import filters
from . import forms
from . import tables


class FilteredTableMixin(SingleTableMixin, FilterMixin):
    formhelper_class = None

    def get_formhelper_class(self):
        if self.formhelper_class:
            return self.formhelper_class

    def get_filterset(self, filterset_class):
        kwargs = self.get_filterset_kwargs(filterset_class)
        filterset = filterset_class(**kwargs)
        filterset.form.helper = self.get_formhelper_class()()
        return filterset

    def get_context_data(self, **kwargs):
        f = self.get_filterset(self.get_filterset_class())
        self.table_data = f.qs
        return {**super().get_context_data(**kwargs), 'filter': f, 'has_filter': any(
            field in self.request.GET for field in set(f.get_fields()))}


class FilteredTableView(SingleTableMixin, FilterView):
    formhelper_class = None

    def get_formhelper_class(self):
        if self.formhelper_class:
            return self.formhelper_class

    def get_filterset(self, filterset_class):
        kwargs = self.get_filterset_kwargs(filterset_class)
        filterset = filterset_class(**kwargs)
        filterset.form.helper = self.get_formhelper_class()()
        return filterset

    def get_context_data(self, **kwargs):
        f = self.get_filterset(self.get_filterset_class())
        self.table_data = f.qs
        return {**super().get_context_data(**kwargs), 'filter': f, 'has_filter': any(
            field in self.request.GET for field in set(f.get_fields()))}


def user_is_manager(user):
    return user.is_manager


class UnitMixin:
    unit_id_arg = 'pk_unit'

    def get_unit_queryset(self):
        unit_pk = self.kwargs[self.unit_id_arg]
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = models.Unit.objects.filter(pk=unit_pk).annotate(students_count=Count(
                'enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))
        return models.Unit.objects.filter(pk=unit_pk).annotate(students_count=Count(
            'enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))

    def get_unit_object(self):
        if not hasattr(self, 'unit'):
            self.unit = self.get_unit_queryset().first()
        return self.unit

    def get_context_for_sidebar(self):
        unit = self.get_unit_object()
        nav_items = [
            {'url': 'manager:unit', 'label': unit, 'classes': 'fs-6'},
            # Allocator Settings / Setup
            {'label': 'Unit Actions', 'classes': 'fw-semibold'},
            {'url': 'manager:unit-students-new-list',
                'label': 'Upload Student List', 'classes': 'ms-3'},
            {'url': 'manager:unit-students-new',
                'label': 'Add Student', 'classes': 'ms-3'},
            {'url': 'manager:unit-projects-new-list',
                'label': 'Upload Project List', 'classes': 'ms-3'},
            {'url': 'manager:unit-projects-new',
                'label': 'Add Project', 'classes': 'ms-3'},
            {'url': 'manager:unit-allocation-start',
                'label': 'Start Allocation', 'classes': 'ms-3'},
            # Unit Information
            {'label': 'Unit Information', 'classes': 'fw-semibold'},
            {'url': 'manager:unit-students',
                'label': f'Student List ({unit.students_count})', 'classes': 'ms-3'},
            {'url': 'manager:unit-projects',
                'label': f'Project List ({unit.projects_count})', 'classes': 'ms-3'},
            {'url': 'manager:unit-preferences',
                'label': 'Preference Distribution', 'classes': 'ms-3'},

        ]
        if unit.is_allocated():
            nav_items.append({'url': 'manager:unit-allocation-results',
                              'url': 'manager:unit-allocation-results', 'label': 'Allocation Results', 'classes': 'ms-3'})
        return {'unit': unit, 'nav_items': nav_items}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **self.get_context_for_sidebar()}

    def unit_managed_by_user(self):
        unit = self.get_unit_object()
        return unit.manager.id == self.request.user.id

    def test_func(self):
        return user_is_manager(self.request.user) and self.unit_managed_by_user()


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.Unit
    template_name = 'core/index.html'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.managed_units.all().order_by('-is_active')

    def test_func(self):
        return user_is_manager(self.request.user)

# Unit Views


class UnitCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = forms.CreateUnitForm
    template_name = 'manager/unit_new.html'
    success_url = reverse_lazy('manager:index')

    def post(self, request, *args, **kwargs):
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


class UnitDeleteView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = models.Unit
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_confirm_delete.html'

    unit_id_arg = 'pk'


class UnitView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Unit
    form_class = forms.UpdateUnitForm
    template_name = 'manager/unit.html'

    unit_id_arg = 'pk'

    def get_success_url(self):
        return self.request.path


# Unit student views


class UnitStudentsListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FilteredTableView):
    """
        List of students in unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_students.html'

    def get_formhelper_class(self):
        return filters.StudentAllocatedFilterFormHelper if self.get_unit_object().is_allocated() else filters.StudentFilterFormHelper

    def get_filterset_class(self):
        return filters.StudentAllocatedFilter if self.get_unit_object().is_allocated() else filters.StudentFilter

    def get_table_class(self):
        return tables.StudentAllocatedTable if self.get_unit_object().is_allocated() else tables.StudentTable

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).select_related('user').prefetch_related('project_preferences').select_related('assigned_project')


class UnitStudentCreateView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Add a single student to the unit's student list
    """
    form_class = forms.StudentForm
    template_name = 'manager/students/unit_students_new.html'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'pk_unit': self.kwargs['pk_unit']}

    def post(self, request, *args, **kwargs):
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


class UnitStudentsUploadListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Upload list of students to a unit
    """
    form_class = forms.StudentListForm
    template_name = 'manager/students/unit_students_new_list.html'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request, *args, **kwargs):
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


class UnitStudentDetailView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, SingleTableMixin, ListView):
    """
        View a single student in a unit
    """
    model = models.ProjectPreference
    template_name = 'manager/students/unit_student_detail.html'

    table_class = tables.StudentPreferencesTable

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'student': models.EnrolledStudent.objects.filter(pk=self.kwargs['pk']).prefetch_related('user').first()}

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().filter(student=self.kwargs['pk']).prefetch_related('project')


class UnitStudentDeleteView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
        Remove a single student from a unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_student_confirm_delete.html'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})


class UnitStudentsClearView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
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
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

# Unit project views


class UnitProjectsListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FilteredTableView):
    """
        List of projects in unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_projects.html'

    def get_formhelper_class(self):
        return filters.ProjectAllocatedFilterFormHelper if self.get_unit_object().is_allocated() else filters.ProjectFilterFormHelper

    def get_filterset_class(self):
        return filters.ProjectAllocatedFilter if self.get_unit_object().is_allocated() else filters.ProjectFilter

    def get_table_class(self):
        return tables.ProjectAllocatedTable if self.get_unit_object().is_allocated() else tables.ProjectTable

    def get_queryset(self):
        return super().get_queryset().prefetch_related('unit').filter(unit=self.kwargs['pk_unit']).prefetch_related('assigned_students')


class UnitProjectCreateView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    form_class = forms.ProjectForm
    template_name = 'manager/projects/unit_projects_new.html'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'pk_unit': self.kwargs['pk_unit']}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitProjectsUploadListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Upload list of projects
    """
    form_class = forms.ProjectListForm
    template_name = 'manager/projects/unit_projects_new_list.html'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request, *args, **kwargs):
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


class UnitProjectDetailView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, MultiTableMixin, DetailView):
    """
        View a project in a unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_project_detail.html'

    tables = [
        tables.ProjectPreferencesTable,
    ]

    def get_tables(self):
        project_tables = []
        project = self.get_object()

        preference_table = tables.ProjectPreferencesTable(
            data=project.get_preference_counts())
        preference_table.name = 'Preference Distribution'
        preference_table.id = 'preferences'
        project_tables.append(preference_table)

        if project.assigned_students:
            allocated_students_table = tables.AllocatedStudentsTable(
                data=project.assigned_students.all())
            allocated_students_table.name = 'Allocated Students'
            allocated_students_table.id = 'allocated'
            project_tables.append(allocated_students_table)

        return project_tables

    def get_queryset(self):
        return super().get_queryset().prefetch_related('assigned_students')


class UnitProjectUpdateView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
        Update a project in a unit
    """
    form_class = forms.ProjectUpdateForm
    model = models.Project
    template_name = 'manager/projects/unit_project_update.html'

    def get_success_url(self):
        return reverse('manager:unit-project-detail', kwargs={'pk': self.kwargs['pk'], 'pk_unit': self.kwargs['pk_unit']})


class UnitProjectDeleteView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
        Remove a single project from a unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_project_confirm_delete.html'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


class UnitProjectsClearView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
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
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


# Unit Preference Views

class UnitPreferencesView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FilteredTableView):
    """
        Show the distribution of preferences for projects in unit
    """
    model = models.Project
    template_name = 'manager/preferences/unit_preferences.html'

    table_class = tables.PreferencesTable
    filterset_class = filters.PreferenceFilter
    formhelper_class = filters.PreferenceFilterFormHelper

    def get_context_data(self, **kwargs):
        enrolled_students_list = models.EnrolledStudent.objects.filter(
            unit=self.kwargs['pk_unit'])
        submitted_prefs_count = enrolled_students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        not_submitted_prefs_count = enrolled_students_list.count() - \
            submitted_prefs_count
        return {**super().get_context_data(**kwargs), 'submitted_prefs_count': submitted_prefs_count, 'not_submitted_prefs_count': not_submitted_prefs_count}

    def get_queryset(self):
        total_projects = models.Project.objects.filter(
            unit_id=self.kwargs['pk_unit']).count()

        project_queryset = super().get_queryset().filter(unit_id=self.kwargs['pk_unit']).prefetch_related(
            'student_preferences').annotate(popularity=Sum(total_projects - F('student_preferences__rank'))).order_by('number', 'name')
        for project in project_queryset:
            project.popularity = project.popularity if project.popularity else 0

        return project_queryset


# Unit Allocation Views


class UnitAllocationStartView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        View for starting/viewing allocation
    """
    form_class = forms.StartAllocationForm
    template_name = 'manager/allocation/unit_allocation_start.html'

    def get_unit_queryset(self):
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = super().get_unit_queryset().prefetch_related('projects').annotate(
                avg_allocated_pref_rounded=Round(Avg('projects__avg_allocated_pref'), 2))
        return self.unit_queryset

    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            unit = self.get_unit_object()
            unit.allocation_status = models.Unit.ALLOCATING
            unit.save()

            from .tasks import start_allocation
            start_allocation.delay(
                unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id, results_url=request.build_absolute_uri(reverse('manager:unit-allocation-results', kwargs={'pk_unit': self.kwargs['pk_unit']})))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        enrolled_students_list = models.EnrolledStudent.objects.filter(
            unit=self.kwargs['pk_unit'])
        enrolled_students_count = enrolled_students_list.count()

        # Calculate number of students who have submitted preferences
        submitted_prefs_count = enrolled_students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        not_submitted_prefs_count = enrolled_students_count - submitted_prefs_count

        # Calculate min & max number of project spaces
        project_spaces = {}
        projects_list = models.Project.objects.filter(
            unit=self.kwargs['pk_unit'])
        if projects_list.exists():
            min_spaces = []
            max_spaces = []
            for project in projects_list.all():
                min_spaces.append(project.min_students)
                max_spaces.append(project.max_students)
            project_spaces = {'too_few_students': min(min_spaces) > enrolled_students_count, 'min_project_space': min(min_spaces),
                              'too_many_students': sum(max_spaces) < enrolled_students_count, 'max_project_spaces': sum(max_spaces)}

        return {**context, 'submitted_prefs_count': submitted_prefs_count, 'not_submitted_prefs_count': not_submitted_prefs_count, **project_spaces}


class UnitAllocationResultsView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        View allocation results & stats
    """
    template_name = 'manager/allocation/unit_allocation_results.html'
    form_class = forms.ExportAllocationForm

    def get_success_url(self):
        return self.request.path

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        return self.make_allocation_results_csv()

    def get_unit_queryset(self):
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = super().get_unit_queryset().prefetch_related('projects').prefetch_related('enrolled_students').annotate(
                avg_allocated_pref_rounded=Round(Avg('projects__avg_allocated_pref'), 2)).annotate(
                max_allocated_pref=Max('enrolled_students__assigned_preference_rank')).annotate(
                min_allocated_pref=Min('enrolled_students__assigned_preference_rank'))
        return self.unit_queryset

    def test_func(self):
        return super().test_func() and self.get_unit_object().is_allocated()

    def get_context_data(self, **kwargs):
        enrolled_students_list = models.EnrolledStudent.objects.filter(
            unit=self.kwargs['pk_unit'])
        submitted_prefs_count = enrolled_students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        not_submitted_prefs_count = enrolled_students_list.count() - \
            submitted_prefs_count

        return {**super().get_context_data(**kwargs), 'submitted_prefs_count': submitted_prefs_count, 'not_submitted_prefs_count': not_submitted_prefs_count}

    def make_allocation_results_csv(self):
        unit = self.get_unit_object()

        response = HttpResponse(
            content_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{unit.code}-project-allocation.csv"'},
        )

        # Write to file
        writer = csv.writer(response)
        # Add headers to file
        writer.writerow(['student_id', 'project_number', 'project_name'])
        # Write students to file
        for student in unit.enrolled_students.all():
            writer.writerow(
                [student.student_id, student.assigned_project.number, student.assigned_project.name])

        return response
