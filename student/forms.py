from typing import Any, Optional
from django import forms
from django.forms import BaseFormSet, formset_factory

from crispy_forms.bootstrap import FormActions, InlineField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Button
from crispy_bootstrap5.bootstrap5 import FloatingField


from core import models


class PreferenceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        unit_id = kwargs.pop('unit_id')

        super().__init__(*args, **kwargs)

        self.fields['project'].queryset = models.Project.objects.filter(
            unit_id=unit_id)

        self.empty_permitted = False

        self.helper = FormHelper()
        self.helper.layout = Layout(
            InlineField('project')
        )

    class Meta:
        model = models.ProjectPreference
        fields = ['project']


class PreferenceFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        # Ensure each project is only added once
        projects = []
        for form in self.forms:
            if form.cleaned_data.get('project') in projects:
                form.add_error(
                    'project', 'Each project can only be added to your preferences once.')
            else:
                projects.append(form.cleaned_data.get('project'))


class PreferenceFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.add_input(Submit('submit', 'Save Preferences'))
        self.add_input(Button('add_preference', 'Add Another Preference',
                       css_class='btn btn-secondary'))
        self.template = 'student/table_inline_formset.html'
