import datetime
from django import forms

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div
from crispy_bootstrap5.bootstrap5 import FloatingField

import csv
from io import StringIO

from core import models


class SplitDateTimeWidget(forms.SplitDateTimeWidget):
    def __init__(self, attrs=None, date_format=None, time_format=None, date_attrs=None, time_attrs=None):
        date_attrs = date_attrs if date_attrs != None else {}
        date_attrs = {**date_attrs, **{'type': 'date'}}
        time_attrs = time_attrs if time_attrs != None else {}
        time_attrs = {**time_attrs, **{'type': 'time'}}
        return super().__init__(attrs=attrs, date_format=date_format, time_format=time_format, date_attrs=date_attrs, time_attrs=time_attrs)


class SplitDateTimeField(forms.SplitDateTimeField):
    widget = SplitDateTimeWidget


class UnitForm(forms.ModelForm):
    preference_submission_start = SplitDateTimeField(
        initial=datetime.datetime.now, required=False)
    preference_submission_end = SplitDateTimeField(
        initial=datetime.datetime.now, required=False)

    # ADD FILE UPLOAD FOR STUDENTS & PROJECTS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                FloatingField('code'),
                FloatingField('name'),
                FloatingField('year'),
                FloatingField('semester'),
                Fieldset('Preference Submission Timeframe',
                         Div(
                             Div('preference_submission_start',
                                 css_class='col preference_submission_timeframe'),
                             Div('preference_submission_end',
                                 css_class='col preference_submission_timeframe'),
                             css_class='row'
                         )
                         ),
                'minimum_preference_limit',
            ),
            FormActions(
                Submit('submit', 'Save', css_class='btn btn-primary'),
            )
        )

    class Meta:
        model = models.Unit
        fields = ['code', 'name', 'year', 'semester', 'preference_submission_start',
                  'preference_submission_end', 'minimum_preference_limit']


class StudentForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                FloatingField('student_id'),
            ),
            FormActions(
                Submit('submit', 'Save', css_class='btn btn-primary'),
            )
        )

    class Meta:
        model = models.EnrolledStudent
        fields = ['student_id']


class StudentListForm(forms.Form):
    file = forms.FileField(label='')
    # file.widget = forms.ClearableFileInput(
    #     attrs={'enctype': 'multipart/form-data', })
    list_override = forms.BooleanField(
        label='Replace current students', required=False)
    column_name = forms.CharField(
        label='Name of the column for the Student ID in the uploaded file.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                'file',
                'list_override',
                FloatingField('column_name')
            ),
            FormActions(
                Submit('submit', 'Save', css_class='btn btn-primary'),
            )
        )

    def clean(self):
        file = self.cleaned_data.get('file').read().decode('utf-8')
        csv_data = csv.DictReader(StringIO(file), delimiter=',')

        try:
            next(csv_data)[self.cleaned_data.get('column_name')]
        except KeyError:
            raise forms.ValidationError(
                {'column_name': 'Please enter a valid column name for this file.'})

        return super().clean()
