from django import forms
from django.forms import BaseFormSet, formset_factory

from crispy_forms.bootstrap import FormActions, InlineField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField


from core import models


class PreferenceForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            # FloatingField()
            'project'
        )

    class Meta:
        model = models.ProjectPreference
        fields = ['project', 'rank']


PreferenceFormset = formset_factory(PreferenceForm, extra=1)


class PreferenceFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.layout = Layout(
            Fieldset(
                '',
                HTML('<div>{{forloop.counter}}</div>'),
                'project',
                css_class='d-flex gap-3 align-items-center'
            ),
        )
        self.add_input(Submit('submit', 'Save'))
