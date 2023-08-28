import csv
from io import StringIO

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count, Sum, F, Avg, Min, Max, Exists, OuterRef
from django.db.models.functions import Round
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormMixin

from django_filters.views import FilterView, FilterMixin
from django_tables2 import SingleTableMixin, MultiTableMixin

from core import models
from . import filters
from . import forms
from . import tables
from . import tasks


class FilteredTableBase(SingleTableMixin):
    filter_formhelper_class = None

    def get_filter_formhelper_class(self):
        if self.filter_formhelper_class:
            return self.filter_formhelper_class

    def get_filterset(self, filterset_class):
        kwargs = self.get_filterset_kwargs(filterset_class)
        filterset = filterset_class(**kwargs)
        filterset.form.helper = self.get_filter_formhelper_class()()
        return filterset

    def get_context_data(self, **kwargs):
        f = self.get_filterset(self.get_filterset_class())
        self.table_data = f.qs
        return {**super().get_context_data(**kwargs), 'filter': f, 'has_filter': any(
            field in self.request.GET for field in set(f.get_fields()))}


class FilteredTableMixin(FilteredTableBase, FilterMixin):
    pass


class FilteredTableView(FilteredTableBase, FilterView):
    pass


def user_is_manager(user):
    return user.is_manager


class UnitMixin(LoginRequiredMixin, UserPassesTestMixin):
    unit_id_arg = 'pk_unit'
    template_name = 'manager/base.html'

    def get_unit_queryset(self):
        unit_pk = self.kwargs[self.unit_id_arg]
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = models.Unit.objects.filter(pk=unit_pk).annotate(students_count=Count(
                'students', distinct=True)).annotate(projects_count=Count('projects', distinct=True)).annotate(
                preference_count=Count('students__project_preferences'))
        return self.unit_queryset

    def get_unit_object(self):
        if not hasattr(self, 'unit'):
            self.unit = self.get_unit_queryset().first()
        return self.unit

    def get_context_for_sidebar(self):
        link_classes = 'link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover'
        unit = self.get_unit_object()
        nav_items = [
            {'url': 'manager:unit', 'label': unit,
                'classes': f'fs-6 {link_classes}'},
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
            {'url': 'manager:unit-preferences', 'label': 'Submitted Preferences',
                'classes': 'ms-3', 'disabled': not unit.preference_count},
            {'url': 'manager:unit-preferences-distribution',
             'label': 'Preference Distribution', 'classes': 'ms-3', 'disabled': not unit.preference_count},
            {'url': 'manager:unit-allocation-results', 'label': 'Allocation Results',
                'classes': 'ms-3', 'disabled': not unit.successfully_allocated()},
        ]
        return {'unit': unit, 'nav_items': nav_items}

    def get_page_title(self):
        if hasattr(self, 'page_title'):
            return self.page_title
        return self.get_unit_object()

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **
                self.get_context_for_sidebar(), 'page_title': self.get_page_title()}

    def unit_managed_by_user(self):
        unit = self.get_unit_object()
        return unit.manager_id == self.request.user.id

    def test_func(self):
        return user_is_manager(self.request.user) and self.unit_managed_by_user()

    def get_object(self, queryset=None):
        if not hasattr(self, 'object'):
            self.object = super().get_object(queryset)
        return self.object


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.Unit
    template_name = 'core/index.html'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.managed_units.all().order_by('-is_active')

    def test_func(self):
        return user_is_manager(self.request.user)


"""

Unit views

"""


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


class UnitDeleteView(UnitMixin, DeleteView):
    model = models.Unit
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_confirm_delete.html'

    unit_id_arg = 'pk'

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            self.page_title = f'Delete {self.get_unit_object()}?'
        return self.page_title


class UnitView(UnitMixin, UpdateView):
    model = models.Unit
    form_class = forms.UnitUpdateForm

    unit_id_arg = 'pk'

    def get_success_url(self):
        return self.request.path


"""

    Student views
    
"""


