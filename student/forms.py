from django import forms
from django.forms import BaseFormSet

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit

from core import models


class PreferenceForm(forms.ModelForm):
    project_id = forms.IntegerField(widget=forms.HiddenInput())
    rank = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.empty_permitted = False

        self.fields['rank'].widget.attrs['readonly'] = True
        self.fields['project_id'].widget.attrs['readonly'] = True

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                'rank',
                'project_id',
            )
        )

    class Meta:
        model = models.ProjectPreference
        fields = ['rank']


class PreferenceFormSet(BaseFormSet):
    pass


class PreferenceFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.add_input(Submit('submit', 'Save Preferences'))
        self.template = 'bootstrap5/table_inline_formset.html'
