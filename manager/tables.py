from django.db.models import Count
from django.utils.html import format_html
from django.urls import reverse

import django_tables2 as tables

from core import models


class Table(tables.Table):
    class Meta:
        attrs = {'class': 'table table-striped align-middle'}
        empty_text = 'No Results'


"""

Project tables

"""


class ProjectsTable(Table):
    name = tables.Column(attrs={'td': {'style': 'width: 99%;'}})
    min_students = tables.Column(verbose_name='Min. Group Size')
    max_students = tables.Column(verbose_name='Max. Group Size')
    actions = tables.Column(empty_values=(), orderable=False, verbose_name='')

    class Meta(Table.Meta):
        model = models.Project
        fields = ['number', 'name', 'min_students', 'max_students', 'area']
        row_attrs = {'data-project-id': lambda record: record.pk}

    def render_number(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.number}</a>""")

    def render_actions(self, value, record):
        return format_html(f"""<div class="d-flex gap-2 justify-content-end">
                                <a class="btn btn-primary btn-sm" href="{reverse('manager:unit-project-update', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Edit</a>
                                <a class="btn btn-danger btn-sm" href="{reverse('manager:unit-project-remove', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Remove</a>
                            </div>
                            """)

    def render_area(self, value, record):
        areas_html = ''
        first = True
        for area in record.area.all():
            areas_html = areas_html + ('; ' if not first else '') + \
                f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-area-detail',kwargs={'pk_unit':area.unit_id,'pk':area.id})}">{area.name}</a>"""
            if first:
                first = False
        return format_html(f"""{areas_html}""")


class ProjectsAllocatedTable(ProjectsTable):
    allocated_students_count = tables.Column(
        empty_values=(), verbose_name='Allocated Group Size')
    avg_allocated_pref = tables.Column()
    # allocated_students = tables.Column(empty_values=(), orderable=False, verbose_name='Allocated Students')

    class Meta(ProjectsTable.Meta):
        sequence = ('number', 'name', 'min_students', 'max_students', 'area',
                    'allocated_students_count', 'avg_allocated_pref')

    def render_avg_allocated_pref(self, value, record):
        return round(value, 2)

    def order_num_allocated(self, queryset, is_descending):
        queryset = queryset.annotate(allocated_student_count=Count(
            'allocated_students')).order_by(('-' if is_descending else '') + 'allocated_student_count')
        return (queryset, True)

    def render_allocated_students(self, value, record):
        students = ''
        for student in value.all():
            students = students + \
                f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-student-detail', kwargs={'pk_unit': record.unit_id, 'pk': student.id})}">{student.student_id}</a>"""

        return format_html(f"""<div class="d-grid gap-1">{students}</div>""")


class ProjectPreferencesTable(Table):
    rank = tables.Column(verbose_name='Rank')
    student_count = tables.Column(verbose_name='Number of Students')

    class Meta(Table.Meta):
        pass


class ProjectAllocatedStudentsTable(Table):
    student_id = tables.Column(verbose_name='Student')
    allocated_preference_rank = tables.Column(
        verbose_name='Allocated Preference')

    class Meta(Table.Meta):
        model = models.Student
        fields = ['student_id', 'allocated_preference_rank']

    def render_student_id(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-student-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.student_id}</a>""")


"""

Student tables

"""


class StudentsTable(Table):
    student_id = tables.Column(
        accessor='student_id', verbose_name='Student ID')
    registered = tables.Column(
        accessor='user', empty_values=(), verbose_name='Registered')
    preferences = tables.Column(
        accessor='project_preferences', empty_values=(), verbose_name='Submitted Preferences')
    actions = tables.Column(empty_values=(), orderable=False, verbose_name='')

    class Meta(Table.Meta):
        model = models.Student
        fields = ['student_id', 'area']
        sequence = ('student_id', 'registered', 'preferences', 'area')

        row_attrs = {'data-student-id': lambda record: record.pk}

    def render_student_id(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-student-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.student_id}</a>""")

    def render_registered(self, value, record):
        bg_colour = 'success' if record.user_id else 'danger'
        icon_name = 'check' if record.user_id else 'x'
        return format_html(f"""<span class ="badge rounded-pill text-bg-{bg_colour}"><i class="bi bi-{icon_name}-lg"></i></span>""")

    def render_preferences(self, value, record):
        submitted_prefs = record.project_preferences.count()
        bg_colour = 'success' if submitted_prefs else 'danger'
        icon_name = 'check' if submitted_prefs else 'x'
        return format_html(f"""<span class ="badge rounded-pill text-bg-{bg_colour}"><i class="bi bi-{icon_name}-lg"></i></span>""")

    def render_area(self, value, record):
        areas_html = ''
        first = True
        for area in record.area.all():
            areas_html = areas_html + ('; ' if not first else '') + \
                f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-area-detail',kwargs={'pk_unit':area.unit_id,'pk':area.id})}">{area.name}</a>"""
            if first:
                first = False
        return format_html(f"""{areas_html}""")

    def render_actions(self, value, record):
        return format_html(f"""<div class="d-flex flex-wrap gap-2 justify-content-end">
                                <a class="btn btn-primary btn-sm" href="{reverse('manager:unit-student-update', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Edit</a>
                                <a class="btn btn-danger btn-sm" href="{reverse('manager:unit-student-remove', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Remove</a>
                            </div>
                            """)