class UnitStudentsListView(UnitMixin, FilteredTableView):
    """
        List of students in unit
    """
    model = models.Student
    template_name = 'manager/students/unit_students.html'
    page_title = 'Student List'

    def get_filter_formhelper_class(self):
        return filters.StudentAllocatedFilterFormHelper if self.get_unit_object().successfully_allocated() else filters.StudentFilterFormHelper

    def get_filterset_class(self):
        return filters.StudentAllocatedFilter if self.get_unit_object().successfully_allocated() else filters.StudentFilter

    def get_table_class(self):
        return tables.StudentAllocatedTable if self.get_unit_object().successfully_allocated() else tables.StudentTable

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).select_related('user').prefetch_related('project_preferences').select_related('allocated_project')

    def get_context_data(self, **kwargs):
        allocated_student_count = self.get_unit_object().students.filter(
            allocated_project__isnull=False).count()
        return {**super().get_context_data(**kwargs), 'allocated_student_count': allocated_student_count, 'unallocated_student_count': self.get_unit_object().students.count()-allocated_student_count}


class UnitStudentCreateView(UnitMixin, FormMixin, TemplateView):
    """
        Add a single student to the unit's student list
    """
    form_class = forms.StudentForm
    page_title = 'Add Student'

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


class UnitStudentsUploadListView(UnitMixin, FormMixin, TemplateView):
    """
        Upload list of students to a unit
    """
    form_class = forms.StudentListForm
    page_title = 'Upload Student List'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request, *args, **kwargs):
        # form = self.get_form()
        form = forms.StudentListForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('list_override'):
                # Clear previous enrolled students
                models.Student.objects.filter(
                    unit_id=self.kwargs['pk_unit']).delete()

            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            csv_data = csv.DictReader(
                StringIO(file.read().decode('utf-8-sig')), delimiter=',')
            student_id_column = form.cleaned_data.get('student_id_column')

            students = []
            for row in csv_data:
                enrolled_student = models.Student()
                enrolled_student.student_id = row[student_id_column]
                enrolled_student.unit_id = self.kwargs['pk_unit']
                # Check if user account exists for student
                user = models.User.objects.filter(
                    username=row[student_id_column])
                if user.exists():
                    enrolled_student.user_id = user.first().id
                students.append(enrolled_student)

            models.Student.objects.bulk_create(
                students,
                update_conflicts=True,
                update_fields=['student_id', 'unit_id'],
            )

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitStudentDetailView(UnitMixin, SingleTableMixin, UpdateView):
    """
        View/update a single student in a unit
    """
    model = models.Student
    template_name = 'manager/students/unit_student_detail.html'

    table_class = tables.StudentPreferencesTable

    form_class = forms.StudentUpdateForm

    def get_object(self, queryset=None):
        if not hasattr(self, 'object'):
            self.object = super().get_object(queryset)
            self.object.is_registered = self.object.user != None
        return super().get_object(queryset)

    def get_queryset(self):
        return super().get_queryset().select_related('user').prefetch_related('project_preferences').annotate(project_preferences_count=Count('project_preferences', distinct=True))

    def get_table_data(self):
        return self.get_object().project_preferences.prefetch_related('project').all()

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            self.page_title = f'Student: {self.get_object().student_id }'
        return super().get_page_title()

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def get_success_url(self):
        return self.request.path


class UnitStudentDeleteView(UnitMixin, DeleteView):
    """
        Remove a single student from a unit
    """
    model = models.Student
    form_class = forms.StudentDeleteForm

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            self.page_title = f'Remove Student "{self.get_object().student_id }" from Unit?'
        return super().get_page_title()

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})


class UnitStudentsClearView(UnitMixin, FormMixin, TemplateView):
    """
        Clear the student list of a unit
    """
    model = models.Student
    form_class = forms.StudentListClearForm

    page_title = 'Clear Student List for Unit?'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            models.Student.objects.filter(
                unit_id=self.kwargs['pk_unit']).delete()

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})


"""

Project views

"""


