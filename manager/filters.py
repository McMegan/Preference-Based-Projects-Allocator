from distutils.util import strtobool

from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

import django_filters

from crispy_forms.bootstrap import FormActions, InlineField, InlineRadios
from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.layout import Layout, Fieldset, Submit, Field, Div, HTML

from core import models


class ProjectFilter(django_filters.FilterSet):
    number = django_filters.CharFilter(lookup_expr='contains', label='Number')
    name = django_filters.CharFilter(lookup_expr='contains', label='Name')
    min_students = django_filters.NumberFilter(label='Minimum Group Size')
    max_students = django_filters.NumberFilter(label='Maximum Group Size')

    class Meta:
        model = models.Project
        fields = ['number', 'name', 'min_students', 'max_students']


class ProjectFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Fieldset(
            '',
            InlineField('number'),
            InlineField('name'),
            InlineField('min_students'),
            InlineField('max_students'),
            css_class='mb-3 d-flex flex-wrap gap-2'
        ),
        FormActions(
            Submit('submit', 'Filter Projects'),
            HTML("""{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-projects' unit.id %}">Clear Filters</a>{% endif %}""")
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


class StudentFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Fieldset(
            '',
            InlineField('student_id', css_class='mb-3'),
            InlineRadios('registered'),
            InlineRadios('preferences'),
            css_class='mb-3 d-flex flex-wrap column-gap-4 align-items-center'
        ),
        FormActions(
            Submit('submit', 'Filter Students'),
            HTML("""{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-students' unit.id %}">Clear Filters</a>{% endif %}""")
        ),
    )