class StudentsAllocatedTable(StudentsTable):
    allocated_project = tables.Column(
        empty_values=(), verbose_name='Allocated Project')
    allocated_preference_rank = tables.Column(
        empty_values=(), verbose_name='Allocated Preference')

    class Meta(StudentsTable.Meta):
        sequence = ('student_id', 'registered', 'area', 'preferences', 'allocated_project',
                    'allocated_preference_rank')

    def render_allocated_project(self, value, record):
        if record.allocated_project:
            return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.allocated_project.id})}">{record.allocated_project.number}: {record.allocated_project.name}</a>""")
        else:
            return 'n/a'

    def render_allocated_preference_rank(self, value, record):
        return value if value else 'n/a'


class StudentPreferencesTable(Table):
    rank = tables.Column(verbose_name='Rank')
    project = tables.Column(verbose_name='Project')

    class Meta(Table.Meta):
        model = models.ProjectPreference
        fields = ['rank', 'project']

    def render_project(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.project.unit_id, 'pk': record.project.id})}">{record.project.number}: {record.project.name}</a>""")


"""

Preference tables

"""


class PreferencesTable(Table):
    student__student_id = tables.Column(verbose_name='Student')
    project__number = tables.Column(verbose_name='Project')

    class Meta(Table.Meta):
        model = models.ProjectPreference
        fields = ['rank']

    def render_project__number(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.project.unit_id, 'pk': record.project.id})}">{record.project.number}: {record.project.name}</a>""")

    def render_student__student_id(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-student-detail', kwargs={'pk_unit': record.student.unit_id, 'pk': record.student.id})}">{record.student.student_id}</a>""")


class PreferencesDistributionTable(Table):
    number = tables.Column(verbose_name='Project')
    popularity = tables.Column(verbose_name='Project Popularity')

    class Meta(Table.Meta):
        model = models.Project
        fields = ['number']

    def render_number(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.number}: {record.name}</a>""")


"""

Area table

"""


class AreasTable(Table):
    projects = tables.Column(verbose_name='Has Projects')
    students = tables.Column(verbose_name='Has Students')
    actions = tables.Column(empty_values=(), orderable=False, verbose_name='')

    class Meta(Table.Meta):
        model = models.Area
        fields = ['name', 'projects', 'students']

    def render_name(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-area-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.name}</a>""")

    def render_actions(self, value, record):
        return format_html(f"""<div class="d-flex gap-2 justify-content-end">
                                <a class="btn btn-primary btn-sm" href="{reverse('manager:unit-area-update', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Edit</a>
                                <a class="btn btn-danger btn-sm" href="{reverse('manager:unit-area-remove', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Remove</a>
                            </div>
                            """)

    def render_projects(self, value, record):
        bg_colour = 'success' if record.projects.exists() else 'danger'
        icon_name = 'check' if record.projects.exists() else 'x'
        return format_html(f"""<span class ="badge rounded-pill text-bg-{bg_colour}"><i class="bi bi-{icon_name}-lg"></i></span>""")

    def render_students(self, value, record):
        bg_colour = 'success' if record.students.exists() else 'danger'
        icon_name = 'check' if record.students.exists() else 'x'
        return format_html(f"""<span class ="badge rounded-pill text-bg-{bg_colour}"><i class="bi bi-{icon_name}-lg"></i></span>""")


class AreaProjectsTable(Table):
    class Meta(Table.Meta):
        empty_text = 'There are no projects in this area.'
        model = models.Project
        fields = ['name']

    def render_name(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.number}: {record.name}</a>""")


class AreaStudentsTable(Table):

    class Meta(Table.Meta):
        empty_text = 'There are no students in this area.'
        model = models.Student
        fields = ['student_id']

    def render_student_id(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-student-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.student_id}</a>""")
