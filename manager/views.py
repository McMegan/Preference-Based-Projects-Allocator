import base64

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count, Sum, F, Avg, Min, Max
from django.db.models.functions import Round, Coalesce
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy, Resolver404, resolve
from django.utils.html import format_html
from django.views.generic import TemplateView, DetailView, CreateView, DeleteView, UpdateView
from django.views.generic.edit import FormMixin

from django_filters.views import FilterView, FilterMixin
from django_tables2 import SingleTableMixin, MultiTableMixin

from django_celery_results.models import TaskResult

from core import models
from core.views import IndexView
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
            f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit_area_detail',kwargs={'pk_unit':area.unit_id,'pk':area.id})}">{area.name}</a>"""
        if first:
            first = False
    return format_html(f"""{areas_html}""")


def user_is_manager(user):
    return user.is_manager


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


"""

Unit pages mixin

"""


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

    def save_task_to_unit(self, task):
        task = TaskResult.objects.filter(task_id=task.id)
        if task.exists():
            task = task.first()
            self.get_unit_object().celery_task = task
            self.get_unit_object().save()

    def make_sidebar_nav(self):
        unit = self.get_unit_object()
        return {
            'nav_items': [
                {'url': reverse('manager:unit', kwargs={'pk': unit.pk}), 'label': unit,
                 'classes': f'fs-6'},
                {
                    'url': reverse('manager:unit_projects', kwargs={'pk_unit': unit.pk}),
                    'label': f'Project List ({unit.projects_count})',
                    'nested_items': [
                        {'url': reverse('manager:unit_projects_new_list', kwargs={'pk_unit': unit.pk}),
                         'label': 'Upload Project List'},
                        {'url': reverse('manager:unit_projects_new', kwargs={'pk_unit': unit.pk}),
                         'label': 'Add a Project'},
                    ]
                },
                {
                    'url': reverse('manager:unit_students', kwargs={'pk_unit': unit.pk}),
                    'label': f'Student List ({unit.students_count})', 'classes': 'text-body-emphasis',
                    'nested_items': [
                        {'url': reverse('manager:unit_students_new_list', kwargs={'pk_unit': unit.pk}),
                         'label': 'Upload Student List'},
                        {'url': reverse('manager:unit_students_new', kwargs={'pk_unit': unit.pk}),
                         'label': 'Add a Student'},
                    ]
                },
                {
                    'url': reverse('manager:unit_areas', kwargs={'pk_unit': unit.pk}),
                    'label': f'Area List ({unit.areas_count})',
                    'nested_items': [
                        {'url': reverse('manager:unit_areas_new', kwargs={'pk_unit': unit.pk}),
                         'label': 'Add an Area'},
                    ]
                },
                {
                    'url': reverse('manager:unit_preferences', kwargs={'pk_unit': unit.pk}),
                    'label': 'Preference List',
                    'nested_items': [
                        {'url': reverse('manager:unit_preferences_distribution', kwargs={'pk_unit': unit.pk}),
                         'label': 'Project Popularity'},
                        {'url': reverse('manager:unit_preferences_new_list', kwargs={'pk_unit': unit.pk}),
                         'label': 'Upload Preference List'},
                    ]
                },
                {'url': reverse('manager:unit_allocation', kwargs={'pk_unit': unit.pk}),
                 'label': 'Allocation'}
            ]
        }

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            self.page_title = self.get_unit_object()
        return self.page_title

    def get_page_subtitle(self):
        if not hasattr(self, 'page_subtitle'):
            return None
        return self.page_subtitle

    def get_page_title_url(self):
        return self.request.path

    def get_page_info(self):
        if not hasattr(self, 'page_info'):
            return None
        return self.page_info

    def get_page_warnings(self):
        unit = self.get_unit_object()
        if not hasattr(self, 'warnings'):
            self.warnings = []

        if not self.unit.task_ready():
            warning_message = ''
            if self.unit.celery_task.task_name == models.Unit.START_ALLOCATION_TASK_NAME:
                warning_message = format_html(
                    """
                    <p class="fw-bold">Allocation In Progress</p>
                    <p>You can not make changes to the unit while it is allocating.</p>
                    <p>This may take a few minutes, please refresh the page to check if the allocation has been completed.</p>
                    <p class="mb-0">You should recieve an email once the allocation is completed.</p>
                """)
            elif self.unit.celery_task.task_name == models.Unit.EMAIL_ALLOCATION_RESULTS_TASK_NAME:
                warning_message = format_html(
                    """
                    <p class="fw-bold">Email of Allocation Results In Progress</p>
                    <p>You can not make changes to the unit while this is happening.</p>
                    <p class="mb-0">Please refresh the page to check if the email of the allocation results has been completed.</p>
                """)
            elif self.unit.celery_task.task_name == models.Unit.EMAIL_PREFERENCES_TASK_NAME:
                warning_message = format_html(
                    """
                    <p class="fw-bold">Email of Preference List In Progress</p>
                    <p>You can not make changes to the unit while this is happening.</p>
                    <p class="mb-0">Please refresh the page to check if the email of the preference list has been completed.</p>
                """)
            elif self.unit.celery_task.task_name == models.Unit.UPLOAD_PROJECTS_TASK_NAME:
                warning_message = format_html(
                    """
                    <p class="fw-bold">Project List Upload In Progress</p>
                    <p>You can not make changes to the unit while this is happening.</p>
                    <p class="mb-0">This may take a few moments, please refresh the page to check if it has been completed.</p>
                """)
            elif self.unit.celery_task.task_name == models.Unit.UPLOAD_STUDENTS_TASK_NAME:
                warning_message = format_html(
                    """
                    <p class="fw-bold">Student List Upload In Progress</p>
                    <p>You can not make changes to the unit while this is happening.</p>
                    <p class="mb-0">This may take a few moments, please refresh the page to check if it has been completed.</p>
                """)
            elif self.unit.celery_task.task_name == models.Unit.UPLOAD_PREFERENCES_TASK_NAME:
                warning_message = format_html(
                    """
                    <p class="fw-bold">Preference List Upload In Progress</p>
                    <p>You can not make changes to the unit while this is happening.</p>
                    <p class="mb-0">This may take a few minutes, please refresh the page to check if it has been completed.</p>
                """)
            self.warnings.append(
                {'type': 'danger', 'content': warning_message})
        if not unit.is_active:
            self.warnings.append(
                {'type': 'secondary', 'content': 'This unit is inactive.', 'classes': 'text-center'})
        if unit.minimum_preference_limit and unit.minimum_preference_limit > unit.projects_count:
            self.warnings.append(
                {'type': 'danger', 'content': 'The minimum preference limit is greater than the total number of projects in the unit. Please change this or else students will not be able to submit any preferences.'})
        if unit.completed_allocation() and unit.get_unallocated_student_count() > 0:
            self.warnings.append({'type': 'warning', 'content': format_html(f"""
            <p>There {'are' if unit.get_unallocated_student_count() > 1 else 'is'} {unit.get_unallocated_student_count()} student{'s' if unit.get_unallocated_student_count() > 1 else ''} who {'are' if unit.get_unallocated_student_count() > 1 else 'is'} not allocated to a project.</p>
            <p class="mb-0">To fix this:</p>
            <ul class="my-0">
                <li>run the allocator again (this may change the project allocation if existing students), or</li>
                <li>manually add the unallocated student{'s' if unit.get_unallocated_student_count() > 1 else ''} to a project.</li>
            </ul>
        """)})
        if unit.projects_count == 0 and unit.preference_submission_started() and not unit.preference_submission_ended():
            self.warnings.append(
                {'type': 'danger', 'content': 'The preference submission timeframe has started but there are currently no projects in the unit.'})
        if unit.students_count == 0 and unit.preference_submission_started() and not unit.preference_submission_ended():
            self.warnings.append(
                {'type': 'danger', 'content': 'The preference submission timeframe has started but there are currently no students in the unit.'})
        return self.warnings if self.warnings != [] else None

    def get_page_actions(self):
        if not hasattr(self, 'page_actions'):
            return None
        return self.page_actions

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **
                self.make_sidebar_nav(), 'unit': self.get_unit_object(), 'page_title': self.get_page_title(), 'page_subtitle': self.get_page_subtitle(), 'page_title_url': self.get_page_title_url(), 'page_info': self.get_page_info(), 'page_info_column': self.page_info_column if hasattr(self, 'page_info_column') else False, 'page_warnings': self.get_page_warnings(), 'page_actions': self.get_page_actions(), 'breadcrumbs': self.make_breadcrumbs()}

    def unit_managed_by_user(self):
        unit = self.get_unit_object()
        return unit.manager_id == self.request.user.id

    def test_func(self):
        return self.get_unit_queryset().exists() and user_is_manager(self.request.user) and self.unit_managed_by_user()

    def get_object(self, queryset=None):
        if not hasattr(self, 'object'):
            self.object = super().get_object(queryset)
        return self.object

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object(), 'cancel_url': self.get_success_url()}

    def make_breadcrumbs(self):
        breadcrumbs = []
        path_split = self.request.path[:-1].split('/')
        path = ''
        for segment in path_split:
            path = path + segment + '/'
            if path != '/' and path != '/manager/units/':
                try:
                    resolved = resolve(path)
                    match resolved.url_name:
                        case 'index':
                            label = 'Unit List'
                        case 'unit':
                            label = self.get_unit_object()
                        case 'unit_projects':
                            label = 'Project List'
                        case'unit_students':
                            label = 'Student List'
                        case 'unit_areas':
                            label = 'Area List'
                        case 'unit_preferences':
                            label = 'Preference List'
                        case 'unit_allocation':
                            label = 'Allocation'
                        case 'unit_preferences_distribution':
                            label = 'Project Popularity'
                        case 'unit_project_detail':
                            project = self.get_unit_object().projects.filter(pk=resolved.kwargs.get('pk'))
                            if project.exists():
                                label = f'Project {project.first().identifier}'
                        case 'unit_student_detail':
                            student = self.get_unit_object().students.filter(pk=resolved.kwargs.get('pk'))
                            if student.exists():
                                label = student.first()
                        case 'unit_area_detail':
                            area = self.get_unit_object().areas.filter(pk=resolved.kwargs.get('pk'))
                            if area.exists():
                                label = area.first()
                        case _:
                            if 'update' in resolved.url_name or 'delete' in resolved.url_name or 'new' in resolved.url_name:
                                label = self.get_page_subtitle()
                            else:
                                label = ''
                    if label != '':
                        breadcrumbs = breadcrumbs + [{'url': reverse(
                            f'{resolved.app_name}:{resolved.url_name}' if resolved.app_name else resolved.url_name, kwargs=resolved.kwargs), 'label': label}]
                except Resolver404:
                    """Skip segment of path"""
        return breadcrumbs


