from django import forms
from django.db.models import Count

import django_filters

from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import FormActions, InlineField, InlineRadios, Accordion, AccordionGroup
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, Div
from crispy_bootstrap5.bootstrap5 import FloatingField

from core import models


def unit_projects(request):
    if request is None:
        return models.Projects.objects.none()
    pk_unit = request.resolver_match.kwargs.get('pk_unit')
    if not pk_unit:
        return models.Projects.objects.none()
    return models.Project.objects.all().filter(unit=pk_unit)


def unit_students(request):
    if request is None:
        return models.Student.objects.none()
    pk_unit = request.resolver_match.kwargs.get('pk_unit')
    if not pk_unit:
        return models.Student.objects.none()
    return models.Student.objects.all().filter(unit=pk_unit)


"""

Student Filters

"""


class StudentFilter(django_filters.FilterSet):
    SHOW_REGISTERED = 'REG'
    SHOW_NON_REGISTERED = 'NO_REG'
    REGISTERED_STUDENT_CHOICES = ((SHOW_REGISTERED, 'Registered Students'),
                                  (SHOW_NON_REGISTERED, 'Un-Registered Students'))
    SHOW_PREFS = 'PREFS'
    SHOW_NO_PREFS = 'NO_PREFS'
    PREFS_STUDENT_CHOICES = ((SHOW_PREFS, 'Submitted Preferences'),
                             (SHOW_NO_PREFS, 'Didn\'t Submit Preferences'))

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
        elif self.SHOW_REGISTERED in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})

    def filter_preferences(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        elif self.SHOW_PREFS in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})

    class Meta:
        model = models.Student
        fields = ['student_id']


class StudentAllocatedFilter(StudentFilter):
    SHOW_STUDENT_ALLOCATED = 'ALL'
    SHOW_STUDENT_NOT_ALLOCATED = 'NON_ALL'
    REGISTERED_STUDENT_CHOICES = ((SHOW_STUDENT_ALLOCATED, 'Allocated Students'),
                                  (SHOW_STUDENT_NOT_ALLOCATED, 'Unallocated Students'))

    allocated_project = django_filters.ModelMultipleChoiceFilter(
        queryset=unit_projects, label='Allocated Project')
    allocated_preference_rank = django_filters.NumberFilter(
        label='Allocated Preference')

    allocated = django_filters.MultipleChoiceFilter(
        field_name='allocated_project',
        label='', method='filter_allocated',
        choices=REGISTERED_STUDENT_CHOICES,
        widget=forms.CheckboxSelectMultiple(choices=REGISTERED_STUDENT_CHOICES))

    def filter_allocated(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        elif self.SHOW_STUDENT_ALLOCATED in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})


student_filter_form_layout_main = Fieldset(
    '',
    Div(FloatingField('student_id'), css_class='w-100'),
    Div(
        InlineRadios('registered'),
        InlineRadios('preferences'),
        css_class='mb-3 d-flex flex-wrap column-gap-3 align-items-center'
    ),
    css_class='mb-3 d-grid gap-1 align-items-center'
)


class StudentFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                student_filter_form_layout_main,
                FormActions(
                    Submit('submit', 'Filter'),
                    HTML(
                        """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-students' unit.id %}">Clear Filters</a>{% endif %}""")
                ),
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
                        """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-students' unit.id %}">Clear Filters</a>{% endif %}""")
                ),
            ),
        ),
    )


"""

Project Filters

"""


class ProjectFilter(django_filters.FilterSet):

    number = django_filters.CharFilter(lookup_expr='contains', label='Number')
    name = django_filters.CharFilter(lookup_expr='contains', label='Name')
    min_students = django_filters.NumberFilter(label='Min. Group Size')
    max_students = django_filters.NumberFilter(label='Max. Group Size')

    class Meta:
        model = models.Project
        fields = ['number', 'name', 'min_students', 'max_students']


