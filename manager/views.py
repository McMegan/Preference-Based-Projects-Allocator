import csv
from io import StringIO
from typing import Any, Dict, Optional, Type

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count, Sum, F, Avg, Min, Max
from django.db.models.functions import Round
from django.forms.models import BaseModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormMixin

from django_filters.views import FilterView, FilterMixin
from django_tables2 import SingleTableMixin, MultiTableMixin

from core import models
from . import filters
from . import forms
from . import tables
from . import tasks


def render_exists_badge(value: bool):
    return format_html(f"""<span class ="badge rounded-pill text-bg-{'success' if value else 'danger'}"><i class="bi bi-{'check' if value else 'x'}-lg"></i></span>""")


def render_area_list(areas):
    areas_html = ''
    first = True
    for area in areas.all():
        areas_html = areas_html + ('; ' if not first else '') + \
            f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-area-detail',kwargs={'pk_unit':area.unit_id,'pk':area.id})}">{area.name}</a>"""
        if first:
            first = False
    return format_html(f"""{areas_html}""")


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
                preference_count=Count('students__project_preferences')).annotate(
                areas_count=Count('areas', distinct=True))
        return self.unit_queryset

    def get_unit_object(self):
        if not hasattr(self, 'unit'):
            self.unit = self.get_unit_queryset().first()
        return self.unit

    def get_context_for_sidebar(self):
        unit = self.get_unit_object()
        nav_items = [
            {'url': 'manager:unit', 'label': unit,
                'classes': f'fs-6'},
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
            {'url': 'manager:unit-area-new',
                'label': 'Add Area', 'classes': 'ms-3'},
            {'url': 'manager:unit-allocation-start',
                'label': 'Start Allocation', 'classes': 'ms-3'},
            # Unit Information
            {'label': 'Unit Information', 'classes': 'fw-semibold'},
            {'url': 'manager:unit-students',
                'label': f'Student List ({unit.students_count})', 'classes': 'ms-3'},
            {'url': 'manager:unit-projects',
                'label': f'Project List ({unit.projects_count})', 'classes': 'ms-3'},
            {'url': 'manager:unit-areas',
                'label': f'Area List ({unit.areas_count})', 'classes': 'ms-3'},
            {'url': 'manager:unit-preferences', 'label': 'Submitted Preferences',
                'classes': 'ms-3', 'disabled': not unit.preference_count},
            {'url': 'manager:unit-preferences-distribution',
             'label': 'Preference Distribution', 'classes': 'ms-3', 'disabled': not unit.preference_count},
            {'url': 'manager:unit-allocation-results', 'label': 'Allocation Results',
                'classes': 'ms-3', 'disabled': not unit.successfully_allocated()},
        ]
        return {'nav_items': nav_items}

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            self.page_title = self.get_unit_object()
        return self.page_title

    def get_page_title_url(self):
        return self.request.path

    def get_page_title_actions(self):
        if not hasattr(self, 'page_title_actions'):
            return None
        return self.page_title_actions

    def get_page_info(self):
        if not hasattr(self, 'page_info'):
            return None
        return self.page_info

    def get_page_warnings(self):
        if not hasattr(self, 'page_warnings'):
            return None
        return self.page_warnings

    def get_page_actions(self):
        if not hasattr(self, 'page_actions'):
            return None
        return self.page_actions

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **
                self.get_context_for_sidebar(), 'unit': self.get_unit_object(), 'page_title': self.get_page_title(), 'page_title_url': self.get_page_title_url(), 'page_title_actions': self.get_page_title_actions(), 'page_info': self.get_page_info(), 'page_warnings': self.get_page_warnings(), 'page_actions': self.get_page_actions()}

    def unit_managed_by_user(self):
        unit = self.get_unit_object()
        return unit.manager_id == self.request.user.id

    def test_func(self):
        return user_is_manager(self.request.user) and self.unit_managed_by_user()

    def get_object(self, queryset=None):
        if not hasattr(self, 'object'):
            self.object = super().get_object(queryset)
        return self.object


