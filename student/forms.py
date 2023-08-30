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
    def full_clean(self):
        super().full_clean()
        for error in self._non_form_errors.as_data():
            if error.code == 'too_many_forms':
                error.message = f'Please nominate at most {self.max_num} preferences.'
            if error.code == 'too_few_forms':
                error.message = f'Please nominate at least {self.min_num} preferences.'

    def clean(self):
        """ Checks that all projects are listed only once & that submitted ranks are valid. """
        if any(self.errors):
            return
        projects = []
        ranks = []
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            """ Validate project ids """
            project_id = form.cleaned_data.get('project_id')
            if project_id in projects:
                raise forms.ValidationError(
                    'You can only choose each project once.')
            projects.append(project_id)
            """ Validate ranks """
            rank = form.cleaned_data.get('rank')
            if rank in ranks:
                raise forms.ValidationError(
                    'Each preference rank must be unique.')
            ranks.append(rank)
        ranks_sorted = sorted(ranks)
        if ranks_sorted[0] != 1:
            raise forms.ValidationError(
                'Your first preference rank must be 1.')
        if not all(ranks_sorted[i] == ranks_sorted[i-1] +
                   1 for i in range(1, len(ranks_sorted))):
            raise forms.ValidationError(
                'Submitted preferences must be consecutive.')


class PreferenceFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.add_input(Submit('submit', 'Save Preferences'))
        self.template = 'bootstrap5/table_inline_formset.html'
