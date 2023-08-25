from distutils.util import strtobool

from django import forms
from django.db.models import Count, Sum, F, Avg, Min, Max

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

import django_filters

from crispy_forms.bootstrap import FormActions, InlineField, InlineRadios, Accordion, AccordionGroup
from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.layout import Layout, Fieldset, Submit, Field, Div, HTML

from core import models

SHOW_ALLOCATED = 'ALL'
SHOW_NOT_ALLOCATED = 'NON_ALL'
REGISTERED_STUDENT_CHOICES = ((SHOW_ALLOCATED, 'Allocated Projects'),
                              (SHOW_NOT_ALLOCATED, 'Unallocated Projects'))


class ProjectFilter(django_filters.FilterSet):
    number = django_filters.CharFilter(lookup_expr='contains', label='Number')
    name = django_filters.CharFilter(lookup_expr='contains', label='Name')
    min_students = django_filters.NumberFilter(label='Min. Group Size')
    max_students = django_filters.NumberFilter(label='Max. Group Size')

    class Meta:
        model = models.Project
        fields = ['number', 'name', 'min_students', 'max_students']


class ProjectAllocatedFilter(ProjectFilter):
    num_allocated = django_filters.NumberFilter(
        field_name='assigned_students', label='Allocated Group Size', method='filter_num_allocated',)
    allocated = django_filters.MultipleChoiceFilter(
        field_name='assigned_students',
        label='', method='filter_allocated',
        choices=REGISTERED_STUDENT_CHOICES,
        widget=forms.CheckboxSelectMultiple(choices=REGISTERED_STUDENT_CHOICES))

    def filter_allocated(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        elif SHOW_ALLOCATED in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})

    def filter_num_allocated(self, queryset, name, value):
        return queryset.annotate(allocated_student_count=Count(
            'assigned_students')).filter(allocated_student_count=value)


project_filter_form_layout_main = Fieldset(
    '',
    InlineField('number'),
    InlineField('name'),
    InlineField('min_students'),
    InlineField('max_students'),
    css_class='mb-3 d-flex flex-wrap column-gap-4 align-items-center'
)
project_filter_form_layout_actions = FormActions(
    Submit('submit', 'Filter Projects'),
    HTML("""{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-projects' unit.id %}">Clear Filters</a>{% endif %}""")
)


class ProjectFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                project_filter_form_layout_main,
                project_filter_form_layout_actions,
            ),
        ),
    )


class ProjectAllocatedFilterFormHelper(ProjectFilterFormHelper):
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                project_filter_form_layout_main,
                Fieldset(
                    '',
                    InlineField('num_allocated', css_class='mb-3'),
                    InlineRadios('allocated'),
                    css_class='mb-3 d-flex flex-wrap column-gap-4 align-items-center'
                ),
                project_filter_form_layout_actions,
            ),
        ),
    )


SHOW_REGISTERED = 'REG'
SHOW_NON_REGISTERED = 'NO_REG'
REGISTERED_STUDENT_CHOICES = ((SHOW_REGISTERED, 'Registered Students'),
                              (SHOW_NON_REGISTERED, 'Un-Registered Students'))
SHOW_PREFS = 'PREFS'
SHOW_NO_PREFS = 'NO_PREFS'
PREFS_STUDENT_CHOICES = ((SHOW_PREFS, 'Submitted Preferences'),
                         (SHOW_NO_PREFS, 'Didn\'t Submit Preferences'))


class StudentFilter(django_filters.FilterSet):
    student_id = django_filters.CharFilter(
        lookup_expr='contains', label='Student ID')
    registered = django_filters.MultipleChoiceFilter(
        field_name='user',
        label='', method='filter_registered',
        choices=REGISTERED_STUDENT_CHOICES,
        widget=forms.CheckboxSelectMultiple(choices=REGISTERED_STUDENT_CHOICES))
    preferences = django_filters.MultipleChoiceFilter(
        field_name='project_preferences',
        label='', method='filter_preferences',
        choices=PREFS_STUDENT_CHOICES,
        widget=forms.CheckboxSelectMultiple(choices=PREFS_STUDENT_CHOICES))

    def filter_registered(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        elif SHOW_REGISTERED in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})

    def filter_preferences(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        elif SHOW_PREFS in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})

    class Meta:
        model = models.EnrolledStudent
        fields = ['student_id']


def projects(request):
    if request is None:
        return models.Projects.objects.none()
    pk_unit = request.resolver_match.kwargs.get('pk_unit')
    if not pk_unit:
        return models.Projects.objects.none()
    return models.Project.objects.all().filter(unit=pk_unit)


SHOW_STUDENT_ALLOCATED = 'ALL'
SHOW_STUDENT_NOT_ALLOCATED = 'NON_ALL'
REGISTERED_STUDENT_CHOICES = ((SHOW_STUDENT_ALLOCATED, 'Allocated Students'),
                              (SHOW_NOT_ALLOCATED, 'Unallocated Students'))


class StudentAllocatedFilter(StudentFilter):
    assigned_project = django_filters.ModelMultipleChoiceFilter(
        queryset=projects, label='Allocated Project')
    assigned_preference_rank = django_filters.NumberFilter(
        label='Allocated Preference')

    allocated = django_filters.MultipleChoiceFilter(
        field_name='assigned_project',
        label='', method='filter_allocated',
        choices=REGISTERED_STUDENT_CHOICES,
        widget=forms.CheckboxSelectMultiple(choices=REGISTERED_STUDENT_CHOICES))

    def filter_allocated(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        elif SHOW_ALLOCATED in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})


student_filter_form_layout_main = Fieldset(
    '',
    InlineField('student_id', css_class='mb-3'),
    InlineRadios('registered'),
    InlineRadios('preferences'),
    css_class='mb-3 d-flex flex-wrap column-gap-4 align-items-center'
)
student_filter_form_layout_actions = FormActions(
    Submit('submit', 'Filter Students'),
    HTML("""{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-students' unit.id %}">Clear Filters</a>{% endif %}""")
)


class StudentFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                student_filter_form_layout_main,
                student_filter_form_layout_actions,
            ),
        ),
    )


class StudentAllocatedFilterFormHelper(StudentFilterFormHelper):
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                student_filter_form_layout_main,
                Fieldset(
                    '',
                    'assigned_project',
                    InlineField('assigned_preference_rank', css_class='mb-3'),
                    InlineRadios('allocated'),
                    css_class='mb-3 d-flex flex-wrap column-gap-4 align-items-center'
                ),
                student_filter_form_layout_actions,
            ),
        ),
    )


class PreferenceFilter(django_filters.FilterSet):
    number = django_filters.CharFilter(
        lookup_expr='contains', label='Project Number')
    name = django_filters.CharFilter(lookup_expr='contains', label='Name')

    class Meta:
        model = models.Project
        fields = ['number', 'name', 'min_students', 'max_students']


class PreferenceFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                Fieldset(
                    '',
                    InlineField('number'),
                    InlineField('name'),
                    css_class='mb-3 d-flex flex-wrap column-gap-4 align-items-center'
                ),
                FormActions(
                    Submit('submit', 'Filter'),
                    HTML(
                        """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-preferences' unit.id %}">Clear Filters</a>{% endif %}""")
                )
            ),
        ),
    )