"""

Index view

"""


class IndexView(IndexView):
    def get_queryset(self):
        qs = models.Unit.objects
        if hasattr(super(), 'get_queryset'):
            qs = super().get_queryset()
        return qs.filter(manager=self.request.user).order_by('-is_active', 'year', 'code', 'name')

    def test_func(self):
        return super().test_func() and user_is_manager(self.request.user)


"""

Unit views

"""


class UnitCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = forms.UnitCreateForm
    template_name = 'manager/unit_new.html'
    success_url = reverse_lazy('manager:index')

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        if form.is_valid():
            form.instance.manager_id = request.user.id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def test_func(self):
        return user_is_manager(self.request.user)


class UnitPageMixin(UnitMixin):
    model = models.Unit
    unit_id_arg = 'pk'

    def get_page_title_url(self):
        return reverse('manager:unit', kwargs={'pk': self.kwargs['pk']})

    page_info_column = True

    def get_page_info(self):
        unit = self.get_object()
        allocated_info = []
        if unit.is_allocated():
            allocated_info = [
                {'label': 'Allocation Info', 'classes': 'fs-5'},
                {'label': 'Allocation Status',
                 'content': unit.get_allocation_descriptive(), 'classes': 'align-items-center', 'content_classes': f'rounded bg-{"success" if unit.successfully_allocated() else "danger"}-subtle border border-{"success" if unit.successfully_allocated() else "danger"}-subtle p-1 px-2'}
            ]
        return [
            {'label': 'Unit Code', 'content': unit.code},
            {'label': 'Unit Name', 'content': unit.name},
            {'label': 'Year', 'content': unit.year},
            {'label': 'Semester', 'content': unit.semester},
            {'label': 'Is Active/Current?', 'content': render_exists_badge(
                unit.is_active)},
            {'label': 'Preference Submission Settings', 'classes': 'fs-5'},
            {
                'label': 'Preference Submission Timeframe',
                'content': f'{ unit.get_preference_submission_start() if unit.preference_submission_start else "—" } - { unit.get_preference_submission_end() if unit.preference_submission_end else "—" }' if unit.preference_submission_start or unit.preference_submission_end else '—'
            },
            {'label': 'Minimum Preference Limit',
                'content': unit.minimum_preference_limit if unit.minimum_preference_limit else "—"},
            {'label': 'Maximum Preference Limit',
                'content': unit.maximum_preference_limit if unit.maximum_preference_limit else "—"},
            {'label': 'Limiting Preference Selection by Area', 'content': render_exists_badge(
                unit.limit_by_major)},
            {'label': 'Unit Status', 'classes': 'fs-5'},
            {'label': 'Projects Loaded', 'content': render_exists_badge(
                unit.projects.exists())},
            {'label': 'Students Loaded', 'content': render_exists_badge(
                unit.students.exists())},
        ] + allocated_info


