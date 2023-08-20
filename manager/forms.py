from django import forms

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField

import csv
from io import StringIO
import os

from core import models


def valid_csv_file(file):
    if os.path.splitext(file.name)[1].casefold() != '.csv'.casefold():
        raise forms.ValidationError({'file': 'File must be CSV.'})


def column_exists_in_csv(file, field_name, column_name):
    file.seek(0)
    file = file.read().decode('utf-8-sig')
    csv_data = csv.DictReader(StringIO(file), delimiter=',')

    try:
        next(csv_data)[column_name]
    except KeyError:
        raise forms.ValidationError(
            {field_name: 'Please enter a valid column name for this file.'})


class SplitDateTimeWidget(forms.SplitDateTimeWidget):
    def __init__(self, attrs=None, date_format=None, time_format=None, date_attrs=None, time_attrs=None):
        date_attrs = date_attrs if date_attrs != None else {}
        date_attrs = {**date_attrs, **{'type': 'date'}}
        time_attrs = time_attrs if time_attrs != None else {}
        time_attrs = {**time_attrs, **{'type': 'time'}}
        return super().__init__(attrs=attrs, date_format=date_format, time_format=time_format, date_attrs=date_attrs, time_attrs=time_attrs)


class SplitDateTimeField(forms.SplitDateTimeField):
    widget = SplitDateTimeWidget


unit_form_layout_main = Layout(
    FloatingField('code'),
    FloatingField('name'),
    FloatingField('year'),
    FloatingField('semester'),
)
unit_form_layout_allocator = Layout(
    Fieldset(
        'Allocator Settings',
        Div(
            Div('preference_submission_start',
                css_class='col preference_submission_timeframe'),
            Div('preference_submission_end',
                css_class='col preference_submission_timeframe'),
            css_class='row'
        ),
        'minimum_preference_limit',
    ),
)


class CreateUnitForm(forms.ModelForm):
    preference_submission_start = SplitDateTimeField(required=False)
    preference_submission_end = SplitDateTimeField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            unit_form_layout_main,
            FormActions(
                Submit('submit', 'Save Unit', css_class='btn btn-primary'),
            )
        )

    class Meta:
        model = models.Unit
        fields = ['code', 'name', 'year', 'semester', 'preference_submission_start',
                  'preference_submission_end', 'minimum_preference_limit']


class UpdateUnitForm(CreateUnitForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            unit_form_layout_main,
            unit_form_layout_allocator,
            FormActions(
                Submit('submit', 'Save Unit', css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'manager:unit-delete' unit.id %}" class="btn btn-danger">Delete Unit</a>""")
            )
        )


# Students
class StudentForm(forms.ModelForm):
    """
        Form for adding a single student to a unit
    """

    def __init__(self, *args, **kwargs):
        self.pk_unit = kwargs.pop('pk_unit', None)

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                FloatingField('student_id'),
            ),
            FormActions(
                Submit('submit', 'Add Student to Unit',
                       css_class='btn btn-primary'),
            )
        )

    def clean(self):
        student_id = self.cleaned_data.get('student_id')
        if models.EnrolledStudent.objects.filter(student_id=student_id, unit_id=self.pk_unit).exists():
            raise forms.ValidationError(
                {'student_id': 'A student with that ID is already enrolled in this unit.'})
        return super().clean()

    class Meta:
        model = models.EnrolledStudent
        fields = ['student_id']