"""

Index view

"""


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


class StudentsListView(UnitMixin, FilteredTableView):
    """
        List of students in unit
    """
    model = models.Student
    page_title = 'Student List'

    page_actions = [
        {'url': 'manager:unit-students-new-list', 'label': 'Upload Student List'},
        {'url': 'manager:unit-students-new', 'label': 'Add Student'},
        {'url': 'manager:unit-students-clear',
            'label': 'Remove All Students', 'classes': 'btn-danger'},
    ]

    def get_page_info(self):
        unit = self.get_unit_object()
        allocated_info = []
        if unit.is_allocated():
            allocated_info = [
                {'label': 'No. Allocated Students',
                    'content': unit.get_allocated_student_count()},
                {'label': 'No. Unallocated Students',
                    'content': unit.students.count() - unit.get_allocated_student_count()},
            ]
        return [
            {'label': 'Total No. Students', 'content': unit.students_count},
        ] + allocated_info

    def get_page_warnings(self):
        unit = self.get_unit_object()
        warnings = []
        if unit.completed_allocation() and unit.get_unallocated_student_count() > 0:
            warnings.append({'type': 'warning', 'content': format_html(f"""
            <p>There {'are' if unit.get_unallocated_student_count() > 1 else 'is'} {unit.get_unallocated_student_count()} student{'s' if unit.get_unallocated_student_count() > 1 else ''} who {'are' if unit.get_unallocated_student_count() > 1 else 'is'} not allocated to a project.</p>
            <p class="mb-0">To fix this:</p>
            <ul class="my-0">
                <li>run the allocator again (this may change the project allocation if existing students), or</li>
                <li>manually add the unallocated student{'s' if unit.get_unallocated_student_count() > 1 else ''} to a project.</li>
            </ul>
        """)})
        return warnings if warnings != [] else None

    def get_filter_formhelper_class(self):
        return filters.StudentAllocatedFilterFormHelper if self.get_unit_object().successfully_allocated() else filters.StudentFilterFormHelper

    def get_filterset_class(self):
        return filters.StudentAllocatedFilter if self.get_unit_object().successfully_allocated() else filters.StudentFilter

    def get_table_class(self):
        return tables.StudentsAllocatedTable if self.get_unit_object().successfully_allocated() else tables.StudentsTable

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).select_related('user').prefetch_related('project_preferences').select_related('allocated_project').prefetch_related('area')

    def get_context_data(self, **kwargs):
        allocated_student_count = self.get_unit_object().students.filter(
            allocated_project__isnull=False).count()
        return {**super().get_context_data(**kwargs), 'allocated_student_count': allocated_student_count, 'unallocated_student_count': self.get_unit_object().students.count()-allocated_student_count}


class StudentCreateView(UnitMixin, FormMixin, TemplateView):
    """
        Add a single student to the unit's student list
    """
    form_class = forms.StudentForm
    page_title = 'Add Student'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

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
            form.instance.area.set(form.cleaned_data.get('area'))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class StudentsUploadListView(UnitMixin, FormMixin, TemplateView):
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
                self.get_unit_object().students.all().delete()

            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            csv_data = csv.DictReader(
                StringIO(file.read().decode('utf-8-sig')), delimiter=',')
            student_id_column = form.cleaned_data.get('student_id_column')
            area_column = form.cleaned_data.get('area_column')

            student_create_list = []
            area_create_list = []
            student_areas_list = []
            for row in csv_data:
                student = models.Student()
                student.student_id = row[student_id_column]
                student.unit_id = self.kwargs['pk_unit']
                # Check if user account exists for student
                user = models.User.objects.filter(
                    username=row[student_id_column])
                if user.exists():
                    student.user_id = user.first().id
                if area_column != '' and row[area_column] != '' and row[area_column] != None:
                    areas = row[area_column].split(';')
                    for area in areas:
                        area = area.strip()
                        area = models.Area(
                            name=area, unit=self.get_unit_object())
                        area_create_list.append(area)
                        student_areas_list.append((student, area))
                student_create_list.append(student)

            models.Student.objects.bulk_create(
                student_create_list,
                unique_fields=['student_id', 'unit_id'],
                update_conflicts=True,
                update_fields=['user']
            )
            models.Area.objects.bulk_create(
                area_create_list, ignore_conflicts=True)

            # Add area
            student_areas_create = []
            student_areas_model = models.Student.area.through
            for student, area in student_areas_list:
                student = self.get_unit_object().students.filter(student_id=student.student_id)
                area = self.get_unit_object().areas.filter(name=area.name)
                if student.exists() and area.exists():
                    student = student.first()
                    area = area.first()
                    student_areas_create.append(student_areas_model(
                        student_id=student.id, area_id=area.id))

            student_areas_model.objects.bulk_create(
                student_areas_create, ignore_conflicts=True)

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class StudentsClearView(UnitMixin, FormMixin, TemplateView):
    """
        Clear the student list of a unit
    """
    model = models.Student
    form_class = forms.StudentListClearForm

    page_title = 'Remove all Students from this Unit?'

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