class UnitDetailView(UnitPageMixin, DetailView):
    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_update',
                            kwargs={'pk': self.kwargs['pk']}), 'label': 'Edit'},
            {'url': reverse('manager:unit_delete', kwargs={'pk': self.kwargs['pk']}),
             'label': 'Delete', 'classes': 'btn-danger'},
        ]


class UnitUpdateView(UnitPageMixin, UpdateView):
    form_class = forms.UnitUpdateForm
    page_subtitle = 'Edit Unit'

    def get_page_info(self):
        return None

    def get_success_url(self):
        return reverse('manager:unit', kwargs={'pk': self.kwargs['pk']})


class UnitDeleteView(UnitPageMixin, DeleteView):
    success_url = reverse_lazy('index')
    page_subtitle = 'Delete Unit'

    def get_form(self):
        return forms.DeleteForm(**self.get_form_kwargs(), submit_label='Yes, Delete Unit', form_message='<p>Are you sure you want to delete this unit?</p>')

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'cancel_url': self.get_page_title_url()}


"""

    Student views
    
"""


class StudentsListMixin(UnitMixin):
    model = models.Student
    page_title = 'Student List'

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

    def get_queryset(self):
        qs = models.Student.objects
        if hasattr(super(), 'get_queryset'):
            qs = super().get_queryset()
        return qs.filter(unit=self.kwargs['pk_unit']).select_related('user').prefetch_related('project_preferences').select_related('allocated_project').prefetch_related('area').order_by('student_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.get_unit_object().is_allocated():
            allocated_student_count = self.get_unit_object().students.filter(
                allocated_project__isnull=False).count()
            context['allocated_student_count'] = allocated_student_count
            context['unallocated_student_count'] = self.get_unit_object(
            ).students.count()-allocated_student_count
        return context

    def get_page_title_url(self):
        return reverse('manager:unit_students', kwargs={'pk_unit': self.kwargs.get('pk_unit')})

    def get_success_url(self):
        return reverse('manager:unit_students', kwargs={'pk_unit': self.kwargs['pk_unit']})


class StudentsListView(StudentsListMixin, FilteredTableView):
    """
        List of students in unit
    """

    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_students_new_list',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Upload Student List'},
            {'url': reverse('manager:unit_students_new',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Add Student'},
            {'url': reverse('manager:unit_students_delete_all',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Remove All Students', 'classes': 'btn-danger', 'disabled': not self.get_unit_object().students.exists()},
        ]

    def get_filter_formhelper_class(self):
        return filters.StudentAllocatedFilterFormHelper if self.get_unit_object().successfully_allocated() else filters.StudentFilterFormHelper

    def get_filterset_class(self):
        return filters.StudentAllocatedFilter if self.get_unit_object().successfully_allocated() else filters.StudentFilter

    def get_table_class(self):
        return tables.StudentsAllocatedTable if self.get_unit_object().successfully_allocated() else tables.StudentsTable


class StudentCreateView(StudentsListMixin, FormMixin, TemplateView):
    """
        Add a single student to the unit's student list
    """
    form_class = forms.StudentForm
    page_subtitle = 'Add Student'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            # Check if user account exists for student
            user = models.User.objects.filter(
                username=form.cleaned_data.get('student_id'))
            if user.exists():
                user = user.first()
                form.instance.user_id = user.id
                user.is_student = True
                user.save()
            form.instance.save()
            form.instance.area.set(form.cleaned_data.get('area'))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class StudentsUploadListView(StudentsListMixin, FormMixin, TemplateView):
    """
        Upload list of students to a unit
    """
    form_class = forms.StudentListForm
    page_subtitle = 'Upload Student List'

    def post(self, request, *args, **kwargs):
        form = forms.StudentListForm(
            request.POST, request.FILES, unit=self.get_unit_object())
        if form.is_valid():
            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            file_bytes_base64 = base64.b64encode(file.read())
            file_bytes_base64_str = file_bytes_base64.decode('utf-8')

            task = tasks.upload_students_list_task.delay(
                unit_id=self.kwargs['pk_unit'],
                manager_id=self.request.user.id,
                file_bytes_base64_str=file_bytes_base64_str,
                override_list=form.cleaned_data.get('list_override'),

                student_id_column=form.cleaned_data.get('student_id_column'),
                student_name_column=form.cleaned_data.get(
                    'student_name_column'),
                area_column=form.cleaned_data.get(
                    'area_column')
            )
            self.save_task_to_unit(task=task)

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class StudentsClearView(StudentsListMixin, FormMixin, TemplateView):
    """
        Clear the student list of a unit
    """
    model = models.Student
    page_subtitle = 'Remove All Students'

    def get_form(self):
        return forms.DeleteForm(**self.get_form_kwargs(), submit_label='Yes, Remove All Students from Unit', form_message='<p>Are you sure you want to remove all students from this unit?</p>')

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            unit = self.get_unit_object()
            unit.students.all().delete()
            unit.is_allocated = False
            unit.allocation_status = None
            unit.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class StudentPageMixin(UnitMixin):
    """
    Mixin for student pages
    """
    model = models.Student

    def get_page_info(self):
        student = self.get_object()
        allocated_info = []
        if self.get_unit_object().is_allocated():
            allocated_info = [
                {'label': 'Allocated Project',
                    'content': format_html(f"""
                        <a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit_project_detail',kwargs={'pk_unit':student.unit_id,'pk':student.allocated_project_id})}">{student.allocated_project.identifier}: {student.allocated_project.name}</a>""") if student.allocated_project else 'n/a'},
                {'label': 'Allocated Preference Rank',
                    'content': student.allocated_preference_rank if student.allocated_preference_rank else 'n/a'},
            ]

        return [
            {'label': 'Student ID', 'content': student.student_id},
            {'label': 'Student Name', 'content': student.name if student.name else '-'},
            {'label': 'Registered', 'content': render_exists_badge(
                student.get_is_registered())},
            {'label': 'Submitted Preferences', 'content': render_exists_badge(
                student.preferences_count)},
            {'label': 'Area', 'content': render_area_list(
                student.area) if student.area.count() else '-'},

        ] + allocated_info

    def get_queryset(self):
        qs = models.Student.objects
        if hasattr(super(), 'get_queryset'):
            qs = super().get_queryset()
        return qs.select_related('user').prefetch_related('project_preferences').annotate(preferences_count=Count('project_preferences', distinct=True))

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            self.page_title = f'Student: {self.get_object().student_id }'
        return super().get_page_title()

    def get_page_title_url(self):
        return reverse('manager:unit_student_detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class StudentDetailView(StudentPageMixin, SingleTableMixin, DetailView):
    """
        View a single student in a unit
    """
    table_class = tables.StudentPreferencesTable

    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_student_update', kwargs={'pk': self.kwargs.get(
                'pk'), 'pk_unit': self.kwargs.get('pk_unit')}), 'label': 'Edit'},
            {'url': reverse('manager:unit_student_delete', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')}),
             'label': 'Remove', 'classes': 'btn-danger'},
        ]

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
    page_subtitle = 'Edit Student'

    def get_form_class(self):
        return forms.StudentAllocatedUpdateForm if self.get_unit_object().successfully_allocated() else forms.StudentUpdateForm

    def get_success_url(self):
        return reverse('manager:unit_student_detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class StudentDeleteView(StudentPageMixin, DeleteView):
    """
        Remove a single student from a unit
    """
    page_subtitle = 'Remove Student'

    def get_form(self):
        return forms.DeleteForm(**self.get_form_kwargs(), submit_label='Yes, Remove Student from Unit', form_message='<p>Are you sure you want to remove this student?</p>')

    def get_success_url(self):
        return reverse('manager:unit_students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'cancel_url': self.get_page_title_url()}


"""

Project views

"""


class ProjectsListMixin(UnitMixin):
    model = models.Project
    page_title = 'Project List'

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

    def get_queryset(self):
        qs = models.Project.objects
        if hasattr(super(), 'get_queryset'):
            qs = super().get_queryset()
        return qs.filter(unit=self.kwargs['pk_unit']).prefetch_related('unit').prefetch_related('area').prefetch_related('allocated_students').annotate(allocated_students_count=Count('allocated_students', distinct=True)).annotate(avg_allocated_pref=Avg('allocated_students__allocated_preference_rank')).order_by('identifier')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.get_unit_object().is_allocated():
            allocated_student_count = self.get_unit_object().students.filter(
                allocated_project__isnull=False).count()
            context['allocated_student_count'] = allocated_student_count
            context['unallocated_student_count'] = self.get_unit_object(
            ).students.count()-allocated_student_count
        return context

    def get_page_title_url(self):
        return reverse('manager:unit_projects', kwargs={'pk_unit': self.kwargs.get('pk_unit')})

    def get_success_url(self):
        return reverse('manager:unit_projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


class ProjectsListView(ProjectsListMixin, FilteredTableView):
    """
        List of projects in unit
    """

    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_projects_new_list',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Upload Project List'},
            {'url': reverse('manager:unit_projects_new',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Add Project'},
            {'url': reverse('manager:unit_projects_delete_all',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Remove All Projects', 'classes': 'btn-danger', 'disabled': not self.get_unit_object().projects.exists()},
        ]

    def get_filter_formhelper_class(self):
        return filters.ProjectAllocatedFilterFormHelper if self.get_unit_object().successfully_allocated() else filters.ProjectFilterFormHelper

    def get_filterset_class(self):
        return filters.ProjectAllocatedFilter if self.get_unit_object().successfully_allocated() else filters.ProjectFilter

    def get_table_class(self):
        return tables.ProjectsAllocatedTable if self.get_unit_object().successfully_allocated() else tables.ProjectsTable


class ProjectCreateView(ProjectsListMixin, FormMixin, TemplateView):
    form_class = forms.ProjectForm
    page_subtitle = 'Add Project'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            form.instance.area.set(form.cleaned_data.get('area'))
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ProjectsUploadListView(ProjectsListMixin, FormMixin, TemplateView):
    """
        Upload list of projects
    """
    form_class = forms.ProjectListForm
    page_subtitle = 'Upload Project List'

    def post(self, request, *args, **kwargs):
        form = forms.ProjectListForm(
            request.POST, request.FILES, unit=self.get_unit_object())
        if form.is_valid():
            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            file_bytes_base64 = base64.b64encode(file.read())
            file_bytes_base64_str = file_bytes_base64.decode('utf-8')

            task = tasks.upload_projects_list_task.delay(
                unit_id=self.kwargs['pk_unit'],
                manager_id=self.request.user.id, file_bytes_base64_str=file_bytes_base64_str,
                override_list=form.cleaned_data.get('list_override'),
                identifier_column=form.cleaned_data.get('identifier_column'),
                name_column=form.cleaned_data.get('name_column'),
                min_students_column=form.cleaned_data.get(
                    'min_students_column'),
                max_students_column=form.cleaned_data.get(
                    'max_students_column'),
                description_column=form.cleaned_data.get('description_column'),
                area_column=form.cleaned_data.get('area_column')
            )
            self.save_task_to_unit(task=task)

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ProjectsClearView(ProjectsListMixin, FormMixin, TemplateView):
    """
        Clear the project list of a unit
    """
    page_subtitle = 'Remove All Projects'

    def get_form(self):
        return forms.DeleteForm(**self.get_form_kwargs(), submit_label='Yes, Remove All Projects from Unit', form_message=f'<p>Are you sure you want to remove all projects from this unit?</p>' + ('<div class="alert alert-danger">The preference submission timeframe is open, removing all projects now will remove all submitted preferences as well.</div>' if self.get_unit_object().preference_submission_open() else ''))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            unit = self.get_unit_object()
            unit.projects.all().delete()
            unit.is_allocated = False
            unit.allocation_status = None
            unit.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ProjectPageMixin(UnitMixin):
    """
        Mixin for project pages
    """
    model = models.Project

    page_info_column = True

    def get_page_info(self):
        project = self.get_object()
        allocated_info = []
        if self.get_unit_object().is_allocated():
            allocated_info = [
                {'label': 'Is Allocated', 'content': render_exists_badge(
                    project.is_allocated())},
                {'label': 'Allocated Group Size',
                    'content': project.allocated_students.count()},
                {'label': 'Average Allocated Preference',
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
            {'label': 'ID', 'content': project.identifier},
            {'label': 'Name', 'content': project.name},
            {'label': 'Group Size',
                'content': f'{ project.min_students } - { project.max_students }'}
        ] + description_info + [
            {'label': 'Area', 'content': render_area_list(
                project.area) if project.area.count() else '-'},
        ] + allocated_info

    def get_queryset(self):
        qs = models.Project.objects
        if hasattr(super(), 'get_queryset'):
            qs = super().get_queryset()
        return qs.prefetch_related('allocated_students').annotate(avg_allocated_pref=Avg('allocated_students__allocated_preference_rank')).prefetch_related('area')

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            project = self.get_object()
            self.page_title = f'Project: {project.identifier} - {project.name}'
        return self.page_title

    def get_page_title_url(self):
        return reverse('manager:unit_project_detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class ProjectDetailView(ProjectPageMixin, MultiTableMixin, DetailView):
    """
        View a project in a unit
    """

    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_project_update', kwargs={'pk': self.kwargs.get(
                'pk'), 'pk_unit': self.kwargs.get('pk_unit')}), 'label': 'Edit'},
            {'url': reverse('manager:unit_project_delete', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')}),
             'label': 'Remove', 'classes': 'btn-danger'},
        ]

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
    page_subtitle = 'Edit Project'

    def get_form_class(self):
        return forms.ProjectAllocatedUpdateForm if self.get_unit_object().successfully_allocated() else forms.ProjectUpdateForm

    def get_success_url(self):
        return reverse('manager:unit_project_detail', kwargs={'pk': self.kwargs['pk'], 'pk_unit': self.kwargs['pk_unit']})

    def get_page_info(self):
        return []


class ProjectDeleteView(ProjectPageMixin, DeleteView):
    """
        Remove a single project from a unit
    """
    page_subtitle = 'Remove Project'

    def get_form(self):
        return forms.DeleteForm(**self.get_form_kwargs(), submit_label='Yes, Remove Project from Unit', form_message='<p>Are you sure you want to remove this project?</p>' + ('<div class="alert alert-danger">The preference submission timeframe is open, removing a project now will remove the project from the preferences of students who preferred this project. This may result in students having fewer preferences than the minimum preference limit, if it was set.</div>' if self.get_unit_object().preference_submission_open() else ''))

    def get_success_url(self):
        return reverse('manager:unit_projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def form_valid(self, form):
        success_url = self.get_success_url()
        # Adjust student preferences
        update_prefs = []
        for preference in self.object.student_preferences.all():
            for preference in preference.student.project_preferences.all()[
                    preference.rank - 1:]:
                preference.rank = preference.rank - 1
                update_prefs.append(preference)
        self.object.delete()
        models.ProjectPreference.objects.bulk_update(
            update_prefs, fields=['rank'])
        return HttpResponseRedirect(success_url)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'cancel_url': self.get_page_title_url()}


"""

Area views

"""


class AreasListMixin(UnitMixin):
    model = models.Area
    page_title = 'Area List'

    def get_page_info(self):
        unit = self.get_unit_object()
        return [
            {'label': 'Preference Selection Limited by Area',
                'content': render_exists_badge(unit.limit_by_major)},
        ]

    def get_queryset(self):
        qs = models.Area.objects
        if hasattr(super(), 'get_queryset'):
            qs = super().get_queryset()
        return qs.filter(unit=self.kwargs['pk_unit']).prefetch_related('students').prefetch_related('projects').order_by('name')

    def get_page_title_url(self):
        return reverse('manager:unit_areas', kwargs={'pk_unit': self.kwargs.get('pk_unit')})

    def get_success_url(self):
        return reverse('manager:unit_areas', kwargs={'pk_unit': self.kwargs['pk_unit']})


class AreasListView(AreasListMixin, FilteredTableView):
    """
        List of areas in unit
    """
    model = models.Area

    table_class = tables.AreasTable
    filterset_class = filters.AreaFilter
    filter_formhelper_class = filters.AreaFilterFormHelper

    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_areas_new',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Add Area'},
            {'url': reverse('manager:unit_areas_delete_all', kwargs={'pk_unit': self.kwargs['pk_unit']}),
             'label': 'Remove All Areas', 'classes': 'btn-danger', 'disabled': not self.get_unit_object().areas.exists()},
        ]


class AreaCreateView(AreasListMixin, FormMixin, TemplateView):
    """
        Add a single area to the unit
    """
    form_class = forms.AreaForm
    page_subtitle = 'Add Area'

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class AreasClearView(AreasListMixin, FormMixin, TemplateView):
    """
        Clear all areas from unit
    """
    page_subtitle = 'Remove All Areas'

    def get_form(self):
        return forms.DeleteForm(**self.get_form_kwargs(), submit_label='Yes, Remove All Areas from Unit', form_message='<p>Are you sure you want to remove all areas from this unit?</p><p>Any projects and students with an area will be retained.</p>')

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            models.Area.objects.filter(
                unit_id=self.kwargs['pk_unit']).delete()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class AreaPageMixin(UnitMixin):
    """
    Mixin for area pages
    """
    model = models.Area

    def get_page_info(self):
        area = self.get_object()
        return [
            {'label': 'No. Projects', 'content': area.projects.count()},
            {'label': 'No. Students', 'content': area.students.count()},
        ]

    def get_queryset(self):
        qs = models.Area.objects
        if hasattr(super(), 'get_queryset'):
            qs = super().get_queryset()
        return qs.prefetch_related('projects').prefetch_related('students')

    def get_page_title(self):
        if not hasattr(self, 'page_title'):
            area = self.get_object()
            self.page_title = f'Area: {area.name}'
        return self.page_title

    def get_page_title_url(self):
        return reverse('manager:unit_area_detail', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')})


class AreaDetailView(AreaPageMixin, MultiTableMixin, DetailView):
    """
        View a area in a unit
    """

    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_area_update', kwargs={'pk': self.kwargs.get(
                'pk'), 'pk_unit': self.kwargs.get('pk_unit')}), 'label': 'Edit'},
            {'url': reverse('manager:unit_area_delete', kwargs={'pk': self.kwargs.get('pk'), 'pk_unit': self.kwargs.get('pk_unit')}),
             'label': 'Remove', 'classes': 'btn-danger'},
        ]

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
    page_subtitle = 'Edit Area'

    form_class = forms.AreaUpdateForm

    def get_success_url(self):
        return reverse('manager:unit_area_detail', kwargs={'pk': self.kwargs['pk'], 'pk_unit': self.kwargs['pk_unit']})