class UnitProjectsListView(UnitMixin, FilteredTableView):
    """
        List of projects in unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_projects.html'

    page_title = 'Project List'

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'allocated_projects_count': self.get_queryset().filter(allocated_students_count__gt=0).count()}

    def get_filter_formhelper_class(self):
        return filters.ProjectAllocatedFilterFormHelper if self.get_unit_object().successfully_allocated() else filters.ProjectFilterFormHelper

    def get_filterset_class(self):
        return filters.ProjectAllocatedFilter if self.get_unit_object().successfully_allocated() else filters.ProjectFilter

    def get_table_class(self):
        return tables.ProjectAllocatedTable if self.get_unit_object().successfully_allocated() else tables.ProjectTable

    def get_queryset(self):
        return super().get_queryset().prefetch_related('unit').filter(unit=self.kwargs['pk_unit']).prefetch_related('allocated_students').annotate(allocated_students_count=Count('allocated_students', distinct=True)).annotate(avg_allocated_pref=Avg('allocated_students__allocated_preference_rank'))


class UnitProjectCreateView(UnitMixin, FormMixin, TemplateView):
    form_class = forms.ProjectForm
    page_title = 'Add Project'

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


class UnitProjectsUploadListView(UnitMixin, FormMixin, TemplateView):
    """
        Upload list of projects
    """
    form_class = forms.ProjectListForm
    page_title = 'Upload Project List'

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


class UnitProjectDetailView(UnitMixin, MultiTableMixin, DetailView):
    """
        View a project in a unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_project_detail.html'

    tables = [
        tables.ProjectPreferencesTable,
    ]

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            project = self.get_object()
            self.page_title = f'Project: {project.number} - {project.name}?'
        return self.page_title

    def get_tables(self):
        project_tables = []
        project = self.get_object()

        preference_counts = project.get_preference_counts()
        if preference_counts.exists():
            preference_table = tables.ProjectPreferencesTable(
                data=project.get_preference_counts())
            preference_table.name = 'Preference Distribution'
            preference_table.id = 'preferences'
            project_tables.append(preference_table)

        if project.allocated_students.exists():
            allocated_students_table = tables.AllocatedStudentsTable(
                data=project.allocated_students.all())
            allocated_students_table.name = 'Allocated Students'
            allocated_students_table.id = 'allocated'
            project_tables.append(allocated_students_table)

        return project_tables

    def get_queryset(self):
        return super().get_queryset().prefetch_related('allocated_students').annotate(avg_allocated_pref=Avg('allocated_students__allocated_preference_rank'))


class UnitProjectUpdateView(UnitMixin, UpdateView):
    """
        Update a project in a unit
    """
    model = models.Project

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            project = self.get_object()
            self.page_title = f'Update Project: {project.number} - {project.name}?'
        return self.page_title

    def get_form_class(self):
        return forms.ProjectAllocatedUpdateForm if self.get_unit_object().successfully_allocated() else forms.ProjectUpdateForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def get_success_url(self):
        return reverse('manager:unit-project-detail', kwargs={'pk': self.kwargs['pk'], 'pk_unit': self.kwargs['pk_unit']})


class UnitProjectDeleteView(UnitMixin, DeleteView):
    """
        Remove a single project from a unit
    """
    model = models.Project
    form_class = forms.ProjectDeleteForm

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            project = self.get_object()
            self.page_title = f'Remove Project "{project.number} - {project.name}" from Unit?'
        return self.page_title

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


class UnitProjectsClearView(UnitMixin, FormMixin, TemplateView):
    """
        Clear the project list of a unit
    """
    form_class = forms.ProjectListClearForm

    page_title = 'Clear Project List for Unit?'

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


"""

Preference Views

"""


class UnitPreferencesView(UnitMixin, FilteredTableView):
    """
        Show a list of all submitted preferences by students for projects in a unit
    """
    model = models.ProjectPreference
    template_name = 'manager/preferences/unit_preferences.html'
    page_title = 'Submitted Preferences'

    table_class = tables.PreferencesTable
    filterset_class = filters.PreferenceFilter
    filter_formhelper_class = filters.PreferenceFilterFormHelper

    def get_context_data(self, **kwargs):
        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        not_submitted_prefs_count = students_list.count() - \
            submitted_prefs_count
        return {**super().get_context_data(**kwargs), 'submitted_prefs_count': submitted_prefs_count, 'not_submitted_prefs_count': not_submitted_prefs_count, 'submitted_prefs_perc': round((submitted_prefs_count/students_count)*100, 1)}

    def get_queryset(self):
        return super().get_queryset().filter(project__unit_id=self.kwargs['pk_unit']).prefetch_related('project').prefetch_related('student')

    def post(self, request, *args, **kwargs):
        email_results = 'email_results' in request.POST
        from . import export
        if email_results:
            export.email_preferences_csv(
                unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id)
            return HttpResponseRedirect(self.request.path)
        return export.download_preferences_csv(unit_id=self.kwargs['pk_unit'])