class StudentPageMixin(UnitMixin):
    """
    Mixin for student pages
    """
    model = models.Student

    page_title_actions = [
        {'url': 'manager:unit-student-update', 'label': 'Edit'},
        {'url': 'manager:unit-student-remove',
            'label': 'Remove', 'classes': 'btn-danger'},
    ]

    def get_page_info(self):
        student = self.get_object()
        allocated_info = []
        if self.get_unit_object().is_allocated():
            allocated_info = [
                {'label': 'Allocated Project',
                    'content': format_html(f"""
                        <a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail',kwargs={'pk_unit':student.unit_id,'pk':student.allocated_project_id})}">{student.allocated_project.number}: {student.allocated_project.name}</a>""") if student.allocated_project else 'n/a'},
                {'label': 'Area', 'content': student.allocated_preference_rank if student.allocated_preference_rank else 'n/a'},
            ]

        return [
            {'label': 'Student ID', 'content': student.student_id},
            {'label': 'Registered', 'content': render_exists_badge(
                student.get_is_registered())},
            {'label': 'Submitted Preferences', 'content': render_exists_badge(
                student.project_preferences_count)},
            {'label': 'Area', 'content': render_area_list(
                student.area) if student.area.count() else '-'},

        ] + allocated_info

    def get_queryset(self):
        return super().get_queryset().select_related('user').prefetch_related('project_preferences').annotate(project_preferences_count=Count('project_preferences', distinct=True))

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            self.page_title = f'Student: {self.get_object().student_id }'
        return super().get_page_title()

    def get_page_title_url(self):
        return reverse('manager:unit-student-detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class StudentDetailView(StudentPageMixin, SingleTableMixin, DetailView):
    """
        View a single student in a unit
    """
    table_class = tables.StudentPreferencesTable

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table'].title = 'Project Preferences'
        return context

    def get_table_data(self):
        return self.get_object().project_preferences.prefetch_related('project').all()


class StudentUpdateView(StudentPageMixin, UpdateView):
    """
        Update a single student in a unit
    """

    def get_form_class(self):
        return forms.StudentAllocatedUpdateForm if self.get_unit_object().successfully_allocated() else forms.StudentUpdateForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def get_success_url(self):
        return reverse('manager:unit-student-detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class StudentDeleteView(StudentPageMixin, DeleteView):
    """
        Remove a single student from a unit
    """
    form_class = forms.StudentDeleteForm

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})


"""

Project views

"""