class AreaDeleteView(AreaPageMixin, DeleteView):
    """
        Remove a single area from a unit
    """
    page_subtitle = 'Remove Area'

    def get_form(self):
        return forms.DeleteForm(**self.get_form_kwargs(), submit_label='Yes, Remove Area from Unit', form_message='<p>Are you sure you want to remove this project?</p><p>Any projects and students with this area will be retained.</p>')

    def get_success_url(self):
        return reverse('manager:unit_areas', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'cancel_url': self.get_page_title_url()}


"""

Preference Views

"""


class PreferencesMixin(UnitMixin):
    page_title = 'Preference List'

    def get_page_info(self):
        unit = self.get_unit_object()
        students_exist_info = []

        students_list = unit.students
        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()

        if unit.students_count != 0:
            submitted_prefs_perc = round(
                (submitted_prefs_count/unit.students_count)*100, 1)

            students_exist_info = [
                {'label': 'Percentage of Students who have Submitted Preferences',
                 'content': f'{submitted_prefs_perc}% ({submitted_prefs_count} / {unit.students_count} Students)'}
            ]

        return [
            {'label': 'Total No. Students', 'content': unit.students_count}
        ] + students_exist_info

    def get_page_title_url(self):
        return reverse('manager:unit_preferences', kwargs={'pk_unit': self.get_unit_object().pk})

    def get_success_url(self):
        return reverse('manager:unit_preferences', kwargs={'pk_unit': self.get_unit_object().pk})