class StudentListForm(forms.Form):
    """
        Form for uploading a list of students
    """
    file = forms.FileField(label='')
    list_override = forms.BooleanField(
        label='Replace current students', required=False)
    student_id_column = forms.CharField(
        label='Name of the column for the Student ID in the uploaded file.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['student_id_column'].initial = 'user_id'

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                'file',
                'list_override',
                FloatingField('student_id_column')
            ),
            FormActions(
                Submit('submit', 'Upload List of Students to Unit',
                       css_class='btn btn-primary'),
            )
        )

    def clean(self):
        valid_csv_file(self.cleaned_data.get('file'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'student_id_column',
                             self.cleaned_data.get('student_id_column'))
        return super().clean()


class StudentListClearForm(forms.Form):
    """
        Form for clearing the list of students
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<p>Are you sure you want to remove all students from this unit?</p>'),
            FormActions(
                Submit('submit', 'Confirm', css_class='btn btn-danger'),
            )
        )


# Projects
project_form_layout_main = Layout(
    Fieldset(
        '',
        FloatingField('number'),
        FloatingField('name'),
        FloatingField('min_students'),
        FloatingField('max_students'),
        'description'
    ),
)


class ProjectForm(forms.ModelForm):
    """
        Form for adding a single project to a unit
    """

    def __init__(self, *args, **kwargs):
        self.pk_unit = kwargs.pop('pk_unit', None)

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            project_form_layout_main,
            FormActions(
                Submit('submit', 'Add Project to Unit',
                       css_class='btn btn-primary'),
            )
        )

    def clean(self):
        number = self.cleaned_data.get('number')
        if models.Project.objects.filter(number=number, unit_id=self.pk_unit).exists():
            raise forms.ValidationError(
                {'number': 'A project with that number is already included in this unit.'})
        return super().clean()

    class Meta:
        model = models.Project
        fields = ['number', 'name', 'description',
                  'min_students', 'max_students']


class ProjectUpdateForm(ProjectForm):
    """
        Form for updating a project in a unit
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            project_form_layout_main,
            FormActions(
                Submit('submit', 'Save Project',
                       css_class='btn btn-primary'),
            )
        )


class ProjectListForm(forms.Form):
    """
        Form for uploading a list of projects
    """
    file = forms.FileField(label='')
    list_override = forms.BooleanField(
        label='Replace current projects', required=False)
    number_column = forms.CharField(
        label='Name of the column for the Project Number in the uploaded file.')
    name_column = forms.CharField(
        label='Name of the column for the Project Name in the uploaded file.')
    min_students_column = forms.CharField(
        label='Name of the column for the Minimum Students in the uploaded file.')
    max_students_column = forms.CharField(
        label='Name of the column for the Maximum Students in the uploaded file.')

    description_column = forms.CharField(
        label='Name of the column for the Project Description in the uploaded file. Leave blank if none.', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial['number_column'] = 'number'
        self.initial['name_column'] = 'name'
        self.initial['min_students_column'] = 'min_students'
        self.initial['max_students_column'] = 'max_students'

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                'file',
                'list_override',
                FloatingField('number_column'),
                FloatingField('name_column'),
                FloatingField('min_students_column'),
                FloatingField('max_students_column'),
                FloatingField('description_column')
            ),
            FormActions(
                Submit('submit', 'Upload List of Projects to Unit',
                       css_class='btn btn-primary'),
            )
        )

    def clean(self):
        valid_csv_file(self.cleaned_data.get('file'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'number_column',
                             self.cleaned_data.get('number_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'name_column',
                             self.cleaned_data.get('name_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'min_students_column',
                             self.cleaned_data.get('min_students_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'max_students_column',
                             self.cleaned_data.get('max_students_column'))

        if self.cleaned_data.get('description_column') != '':
            column_exists_in_csv(self.cleaned_data.get('file'), 'max_students_column',
                                 self.cleaned_data.get('max_students_column'))

        return super().clean()


class StartAllocationForm(forms.Form):
    """
        Form for starting the allocation process
    """

    def __init__(self, *args, **kwargs):
        self.pk_unit = kwargs.pop('pk_unit', None)
        self.unit = kwargs.pop('unit', None)

        super().__init__(*args, **kwargs)

        submit_text = 'Start Allocation'
        submit_btn_colour = 'btn-primary'
        warning = ''
        if self.unit.is_allocated():
            submit_text = 'Override Allocation'
            submit_btn_colour = 'btn-danger'
            warning = """
                <div class="alert alert-danger" role="alert">
                    This unit has already been allocated, allocating again will override the current allocation.
                </div>
            """

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML(warning),
            FormActions(
                Submit('submit', submit_text,
                       css_class=f'btn {submit_btn_colour}'),
            ),
        )
