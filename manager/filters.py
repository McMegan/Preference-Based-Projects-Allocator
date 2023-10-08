from django.db.models import Count

import django_filters

from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import FormActions, InlineField, InlineRadios
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, Div
from crispy_bootstrap5.bootstrap5 import FloatingField

from core import models
from core.filters import ExistsMultipleChoiceFilter, ExistsMultipleChoiceFilterSet


def unit_projects(request):
    if request is None:
        return models.Projects.objects.none()
    pk_unit = request.resolver_match.kwargs.get('pk_unit')
    if not pk_unit:
        return models.Projects.objects.none()
    return models.Project.objects.filter(unit=pk_unit)


def unit_students(request):
    if request is None:
        return models.Student.objects.none()
    pk_unit = request.resolver_match.kwargs.get('pk_unit')
    if not pk_unit:
        return models.Student.objects.none()
    return models.Student.objects.filter(unit=pk_unit)


def unit_areas(request):
    if request is None:
        return models.Area.objects.none()
    pk_unit = request.resolver_match.kwargs.get('pk_unit')
    if not pk_unit:
        return models.Area.objects.none()
    return models.Area.objects.filter(unit=pk_unit)


"""

Student Filters

"""


class StudentFilter(ExistsMultipleChoiceFilterSet):
    student_id = django_filters.CharFilter(
        lookup_expr='icontains', label='Student ID')
    name = django_filters.CharFilter(
        lookup_expr='icontains', label='Student Name')
    registered = ExistsMultipleChoiceFilter(
        field_name='user', exists_label='Registered Students', not_exists_label='Un-Registered Students')
    preferences = ExistsMultipleChoiceFilter(
        field_name='project_preferences', exists_label='Submitted Preferences', not_exists_label='Didn\'t Submit Preferences')
    area = django_filters.ModelMultipleChoiceFilter(
        queryset=unit_areas, label='Area')

    class Meta:
        model = models.Student
        fields = ['student_id', 'area']


class StudentAllocatedFilter(StudentFilter):
    allocated_project = django_filters.ModelMultipleChoiceFilter(
        queryset=unit_projects, label='Allocated Project')
    allocated_preference_rank = django_filters.NumberFilter(
        label='Allocated Preference')
    allocated = ExistsMultipleChoiceFilter(
        field_name='allocated_project', exists_label='Allocated Students', not_exists_label='Unallocated Students')


student_filter_form_layout_main = Fieldset(
    '',
    Div(
        Div(FloatingField('student_id'), css_class='flex-grow-1'),
        Div(FloatingField('name'), css_class='flex-grow-1'),
        css_class='mb-3 d-flex flex-wrap column-gap-3 align-items-center'
    ),
    Div(
        InlineRadios('registered'),
        InlineRadios('preferences'),
        css_class='mb-3 d-flex flex-wrap column-gap-3 align-items-center'
    ),
    Div('area', css_class='w-100'),
    css_class='mb-3 d-grid gap-1 align-items-center'
)


class StudentFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        student_filter_form_layout_main,
        FormActions(
            Submit('submit', 'Filter'),
            HTML(
                """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit_students' unit.id %}">Clear Filters</a>{% endif %}""")
        )
    )


class StudentAllocatedFilterFormHelper(StudentFilterFormHelper):
    layout = Layout(
        student_filter_form_layout_main,
        Fieldset(
            'Filter by Student Allocation',
            Div(FloatingField('allocated_preference_rank'),
                css_class='w-100'),
            InlineRadios('allocated'),
            Div('allocated_project',
                css_class='flex-grow-1'),
            css_class='mb-3 d-flex flex-wrap gap-1 align-items-center'
        ),
        FormActions(
            Submit('submit', 'Filter'),
            HTML(
                """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit_students' unit.id %}">Clear Filters</a>{% endif %}""")
        )
    )


"""

Project Filters

"""


class ProjectFilter(django_filters.FilterSet):
    identifier = django_filters.NumberFilter(
        lookup_expr='contains', label='ID')
    name = django_filters.CharFilter(lookup_expr='icontains', label='Name')
    min_students = django_filters.NumberFilter(label='Min. Group Size')
    max_students = django_filters.NumberFilter(label='Max. Group Size')

    area = django_filters.ModelMultipleChoiceFilter(
        queryset=unit_areas, label='Area')

    class Meta:
        model = models.Project
        fields = ['identifier', 'name', 'min_students', 'max_students', 'area']


class ProjectAllocatedFilter(ExistsMultipleChoiceFilterSet, ProjectFilter):
    num_allocated = django_filters.NumberFilter(
        field_name='allocated_students', label='Allocated Group Size', method='filter_num_allocated',)
    allocated = ExistsMultipleChoiceFilter(
        field_name='allocated_students', exists_label='Allocated Projects', not_exists_label='Unallocated Projects')

    def filter_num_allocated(self, queryset, name, value):
        return queryset.annotate(allocated_student_count=Count(
            'allocated_students')).filter(allocated_student_count=value)