class PreferencesView(PreferencesMixin, FilteredTableView):
    """
        Show a list of all submitted preferences by students for projects in a unit
    """
    model = models.ProjectPreference
    template_name = 'manager/preferences.html'

    table_class = tables.PreferencesTable
    filterset_class = filters.PreferenceFilter
    filter_formhelper_class = filters.PreferenceFilterFormHelper

    def get_page_actions(self):
        return [
            {'url': reverse('manager:unit_preferences_new_list',
                            kwargs={'pk_unit': self.kwargs['pk_unit']}), 'label': 'Upload Preference List'},
        ]

    def get_queryset(self):
        return super().get_queryset().filter(project__unit_id=self.kwargs['pk_unit']).prefetch_related('project').prefetch_related('student')

    def post(self, request, *args, **kwargs):
        email_results = 'email_results' in request.POST
        from . import export
        if email_results:
            task = tasks.email_preferences_csv_task.delay(
                unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id)
            self.save_task_to_unit(task=task)
            return HttpResponseRedirect(self.request.path)
        return export.download_preferences_csv(unit_id=self.kwargs['pk_unit'])


class PreferencesDistributionView(PreferencesMixin, FilteredTableView):
    """
        Show the distribution of preferences for projects in unit
    """
    model = models.Project
    page_subtitle = 'Project Popularity'

    table_class = tables.PreferencesDistributionTable
    filterset_class = filters.PreferenceDistributionFilter
    filter_formhelper_class = filters.PreferenceDistributionFilterFormHelper

    def get_page_info(self):
        return super().get_page_info() + [
            {'label': 'Project Popularity', 'content': format_html(
                """<p>The popularity of a project is calculated by summing the of number of students who preferred a project multiplied by the total number of projects minus the rank at which they preferred the project.</p>
                <p class="my-4">Project Popularity = <span id="project_pop_formula"><span id="project_pop_sum">&sum;</span><span> N_Proj - rank for preference i</span></span></p>
                <p>Where N_Pref is the total number of preferences submitted for a particular project, and N_Proj is the total number of projects in the unit.</p>
                <p>Projects with a higher popularity index were more popular.</p>"""), 'wide': True},
        ]

    def get_queryset(self):
        if not hasattr(self, 'queryset') or self.queryset == None:
            project_queryset = super().get_queryset().filter(
                unit_id=self.kwargs['pk_unit']).prefetch_related(
                'student_preferences')
            total_projects = project_queryset.count()
            self.queryset = project_queryset.annotate(popularity=Coalesce(Sum(
                total_projects - F('student_preferences__rank')), 0)).order_by('identifier', 'name')
        return self.queryset