class ProjectsListView(UnitMixin, FilteredTableView):
    """
        List of projects in unit
    """
    model = models.Project

    page_title = 'Project List'

    page_actions = [
        {'url': 'manager:unit-projects-new-list', 'label': 'Upload Project List'},
        {'url': 'manager:unit-projects-new', 'label': 'Add Project'},
        {'url': 'manager:unit-projects-clear',
            'label': 'Remove All Projects', 'classes': 'btn-danger'},
    ]

    def get_page_info(self):
        unit = self.get_unit_object()
        allocated_info = []
        if unit.is_allocated():
            allocated_info = [
                {'label': 'No. Allocated Projects',
                    'content': self.get_queryset().filter(allocated_students_count__gt=0).count()},
            ]
        return [
            {'label': 'No. Projects', 'content': unit.projects_count},
        ] + allocated_info

    def get_filter_formhelper_class(self):
        return filters.ProjectAllocatedFilterFormHelper if self.get_unit_object().successfully_allocated() else filters.ProjectFilterFormHelper

    def get_filterset_class(self):
        return filters.ProjectAllocatedFilter if self.get_unit_object().successfully_allocated() else filters.ProjectFilter

    def get_table_class(self):
        return tables.ProjectsAllocatedTable if self.get_unit_object().successfully_allocated() else tables.ProjectsTable

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).prefetch_related('unit').prefetch_related('area').prefetch_related('allocated_students').annotate(allocated_students_count=Count('allocated_students', distinct=True)).annotate(avg_allocated_pref=Avg('allocated_students__allocated_preference_rank'))


class ProjectCreateView(UnitMixin, FormMixin, TemplateView):
    form_class = forms.ProjectForm
    page_title = 'Add Project'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            form.instance.area.set(form.cleaned_data.get('area'))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ProjectsUploadListView(UnitMixin, FormMixin, TemplateView):
    """
        Upload list of projects
    """
    form_class = forms.ProjectListForm
    page_title = 'Upload Project List'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request, *args, **kwargs):
        form = forms.ProjectListForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('list_override'):
                # Clear previous enrolled projects
                self.get_unit_object().projects.all().delete()

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
            area_column = form.cleaned_data.get('area_column')

            project_create_list = []
            area_create_list = []
            project_areas_list = []
            for row in csv_data:
                project = models.Project()
                project.number = row[number_column]
                project.name = row[name_column]
                project.min_students = row[min_students_column]
                project.max_students = row[max_students_column]
                project.unit_id = self.kwargs['pk_unit']
                if description_column != '' and row[description_column] != '' and row[description_column] != None:
                    project.description = row[description_column]
                if area_column != '' and row[area_column] != '' and row[area_column] != None:
                    areas = row[area_column].split(';')
                    for area in areas:
                        area = area.strip()
                        area = models.Area(
                            name=area, unit=self.get_unit_object())
                        area_create_list.append(area)
                        project_areas_list.append((project, area))
                project_create_list.append(project)

            models.Project.objects.bulk_create(
                project_create_list,
                unique_fields=['number', 'unit_id'],
                update_conflicts=True,
                update_fields=['name', 'description',
                               'min_students', 'max_students'],
            )
            models.Area.objects.bulk_create(
                area_create_list, ignore_conflicts=True)

            # Add area
            project_areas_create = []
            project_areas_model = models.Project.area.through
            for project, area in project_areas_list:
                project = self.get_unit_object().projects.filter(number=project.number)
                area = self.get_unit_object().areas.filter(name=area.name)
                if project.exists() and area.exists():
                    project = project.first()
                    area = area.first()
                    project_areas_create.append(project_areas_model(
                        project_id=project.id, area_id=area.id))

            project_areas_model.objects.bulk_create(
                project_areas_create, ignore_conflicts=True)

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ProjectsClearView(UnitMixin, FormMixin, TemplateView):
    """
        Clear the project list of a unit
    """
    form_class = forms.ProjectListClearForm

    page_title = 'Delete all Projects for this Unit?'

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