class UnitPreferencesDistributionView(UnitMixin, FilteredTableView):
    """
        Show the distribution of preferences for projects in unit
    """
    model = models.Project
    template_name = 'manager/preferences/unit_preferences_distribution.html'
    page_title = 'Preference Distribution'

    table_class = tables.PreferencesDistributionTable
    filterset_class = filters.PreferenceDistributionFilter
    filter_formhelper_class = filters.PreferenceDistributionFilterFormHelper

    def get_context_data(self, **kwargs):
        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        not_submitted_prefs_count = students_list.count() - \
            submitted_prefs_count
        return {**super().get_context_data(**kwargs), 'submitted_prefs_count': submitted_prefs_count, 'not_submitted_prefs_count': not_submitted_prefs_count, 'submitted_prefs_perc': round((submitted_prefs_count/students_count)*100, 1)}

    def get_queryset(self):
        total_projects = models.Project.objects.filter(
            unit_id=self.kwargs['pk_unit']).count()

        project_queryset = super().get_queryset().filter(unit_id=self.kwargs['pk_unit']).prefetch_related(
            'student_preferences').annotate(popularity=Sum(total_projects - F('student_preferences__rank'))).order_by('number', 'name')
        for project in project_queryset:
            project.popularity = project.popularity if project.popularity else 0

        return project_queryset


"""

Allocation Views

"""


class UnitAllocationStartView(UnitMixin, FormMixin, TemplateView):
    """
        View for starting/viewing allocation
    """
    form_class = forms.StartAllocationForm
    template_name = 'manager/allocation/unit_allocation_start.html'

    page_title = 'Start Allocation'

    def get_unit_queryset(self):
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = super().get_unit_queryset()
        return self.unit_queryset

    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            unit = self.get_unit_object()
            unit.is_allocating = True
            unit.save()

            tasks.start_allocation.delay(
                unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id, results_url=request.build_absolute_uri(reverse('manager:unit-allocation-results', kwargs={'pk_unit': self.kwargs['pk_unit']})))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()

        # Calculate number of students who have submitted preferences
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        not_submitted_prefs_count = students_count - submitted_prefs_count

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
            project_spaces = {'too_few_students': min(min_spaces) > students_count, 'min_project_space': min(min_spaces),
                              'too_many_students': sum(max_spaces) < students_count, 'max_project_spaces': sum(max_spaces)}

        return {**context, 'submitted_prefs_count': submitted_prefs_count, 'not_submitted_prefs_count': not_submitted_prefs_count, 'submitted_prefs_perc': round((submitted_prefs_count/students_count)*100, 1), **project_spaces}


class UnitAllocationResultsView(UnitMixin, TemplateView):
    """
        View allocation results & stats
    """
    template_name = 'manager/allocation/unit_allocation_results.html'

    page_title = 'Allocation Results'

    def post(self, request, *args, **kwargs):
        email_results = 'email_results' in request.POST
        from . import export
        if email_results:
            export.email_allocation_results_csv(
                unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id)
            return HttpResponseRedirect(self.request.path)
        return export.download_allocation_results_csv(unit_id=self.kwargs['pk_unit'])

    def get_unit_queryset(self):
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = super().get_unit_queryset().prefetch_related('projects').prefetch_related('students').annotate(
                avg_allocated_pref_rounded=Round(Avg('students__allocated_preference_rank'), 2)).annotate(
                max_allocated_pref=Max('students__allocated_preference_rank')).annotate(
                min_allocated_pref=Min('students__allocated_preference_rank'))
        return self.unit_queryset

    def test_func(self):
        return super().test_func() and self.get_unit_object().successfully_allocated()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        not_submitted_prefs_count = students_list.count() - submitted_prefs_count

        allocated_student_count = self.get_unit_object().students.filter(
            allocated_project__isnull=False).count()

        return {**context, 'submitted_prefs_count': submitted_prefs_count, 'not_submitted_prefs_count': not_submitted_prefs_count, 'submitted_prefs_perc': round((submitted_prefs_count/students_count)*100, 1), 'allocated_student_count': allocated_student_count, 'unallocated_student_count': self.get_unit_object().students.count()-allocated_student_count}
