from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import FormActions
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, Div
from crispy_bootstrap5.bootstrap5 import FloatingField

import django_filters

from . import models


class ExistsMultipleChoiceMixin:
    SHOW_EXISTS = 'EXISTS'
    SHOW_NOT_EXISTS = 'N_EXISTS'


class ExistsMultipleChoiceFilter(ExistsMultipleChoiceMixin, django_filters.MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        self.exists_label = kwargs.pop('exists_label', None)
        self.not_exists_label = kwargs.pop('not_exists_label', None)

        super().__init__(*args, **kwargs)

        self.extra['choices'] = (
            (self.SHOW_EXISTS, self.exists_label), (self.SHOW_NOT_EXISTS, self.not_exists_label))
        self.extra['widget'] = forms.CheckboxSelectMultiple(
            choices=self.extra['choices'])

        self._label = ''

        self.method = 'filter_exists'


class ExistsMultipleChoiceFilterSet(ExistsMultipleChoiceMixin, django_filters.FilterSet):
    def filter_exists(self, queryset, name, value):
        if len(value) == 2:
            return queryset
        lookup = '__'.join([name, 'isnull'])
        return queryset.filter(**{lookup: False if self.SHOW_EXISTS in value else True}).distinct()


"""

Unit filters

"""


class CustomBooleanWidget(django_filters.widgets.BooleanWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = (('', '-----'), ('true', 'Yes'), ('false', 'No'))


class UnitFilter(ExistsMultipleChoiceFilterSet):
    code = django_filters.CharFilter(
        lookup_expr='icontains', label='Code')
    name = django_filters.CharFilter(
        lookup_expr='icontains', label='Name')
    year = django_filters.CharFilter(
        lookup_expr='icontains', label='Year')
    semester = django_filters.CharFilter(
        lookup_expr='icontains', label='Semester')
    is_active = django_filters.BooleanFilter(
        widget=CustomBooleanWidget, label='Is Active?')

    class Meta:
        model = models.Unit
        fields = ['code', 'name', 'year', 'semester']


class ManagerUnitFilter(UnitFilter):
    is_active = django_filters.BooleanFilter(
        widget=CustomBooleanWidget, label='Is Active?')


unit_filter_form_layout_main = Layout(
    Fieldset(
        '',
        Div(
            Div(FloatingField('code'), css_class='flex-grow-1'),
            Div(FloatingField('name'), css_class='flex-grow-1'),
            css_class='d-flex flex-wrap column-gap-3 align-items-center'
        ),
        Div(
            Div(FloatingField('year'), css_class='flex-grow-1'),
            Div(FloatingField('semester'), css_class='flex-grow-1'),
            css_class='d-flex flex-wrap column-gap-3 align-items-center'
        ),
        css_class='d-grid gap-1 align-items-center'
    )
)
unit_filter_form_layout_actions = FormActions(
    Submit('submit', 'Filter'),
    HTML(
        """{% if has_filter %}<a class="btn" href="{%  url 'manager:index' %}">Clear Filters</a>{% endif %}""")
)


class UnitFilterFormHelper(FormHelper):
    form_method = 'GET'
    layout = Layout(
        unit_filter_form_layout_main,
        unit_filter_form_layout_actions
    )


class ManagerUnitFilterFormHelper(UnitFilterFormHelper):
    form_method = 'GET'
    layout = Layout(
        unit_filter_form_layout_main,
        'is_active',
        unit_filter_form_layout_actions,
    )