class ProjectPageMixin(UnitMixin):
    """
        Mixin for project pages
    """
    model = models.Project

    page_title_actions = [
        {'url': 'manager:unit-project-update', 'label': 'Edit'},
        {'url': 'manager:unit-project-remove',
            'label': 'Remove', 'classes': 'btn-danger'},
    ]

    def get_page_info(self):
        project = self.get_object()
        allocated_info = []
        if self.get_unit_object().is_allocated():
            allocated_info = [
                {'label': 'Is Allocated', 'content': render_exists_badge(
                    project.is_allocated())},
                {'label': 'Allocated Group Size',
                    'content': project.allocated_students.count()},
                {'label': 'Allocated Group Size',
                    'content': project.avg_allocated_pref if project.avg_allocated_pref else 'n/a'},
            ]
        description_info = []
        if project.description:
            description_info = [
                {
                    'label': 'Description',
                    'content': project.description,
                    'wide': True
                }
            ]

        return [
            {'label': 'Number', 'content': project.number},
            {'label': 'Name', 'content': project.name},
            {'label': 'Group Size',
                'content': f'{ project.min_students } - { project.max_students }'}
        ] + description_info + [
            {'label': 'Area', 'content': render_area_list(
                project.area) if project.area.count() else '-'},
        ] + allocated_info

    def get_queryset(self):
        return super().get_queryset().prefetch_related('allocated_students').annotate(avg_allocated_pref=Avg('allocated_students__allocated_preference_rank')).prefetch_related('area')

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            project = self.get_object()
            self.page_title = f'Project: {project.number} - {project.name}'
        return self.page_title

    def get_page_title_url(self):
        return reverse('manager:unit-project-detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class ProjectDetailView(ProjectPageMixin, MultiTableMixin, DetailView):
    """
        View a project in a unit
    """

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
            allocated_students_table = tables.ProjectAllocatedStudentsTable(
                data=project.allocated_students.all())
            allocated_students_table.name = 'Allocated Students'
            allocated_students_table.id = 'allocated'
            project_tables.append(allocated_students_table)

        return project_tables


class ProjectUpdateView(ProjectPageMixin, UpdateView):
    """
        Update a project in a unit
    """

    def get_form_class(self):
        return forms.ProjectAllocatedUpdateForm if self.get_unit_object().successfully_allocated() else forms.ProjectUpdateForm

    def get_success_url(self):
        return reverse('manager:unit-project-detail', kwargs={'pk': self.kwargs['pk'], 'pk_unit': self.kwargs['pk_unit']})


class ProjectDeleteView(ProjectPageMixin, DeleteView):
    """
        Remove a single project from a unit
    """
    form_class = forms.ProjectDeleteForm

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


"""

Preference Views

"""


class PreferencesView(UnitMixin, FilteredTableView):
    """
        Show a list of all submitted preferences by students for projects in a unit
    """
    model = models.ProjectPreference
    template_name = 'manager/preferences.html'
    page_title = 'Submitted Preferences'

    table_class = tables.PreferencesTable
    filterset_class = filters.PreferenceFilter
    filter_formhelper_class = filters.PreferenceFilterFormHelper

    def get_page_info(self):
        unit = self.get_unit_object()

        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        submitted_prefs_perc = round(
            (submitted_prefs_count/students_count)*100, 1)

        return [
            {'label': 'Total No. Students', 'content': unit.students_count},
            {'label': 'Percentage of Students who have Submitted Preferences',
                'content': f'{ submitted_prefs_perc }% ({ submitted_prefs_count } Students)'},
        ]

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


class PreferencesDistributionView(UnitMixin, FilteredTableView):
    """
        Show the distribution of preferences for projects in unit
    """
    model = models.Project
    page_title = 'Preference Distribution'

    table_class = tables.PreferencesDistributionTable
    filterset_class = filters.PreferenceDistributionFilter
    filter_formhelper_class = filters.PreferenceDistributionFilterFormHelper

    def get_page_info(self):
        unit = self.get_unit_object()

        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        submitted_prefs_perc = round(
            (submitted_prefs_count/students_count)*100, 1)

        submitted_prefs_count = submitted_prefs_count
        submitted_prefs_perc = submitted_prefs_perc

        return [
            {'label': 'Total No. Students', 'content': unit.students_count},
            {'label': 'Percentage of Students who have Submitted Preferences',
                'content': f'{ submitted_prefs_perc }% ({ submitted_prefs_count } Students)'},
            {'label': 'Project Popularity', 'content': 'The popularity of a project is calculated by summing the of number of students who preferred a project multiplied by the rank at which they preferred the project. Projects with a higher popularity index were more popular.', 'wide': True},
        ]

    def get_queryset(self):
        if not hasattr(self, 'queryset') or self.queryset == None:
            project_queryset = super().get_queryset().filter(
                unit_id=self.kwargs['pk_unit']).prefetch_related(
                'student_preferences')
            total_projects = project_queryset.count()
            self.queryset = project_queryset.annotate(popularity=Sum(
                total_projects - F('student_preferences__rank'))).order_by('number', 'name')
        return self.queryset


"""

Allocation Views

"""


class AllocationStartView(UnitMixin, TemplateView):
    """
        View for starting/viewing allocation
    """
    template_name = 'manager/allocation_start.html'
    page_title = 'Start Allocation'

    def get_page_info(self):
        unit = self.get_unit_object()

        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        submitted_prefs_perc = round(
            (submitted_prefs_count/students_count)*100, 1)

        return [
            {'label': 'Total No. Students', 'content': unit.students_count},
            {'label': 'Percentage of Students who have Submitted Preferences',
                'content': f'{ submitted_prefs_perc }% ({ submitted_prefs_count } Students)'},
        ]

    def post(self, request, *args, **kwargs):
        unit = self.get_unit_object()
        unit.is_allocating = True
        unit.save()

        tasks.start_allocation.delay(
            unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id, results_url=request.build_absolute_uri(reverse('manager:unit-allocation-results', kwargs={'pk_unit': self.kwargs['pk_unit']})))
        return HttpResponseRedirect(self.request.path)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = context.get('unit')

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
            project_spaces = {'too_few_students': min(min_spaces) > unit.students_count, 'min_project_space': min(min_spaces),
                              'too_many_students': sum(max_spaces) < unit.students_count, 'max_project_spaces': sum(max_spaces)}

        return {**context, **project_spaces}


class AllocationResultsView(UnitMixin, TemplateView):
    """
        View allocation results & stats
    """
    template_name = 'manager/allocation_results.html'

    page_title = 'Allocation Results'

    def get_page_warnings(self):
        unit = self.get_unit_object()
        warnings = []
        if unit.completed_allocation() and unit.get_unallocated_student_count() > 0:
            warnings.append({'type': 'warning', 'content': format_html(f"""
            <p>There {'are' if unit.get_unallocated_student_count() > 1 else 'is'} {unit.get_unallocated_student_count()} student{'s' if unit.get_unallocated_student_count() > 1 else ''} who {'are' if unit.get_unallocated_student_count() > 1 else 'is'} not allocated to a project.</p>
            <p class="mb-0">To fix this:</p>
            <ul class="my-0">
                <li>run the allocator again (this may change the project allocation if existing students), or</li>
                <li>manually add the unallocated student{'s' if unit.get_unallocated_student_count() > 1 else ''} to a project.</li>
            </ul>
        """)})
        return warnings if warnings != [] else None

    def get_page_info(self):
        unit = self.get_unit_object()

        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        submitted_prefs_perc = round(
            (submitted_prefs_count/students_count)*100, 1)

        return [
            {'label': 'Total No. Students', 'content': unit.students_count},
            {'label': 'Percentage of Students who have Submitted Preferences',
                'content': f'{ submitted_prefs_perc }% ({ submitted_prefs_count } Students)'},
            {'label': 'Allocation Status',
                'content': unit.get_allocation_descriptive()},
            {'label': 'Average Allocated Preference',
                'content': unit.avg_allocated_pref_rounded},
            {'label': 'Best Allocated Preference',
                'content': unit.min_allocated_pref},
            {'label': 'Worst Allocated Preference',
                'content': unit.max_allocated_pref},
        ]

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


"""

Area views

"""


class AreasListView(UnitMixin, FilteredTableView):
    """
        List of areas in unit
    """
    model = models.Area
    page_title = 'Area List'

    table_class = tables.AreaTable
    filter_class = filters.AreaFilter
    filter_formhelper_class = filters.AreaFilterFormHelper

    def get_page_actions(self):
        return [
            {'url': 'manager:unit-area-new', 'label': 'Add Area'},
            {'url': 'manager:unit-areas-clear',
             'label': 'Remove All Areas', 'classes': 'btn-danger', 'disabled': not self.get_queryset().exists()},
        ]

    def get_page_info(self):
        unit = self.get_unit_object()
        return [
            {'label': 'Preference Selection Limited by Area',
                'content': render_exists_badge(unit.limit_by_major)},
        ]

    def get_page_warnings(self):
        unit = self.get_unit_object()
        warnings = []
        if unit.completed_allocation() and unit.get_unallocated_student_count() > 0:
            warnings.append({'type': 'warning', 'content': format_html(f"""
            <p>There {'are' if unit.get_unallocated_student_count() > 1 else 'is'} {unit.get_unallocated_student_count()} student{'s' if unit.get_unallocated_student_count() > 1 else ''} who {'are' if unit.get_unallocated_student_count() > 1 else 'is'} not allocated to a project.</p>
            <p class="mb-0">To fix this:</p>
            <ul class="my-0">
                <li>run the allocator again (this may change the project allocation if existing students), or</li>
                <li>manually add the unallocated student{'s' if unit.get_unallocated_student_count() > 1 else ''} to a project.</li>
            </ul>
        """)})
        return warnings if warnings != [] else None

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).prefetch_related('students').prefetch_related('projects')