class ProjectAllocatedFilter(ProjectFilter):
    SHOW_ALLOCATED = 'ALL'
    SHOW_NOT_ALLOCATED = 'NON_ALL'
    REGISTERED_STUDENT_CHOICES = ((SHOW_ALLOCATED, 'Allocated Projects'),
                                  (SHOW_NOT_ALLOCATED, 'Unallocated Projects'))

    num_allocated = django_filters.NumberFilter(
        field_name='allocated_students', label='Allocated Group Size', method='filter_num_allocated',)
    allocated = django_filters.MultipleChoiceFilter(
        field_name='allocated_students',
        label='', method='filter_allocated',
        choices=REGISTERED_STUDENT_CHOICES,
        widget=forms.CheckboxSelectMultiple(choices=REGISTERED_STUDENT_CHOICES))

    def filter_allocated(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        elif self.SHOW_ALLOCATED in value:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: False})
        else:
            lookup = '__'.join([name, 'isnull'])
            return queryset.filter(**{lookup: True})

    def filter_num_allocated(self, queryset, name, value):
        return queryset.annotate(allocated_student_count=Count(
            'allocated_students')).filter(allocated_student_count=value)


project_filter_form_layout_main = Fieldset(
    '',
    FloatingField('number'),
    FloatingField('name'),
    FloatingField('min_students'),
    FloatingField('max_students'),
    css_class='d-flex flex-wrap column-gap-3 align-items-center'
)


class ProjectFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                project_filter_form_layout_main,
                FormActions(
                    Submit('submit', 'Filter'),
                    HTML(
                        """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-projects' unit.id %}">Clear Filters</a>{% endif %}""")
                ),
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
                    'Filter by Allocation',
                    Div(FloatingField('num_allocated'), css_class='w-100'),
                    InlineRadios('allocated'),
                    css_class='d-grid column-gap-3'
                ),
                FormActions(
                    Submit('submit', 'Filter'),
                    HTML(
                        """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-projects' unit.id %}">Clear Filters</a>{% endif %}""")
                ),
            ),
        ),
    )


"""

Preference filters

"""


class PreferenceFilter(django_filters.FilterSet):
    rank = django_filters.NumberFilter(lookup_expr='exact')

    project__number = django_filters.CharFilter(
        lookup_expr='contains', label='Project Number')
    project__name = django_filters.CharFilter(
        lookup_expr='contains', label='Project Name')
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
        Accordion(
            AccordionGroup(
                'Filters',
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
                            FloatingField('project__number'),
                            Div(FloatingField('project__name'),
                                css_class='flex-grow-1'),
                            css_class='d-flex flex-wrap column-gap-3'
                        ),
                        Div(InlineField('project'),
                            css_class='w-100'),
                        css_class='d-grid flex-grow-1'
                    ),
                    css_class='mb-3 d-flex flex-md-nowrap flex-sm-wrap gap-3 align-items-start'
                ),
                FormActions(
                    Submit('submit', 'Filter'),
                    HTML(
                        """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-preferences' unit.id %}">Clear Filters</a>{% endif %}""")
                ),
            ),
        ),
    )


class PreferenceDistributionFilter(django_filters.FilterSet):
    number = django_filters.CharFilter(
        lookup_expr='contains', label='Project Number')
    name = django_filters.CharFilter(lookup_expr='contains', label='Name')
    project = django_filters.ModelMultipleChoiceFilter(queryset=unit_projects)

    class Meta:
        model = models.Project
        fields = ['number', 'name', 'min_students', 'max_students']


class PreferenceDistributionFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        Accordion(
            AccordionGroup(
                'Filters',
                Fieldset(
                    '',
                    FloatingField('number'),
                    Div(FloatingField('name'),
                        css_class='flex-grow-1'),
                    Div(InlineField('project'),
                        css_class='flex-grow-1'),
                    css_class='mb-3 d-flex flex-wrap column-gap-3 align-items-center'
                ),
                FormActions(
                    Submit('submit', 'Filter'),
                    HTML(
                        """{% if has_filter %}<a class="btn" href="{%  url 'manager:unit-preferences-distribution' unit.id %}">Clear Filters</a>{% endif %}""")
                )
            ),
        ),
    )