class PreferencesUploadListView(PreferencesMixin, FormMixin, TemplateView):
    """
        Upload a list of preferences
    """
    model = models.ProjectPreference
    form_class = forms.PreferenceListForm
    page_subtitle = 'Upload Preference List'

    def post(self, request, *args, **kwargs):
        form = forms.PreferenceListForm(
            request.POST, request.FILES, unit=self.get_unit_object())
        if form.is_valid():
            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            file_bytes_base64 = base64.b64encode(file.read())
            file_bytes_base64_str = file_bytes_base64.decode('utf-8')

            task = tasks.upload_preferences_list_task.delay(
                unit_id=self.kwargs['pk_unit'],
                manager_id=self.request.user.id, file_bytes_base64_str=file_bytes_base64_str,
                preference_rank_column=form.cleaned_data.get(
                    'preference_rank_column'),
                student_id_column=form.cleaned_data.get('student_id_column'),
                project_identifier_column=form.cleaned_data.get(
                    'project_identifier_column')
            )
            self.save_task_to_unit(task=task)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


"""

Allocation Views

"""


class AllocationView(UnitMixin, TemplateView):
    """
        View for starting/viewing allocation
    """
    template_name = 'manager/allocation.html'
    page_title = 'Allocation'

    def get_context_data(self, **kwargs):
        unit = self.get_unit_object()
        allocation_warnings = []
        can_start_allocation = True
        if unit.projects_count == 0:
            can_start_allocation = False
            allocation_warnings.append(
                'You must add projects to the unit before it can be allocated.')
        if unit.students_count == 0:
            can_start_allocation = False
            allocation_warnings.append(
                'You must add students to the unit before it can be allocated.')
        elif unit.preference_submission_set() and not unit.preference_submission_ended():
            can_start_allocation = False
            allocation_warnings.append(
                'The preference submission timeframe must end before the unit can be allocated.')
        if unit.get_too_few_students():
            can_start_allocation = False
            allocation_warnings.append(format_html(f"""<p>There are too few students enrolled in the unit compared to the minimum project spaces.</p>
                    <p>
                        <span class="fw-semibold">Students:</span> { unit.students_count }, <span class="fw-semibold">Minimum Spaces:</span> { unit.get_min_project_spaces() }
                    </p>
                    <p class="mb-0">To fix this:</p>
                    <ul class="my-0">
                        <li>change the minimum group size for a project, or</li>
                        <li>add students to the student list.</li>
                    </ul>"""))
        if unit.get_too_many_students():
            can_start_allocation = False
            allocation_warnings.append(format_html(f"""<p>There are too many students enrolled in the unit compared to the maximum project spaces.</p>
                    <p>
                        <span class="fw-semibold">Students:</span> {unit.students_count}, <span class="fw-semibold">Maximum Spaces:</span> {unit.get_max_project_spaces()}
                    </p>
                    <p class="mb-0">To fix this:</p>
                    <ul class="my-0">
                        <li>change the maximum group size for a project, or</li>
                        <li>add projects to the project list, or</li>
                        <li>remove students from the student list.</li>
                    </ul>"""))
        return {**super().get_context_data(**kwargs),  'can_start_allocation': can_start_allocation, 'allocation_warnings': allocation_warnings}

    page_info_column = True

    def get_page_info(self):
        unit = self.get_unit_object()
        allocated_info = []
        if unit.is_allocated():
            allocated_info = [
                {'label': 'Allocation Status',
                 'content': unit.get_allocation_descriptive(), 'classes': 'align-items-center', 'content_classes': f'rounded bg-{"success" if unit.successfully_allocated() else "danger"}-subtle border border-{"success" if unit.successfully_allocated() else "danger"}-subtle p-1 px-2'},
                {'label': 'Average Allocated Preference',
                    'content': unit.avg_allocated_pref_rounded if unit.avg_allocated_pref_rounded else '—'},
                {'label': 'Best Allocated Preference',
                    'content': unit.min_allocated_pref if unit.min_allocated_pref else '—'},
                {'label': 'Worst Allocated Preference',
                    'content': unit.max_allocated_pref if unit.max_allocated_pref else '—'},
            ]

        students_list = models.Student.objects.filter(
            unit=self.kwargs['pk_unit'])
        students_count = students_list.count()
        if students_count == 0:
            return [
                {'label': 'Total No. Students', 'content': unit.students_count}]

        submitted_prefs_count = students_list.annotate(project_preference_count=Count(
            'project_preferences')).filter(project_preference_count__gt=0).count()
        submitted_prefs_perc = round(
            (submitted_prefs_count/students_count)*100, 1)

        return [
            {'label': 'Total No. Students', 'content': unit.students_count},
            {'label': 'Percentage of Students who have Submitted Preferences',
                'content': f'{ submitted_prefs_perc }% ({ submitted_prefs_count } Students)'},
        ] + allocated_info

    def get_unit_queryset(self):
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = super().get_unit_queryset().prefetch_related('projects').prefetch_related('students').annotate(
                avg_allocated_pref_rounded=Round(Avg('students__allocated_preference_rank'), 2)).annotate(
                max_allocated_pref=Max('students__allocated_preference_rank')).annotate(
                min_allocated_pref=Min('students__allocated_preference_rank'))
        return self.unit_queryset

    def post(self, request, *args, **kwargs):
        if 'start_allocation' in request.POST:
            task = tasks.start_allocation_task.delay(
                unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id, results_url=request.build_absolute_uri(reverse('manager:unit_allocation', kwargs={'pk_unit': self.kwargs['pk_unit']})))
            self.save_task_to_unit(task=task)
            return HttpResponseRedirect(self.request.path)
        from . import export
        if 'email_results' in request.POST:
            task = tasks.email_allocation_results_csv_task.delay(
                unit_id=self.kwargs['pk_unit'], manager_id=self.request.user.id)
            self.save_task_to_unit(task=task)
            return HttpResponseRedirect(self.request.path)
        if 'download_results' in request.POST:
            return export.download_allocation_results_csv(unit_id=self.kwargs['pk_unit'])
        return HttpResponseRedirect(self.request.path)