class AreaCreateView(UnitMixin, FormMixin, TemplateView):
    """
        Add a single area to the unit
    """
    form_class = forms.AreaForm
    page_title = 'Add Area'

    def get_success_url(self):
        return reverse('manager:unit-areas', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class AreasClearView(UnitMixin, FormMixin, TemplateView):
    """
        Clear all areas from unit
    """
    form_class = forms.AreaListClearForm

    page_title = 'Delete All Areas for this Unit?'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            models.Area.objects.filter(
                unit_id=self.kwargs['pk_unit']).delete()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('manager:unit-areas', kwargs={'pk_unit': self.kwargs['pk_unit']})


class AreaPageMixin(UnitMixin):
    """
    Mixin for area pages
    """
    model = models.Area

    page_title_actions = [
        {'url': 'manager:unit-area-update', 'label': 'Edit'},
        {'url': 'manager:unit-area-remove',
            'label': 'Remove', 'classes': 'btn-danger'},
    ]

    def get_queryset(self):
        return super().get_queryset().prefetch_related('projects').prefetch_related('students')

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            area = self.get_object()
            self.page_title = f'Area: {area.name}'
        return self.page_title

    def get_page_title_url(self):
        return reverse('manager:unit-area-detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class AreaDetailView(AreaPageMixin, MultiTableMixin, DetailView):
    """
        View a area in a unit
    """

    def get_tables(self):
        area_tables = []
        area = self.get_object()

        project_table = tables.AreaProjectsTable(
            data=area.projects.all())
        project_table.name = 'Projects'
        project_table.id = 'projects'
        area_tables.append(project_table)

        student_table = tables.AreaStudentsTable(
            data=area.students.all())
        student_table.name = 'Students'
        student_table.id = 'students'
        area_tables.append(student_table)

        return area_tables


class AreaUpdateView(AreaPageMixin, UpdateView):
    """
        Update a area in a unit
    """
    model = models.Area
    form_class = forms.AreaUpdateForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def get_success_url(self):
        return reverse('manager:unit-area-detail', kwargs={'pk': self.kwargs['pk'], 'pk_unit': self.kwargs['pk_unit']})


class AreaDeleteView(AreaPageMixin, DeleteView):
    """
        Remove a single area from a unit
    """
    form_class = forms.AreaDeleteForm

    def get_success_url(self):
        return reverse('manager:unit-areas', kwargs={'pk_unit': self.kwargs['pk_unit']})
