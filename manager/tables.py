from django.db.models import Count, Sum, F, Avg, Min, Max
from django.utils.html import format_html
from django.urls import reverse

import django_tables2 as tables

from core import models


class ProjectTable(tables.Table):
    name = tables.Column(attrs={'td': {'style': 'width: 99%;'}})
    actions = tables.Column(empty_values=(), orderable=False, verbose_name='')
    min_students = tables.Column(verbose_name='Minimum Group Size')
    max_students = tables.Column(verbose_name='Maximum Group Size')

    class Meta:
        attrs = {'class': 'table table-striped'}

        model = models.Project
        template_name = "django_tables2/bootstrap5.html"
        fields = ['number', 'name', 'min_students', 'max_students']

        row_attrs = {'data-project-id': lambda record: record.pk}

    def render_number(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.number}</a>""")

    def render_name(self, value, record):
        if record.description:
            return format_html(f"""
                <div class="d-grid gap-2">
                    <div class="d-flex align-items-center justify-content-between">
                        <span>{record.name}</span>
                        <button type="button" onclick="toggle_info({record.id})" class="project_info_toggle_button btn btn-sm"><i class="bi bi-chevron-down"></i></button>
                    </div>
                    <div class="project_info" data-project-id="{record.id}" style="display: none;">
                        <table class="table table-sm table-bordered m-0">
                            <tbody>
                                <tr>
                                    <th style="background-color: transparent;">Description</th>
                                </tr>
                                <tr>
                                    <td class="project_description" style="background-color: transparent;">{record.description}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            """)
        return record.name

    def render_actions(self, value, record):
        return format_html(f"""<div class="d-flex gap-2 justify-content-end">
                                <a class="btn btn-primary btn-sm" href="{reverse('manager:unit-project-update', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Edit</a>
                                <a class="btn btn-danger btn-sm" href="{reverse('manager:unit-project-remove', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Remove</a>
                            </div>
                            """)


class ProjectAllocatedTable(ProjectTable):
    num_allocated = tables.Column(
        empty_values=(), verbose_name='No. Allocated Students')
    assigned_students = tables.Column(
        empty_values=(), orderable=False, verbose_name='Allocated Students')

    class Meta(ProjectTable.Meta):
        sequence = ('number', 'name', 'min_students', 'max_students',
                    'num_allocated', 'assigned_students')

    def render_num_allocated(self, value, record):
        return record.assigned_students.count()

    def order_num_allocated(self, queryset, is_descending):
        queryset = queryset.annotate(allocated_student_count=Sum(
            'assigned_students')).order_by(('-' if is_descending else '') + 'allocated_student_count')
        return (queryset, True)

    def render_assigned_students(self, value, record):
        students = ''
        for student in value.all():
            students = students + \
                f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-student-detail', kwargs={'pk_unit': record.unit_id, 'pk': student.id})}">{student.student_id}</a>"""

        return format_html(f"""<div class="d-grid gap-1">{students}</div>""")


class StudentTable(tables.Table):
    student_id = tables.Column(
        accessor='student_id', verbose_name='Student ID')
    registered = tables.Column(
        accessor='user', empty_values=(), verbose_name='Registered')
    preferences = tables.Column(
        accessor='project_preferences', empty_values=(), verbose_name='Submitted Preferences')
    actions = tables.Column(empty_values=(), orderable=False, verbose_name='')

    class Meta:
        attrs = {'class': 'table table-striped'}

        model = models.EnrolledStudent
        template_name = "django_tables2/bootstrap5.html"
        fields = ['student_id']

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

    def render_actions(self, value, record):
        return format_html(f"""<div class="d-flex gap-2 justify-content-end">
                                <a class="btn btn-danger btn-sm" href="{reverse('manager:unit-student-remove', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">Remove</a>
                            </div>
                            """)


class StudentAllocatedTable(StudentTable):
    assigned_project = tables.Column(
        empty_values=(), verbose_name='Allocated Project')
    assigned_preference_rank = tables.Column(
        empty_values=(), verbose_name='Allocated Preference')

    class Meta(StudentTable.Meta):
        sequence = ('student_id', 'registered', 'preferences', 'assigned_project',
                    'assigned_preference_rank')

    def render_assigned_project(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.unit_id, 'pk': record.id})}">{record.assigned_project.number}: {record.assigned_project.name}</a>""")

    def render_assigned_preference_rank(self, value, record):
        return value if value else 'n/a'