project_filter_form_layout_main = Fieldset(
    '',
    FloatingField('identifier'),
    FloatingField('name'),
    FloatingField('min_students'),
    FloatingField('max_students'),
    Div('area', css_class='w-100'),
    css_class='d-flex flex-wrap column-gap-3 align-items-center'
)


class ProjectFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        project_filter_form_layout_main,
        FormActions(
            Submit('submit', 'Filter'),
            HTML(
                """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit_projects' unit.id %}">Clear Filters</a>{% endif %}""")
        )
    )


class ProjectAllocatedFilterFormHelper(ProjectFilterFormHelper):
    layout = Layout(
        project_filter_form_layout_main,
        Fieldset(
            'Filter by Allocation',
            Div(FloatingField('num_allocated'), css_class='w-100'),
            InlineRadios('allocated'),
            css_class='d-grid column-gap-3'
        ),
        FormActions(
            Submit('submit', 'Filter'),
            HTML(
                """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit_projects' unit.id %}">Clear Filters</a>{% endif %}""")
        )
    )


"""

Preference filters

"""


class PreferenceFilter(django_filters.FilterSet):
    rank = django_filters.NumberFilter(lookup_expr='exact')

    project__identifier = django_filters.CharFilter(
        lookup_expr='icontains', label='Project ID')
    project__name = django_filters.CharFilter(
        lookup_expr='icontains', label='Project Name')
    project = django_filters.ModelMultipleChoiceFilter(queryset=unit_projects)

    student__student_id = django_filters.CharFilter(
        lookup_expr='contains', label='Student ID')
    student = django_filters.ModelMultipleChoiceFilter(queryset=unit_students)

    class Meta:
        model = models.ProjectPreference
        fields = ['rank']


class PreferenceFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        FloatingField('rank'),
        Div(
            Fieldset(
                'Students',
                Div(FloatingField('student__student_id'),
                    css_class='w-100'),
                Div(InlineField('student'),
                    css_class='w-100'),
                css_class='d-grid column-gap-3 flex-grow-1'
            ),
            Fieldset(
                'Projects',
                Div(
                    Div(FloatingField('project__identifier'),
                        css_class='flex-grow-1'),
                    Div(FloatingField('project__name'),
                        css_class='flex-grow-1'),
                    css_class='d-flex flex-wrap column-gap-3'
                ),
                Div(InlineField('project'),
                    css_class='w-100'),
                css_class='d-grid flex-grow-1'
            ),
            css_class='mb-3 d-flex flex-wrap flex-lg-nowrap gap-3 align-items-start'
        ),
        FormActions(
            Submit('submit', 'Filter'),
            HTML(
                """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit_preferences' unit.id %}">Clear Filters</a>{% endif %}""")
        )
    )


class PreferenceDistributionFilter(django_filters.FilterSet):
    identifier = django_filters.CharFilter(
        lookup_expr='icontains', label='Project ID')
    name = django_filters.CharFilter(lookup_expr='icontains', label='Name')
    project = django_filters.ModelMultipleChoiceFilter(queryset=unit_projects)

    class Meta:
        model = models.Project
        fields = ['identifier', 'name', 'min_students', 'max_students']


class PreferenceDistributionFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Fieldset(
            '',
            FloatingField('identifier'),
            Div(FloatingField('name'),
                css_class='flex-grow-1'),
            css_class='d-flex flex-wrap column-gap-3 align-items-center'
        ),
        Div(InlineField('project'), css_class='mb-3'),
        FormActions(
            Submit('submit', 'Filter'),
            HTML(
                """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit_preferences_distribution' unit.id %}">Clear Filters</a>{% endif %}""")
        )
    )


"""

Area filters

"""


class AreaFilter(ExistsMultipleChoiceFilterSet):
    name = django_filters.CharFilter(
        lookup_expr='icontains', label='Name')
    has_projects = ExistsMultipleChoiceFilter(
        field_name='projects', exists_label='Has Projects', not_exists_label='Doesn\'t Have Projects')
    has_students = ExistsMultipleChoiceFilter(
        field_name='students', exists_label='Has Students', not_exists_label='Doesn\'t Have Students')

    class Meta:
        model = models.Area
        fields = ['name']


class AreaFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Div(FloatingField('name'), css_class='w-100'),
        Div(
            InlineRadios('has_projects'),
            InlineRadios('has_students'),
            css_class='mb-3 d-flex flex-wrap column-gap-3 align-items-center'
        ),
        FormActions(
            Submit('submit', 'Filter'),
            HTML(
                """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit_areas' unit.id %}">Clear Filters</a>{% endif %}""")
        )
    )
