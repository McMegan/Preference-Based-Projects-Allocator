import csv
from io import StringIO
import os

from django import forms
from django.db.models import Q, ExpressionWrapper, BooleanField

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField

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


class UnitKwargMixin:
    def __init__(self, *args, **kwargs):
        self.unit = kwargs.pop('unit', None)
        self.disabled = kwargs.pop('disabled', None)

        if not self.disabled:
            self.disabled = self.unit.is_allocating if self.unit else self.disabled

        super().__init__(*args, **kwargs)

        self.init_fields()

        if self.disabled:
            for field_name in self.fields:
                field = self.fields[field_name]
                field.disabled = True

        self.helper = FormHelper()
        self.submit_button = Submit('submit', self.submit_label if hasattr(
            self, 'submit_label') else 'Submit', css_class='btn ' + self.submit_button_variant if hasattr(self, 'submit_button_variant') else 'btn-primary', disabled=self.disabled)
        self.form_actions = FormActions(self.submit_button)

        self.helper.layout = Layout(self.form_layout, self.form_actions) if hasattr(
            self, 'form_layout') and self.form_layout else Layout(self.form_actions)

    def init_fields(self):
        pass


class DeleteForm(UnitKwargMixin, forms.Form):
    """

    Generic delete form

    """
    submit_button_variant = 'btn-danger'

    def __init__(self, *args, **kwargs):
        self.submit_label = kwargs.pop('submit_label', 'Yes, Delete')
        self.form_message = kwargs.pop('form_message', None)
        if self.form_message:
            self.form_layout = HTML(self.form_message)

        super().__init__(*args, **kwargs)


"""

General unit forms

"""

unit_form_layout_main = Layout(
    FloatingField('code'),
    FloatingField('name'),
    FloatingField('year'),
    FloatingField('semester'),
    'is_active',
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
        Div(
            Div('minimum_preference_limit',
                css_class='col'),
            Div('maximum_preference_limit',
                css_class='col'),
            css_class='row'
        ),
    ),
)


class UnitCreateForm(forms.ModelForm):
    is_active = forms.BooleanField(
        label='Unit is current/active', required=False, help_text='If this is un-checked students will be unabled to access the unit.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['code'].label = 'Unit Code'
        self.fields['name'].label = 'Unit Name'

        self.helper = FormHelper()
        self.helper.layout = Layout(
            unit_form_layout_main,
            FormActions(
                Submit('submit', 'Save Unit', css_class='btn btn-primary'),
            )
        )

    class Meta:
        model = models.Unit
        fields = ['code', 'name', 'year', 'semester', 'is_active']


class UnitUpdateForm(UnitKwargMixin, UnitCreateForm):
    """
        Form for updating a unit
    """
    submit_label = 'Save Unit'
    form_layout = Layout(
        unit_form_layout_main,
        unit_form_layout_allocator,
        'limit_by_major',
    )

    preference_submission_start = SplitDateTimeField(required=False)
    preference_submission_end = SplitDateTimeField(required=False)

    limit_by_major = forms.BooleanField(
        label='Limit project preference selection by major/area', required=False, help_text='This will limit each students project preference options to those which match the students area. If a student has no area, all projects will be displayed. If a project has no area, it will be displayed to all students.')

    class Meta(UnitCreateForm.Meta):
        fields = ['code', 'name', 'year', 'semester', 'preference_submission_start',
                  'preference_submission_end', 'minimum_preference_limit', 'maximum_preference_limit', 'is_active', 'limit_by_major']


"""

Student forms 

"""


class StudentForm(UnitKwargMixin, forms.ModelForm):
    """
        Form for adding a single student to a unit
    """
    submit_label = 'Add Student to Unit'
    form_layout = Layout(
        FloatingField('student_id'),
        'area',
    )

    def init_fields(self):
        self.fields['area'] = forms.ModelMultipleChoiceField(
            queryset=self.unit.areas, required=False, help_text='You must add an area to the unit before you can select it for a student. To deselect an area cmd/ctrl + click on the area you wish to deselect.')

    def clean(self):
        student_id = self.cleaned_data.get('student_id')
        if self.unit.students.filter(student_id=student_id).exists():
            raise forms.ValidationError(
                {'student_id': 'A student with that ID is already enrolled in this unit.'})
        return super().clean()

    class Meta:
        model = models.Student
        fields = ['student_id']


class StudentListForm(UnitKwargMixin, forms.Form):
    """
        Form for uploading a list of students
    """
    submit_label = 'Upload List of Students to Unit'
    form_layout = Layout(
        'file',
        'list_override',
        FloatingField('student_id_column'),
        FloatingField('area_column'),
    )

    file = forms.FileField(label='')
    list_override = forms.BooleanField(
        label='Replace current students', required=False)
    student_id_column = forms.CharField(
        label='Student ID Column Name')

    area_column = forms.CharField(
        label='Project Area Column Name', help_text='Leave blank if none. Multiple areas for a single project should be seperated using a semi-colon (;).', required=False)

    def init_fields(self):
        self.fields['student_id_column'].initial = 'user_id'

    def clean(self):
        valid_csv_file(self.cleaned_data.get('file'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'student_id_column',
                             self.cleaned_data.get('student_id_column'))

        if self.cleaned_data.get('area_column') != '':
            column_exists_in_csv(self.cleaned_data.get('file'), 'area_column',
                                 self.cleaned_data.get('area_column'))

        return super().clean()


class AllocatedProjectChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{str(obj)}    (Current Group Size = {obj.allocated_students.count()})'


class StudentUpdateForm(UnitKwargMixin, forms.ModelForm):
    """
        Form for updating a student in a unit
    """
    submit_label = 'Save Student'
    form_layout = Layout('area')

    def init_fields(self):
        self.fields['area'] = forms.ModelMultipleChoiceField(
            queryset=self.unit.areas, required=False, help_text='You must add an area to the unit before you can select it for a student. To deselect an area cmd/ctrl + click on the area you wish to deselect.')

    class Meta:
        model = models.Student
        fields = ['area']


class StudentAllocatedUpdateForm(StudentUpdateForm):
    """
        Form for updating a student in a unit that has been allocated
    """
    form_layout = Layout(
        FloatingField('allocated_project',
                      css_class='my-3'),
        'area'
    )

    def init_fields(self):
        super().init_fields()
        self.fields['allocated_project'] = AllocatedProjectChoiceField(
            queryset=self.unit.projects.prefetch_related('allocated_students'), required=False, label='Allocated Project')

    class Meta(StudentUpdateForm.Meta):
        fields = ['allocated_project', 'area']


"""

Project forms

"""
project_form_layout_main = Layout(
    Fieldset(
        '',
        FloatingField('identifier'),
        FloatingField('name'),
        FloatingField('min_students'),
        FloatingField('max_students'),
        'description',
        'area'
    ),
)


class ProjectForm(UnitKwargMixin, forms.ModelForm):
    """
        Form for adding a single project to a unit
    """
    submit_label = 'Add Project to Unit'
    form_layout = Layout(project_form_layout_main)

    def init_fields(self):
        self.fields['identifier'].label = 'ID'
        self.fields['area'] = forms.ModelMultipleChoiceField(
            queryset=self.unit.areas, required=False, help_text='You must add an area to the unit before you can select it for a project. To deselect an area cmd/ctrl + click on the area you wish to deselect.')

    def clean(self):
        identifier = self.cleaned_data.get('identifier')
        if self.unit.projects.filter(identifier=identifier).exists():
            raise forms.ValidationError(
                {'identifier': 'A project with that ID is already included in this unit.'})
        return super().clean()

    class Meta:
        model = models.Project
        fields = ['identifier', 'name', 'description',
                  'min_students', 'max_students', 'area']


class ProjectUpdateForm(ProjectForm):
    """
        Form for updating a project in a unit
    """
    submit_label = 'Save Project'
    form_layout = Layout(project_form_layout_main)

    def init_fields(self):
        super().init_fields()
        self.fields['area'] = forms.ModelMultipleChoiceField(
            queryset=self.instance.unit.areas, required=False, help_text='You must add an area to the unit before you can select it for a project. To deselect an area cmd/ctrl + click on the area you wish to deselect.')

    def clean(self):
        return super(forms.ModelForm, self).clean()


class ProjectAllocatedUpdateForm(ProjectUpdateForm):
    """
        Form for updating a project in a unit that has been allocated
    """
    submit_label = 'Save Project'
    form_layout = Layout(project_form_layout_main,
                         Fieldset('', 'allocated_students'))

    def init_fields(self):
        super().init_fields()
        self.fields['allocated_students'] = forms.ModelMultipleChoiceField(
            queryset=models.Student.objects.filter(unit_id=self.instance.unit_id).annotate(is_assigned=ExpressionWrapper(Q(allocated_project_id=self.instance.id), output_field=BooleanField())).order_by('-is_assigned'), initial=self.instance.allocated_students.all(), required=False)
        self.fields['allocated_students'].widget.attrs['size'] = '10'

    def save(self, commit: bool = ...):
        current_students = self.instance.allocated_students
        new_students = self.cleaned_data.get('allocated_students')
        if current_students and new_students:
            for student in current_students.all():
                if student not in new_students:
                    student.allocated_project = None
                    student.allocated_preference_rank = None
                    student.save()
        if new_students:
            for student in new_students.all():
                student.allocated_project = self.instance
                allocated_project_pref = student.project_preferences.filter(
                    project_id=self.instance.id)
                student.allocated_preference_rank = allocated_project_pref.first(
                ).rank if allocated_project_pref.exists() else None
                student.save()
        return super().save(commit)


class ProjectListForm(UnitKwargMixin, forms.Form):
    """
        Form for uploading a list of projects
    """
    submit_label = 'Upload List of Projects to Unit'
    form_layout = Layout(
        'file',
        'list_override',
        FloatingField('identifier_column'),
        FloatingField('name_column'),
        FloatingField('min_students_column'),
        FloatingField('max_students_column'),
        FloatingField('description_column'),
        FloatingField('area_column'),
    )

    def init_fields(self):
        self.initial['identifier_column'] = 'id'
        self.initial['name_column'] = 'name'
        self.initial['min_students_column'] = 'min_students'
        self.initial['max_students_column'] = 'max_students'

    file = forms.FileField(label='')
    list_override = forms.BooleanField(
        label='Replace current projects', required=False)
    identifier_column = forms.CharField(
        label='Project ID Column Name')
    name_column = forms.CharField(
        label='Project Name Column Name')
    min_students_column = forms.CharField(
        label='Minimum Students Column Name')
    max_students_column = forms.CharField(
        label='Maximum Students Column Name')

    description_column = forms.CharField(
        label='Project Description Column Name', required=False, help_text='Leave blank if none.')

    area_column = forms.CharField(
        label='Project Area Column Name', help_text='Leave blank if none. Multiple areas for a single project should be seperated using a semi-colon (;).', required=False)

    def clean(self):
        valid_csv_file(self.cleaned_data.get('file'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'identifier_column',
                             self.cleaned_data.get('identifier_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'name_column',
                             self.cleaned_data.get('name_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'min_students_column',
                             self.cleaned_data.get('min_students_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'max_students_column',
                             self.cleaned_data.get('max_students_column'))

        if self.cleaned_data.get('description_column') != '':
            column_exists_in_csv(self.cleaned_data.get('file'), 'description_column',
                                 self.cleaned_data.get('description_column'))

        if self.cleaned_data.get('area_column') != '':
            column_exists_in_csv(self.cleaned_data.get('file'), 'area_column',
                                 self.cleaned_data.get('area_column'))

        file = self.cleaned_data.get(
            'file')
        file.seek(0)
        csv_data = csv.DictReader(
            StringIO(file.read().decode('utf-8-sig')), delimiter=',')
        min_students_column = self.cleaned_data.get('min_students_column')
        max_students_column = self.cleaned_data.get('max_students_column')

        for row in csv_data:
            project = models.Project()
            project.min_students = row[min_students_column]
            project.max_students = row[max_students_column]
            models.project_min_lte_max_constraint.validate(
                models.Project, project)

        return super().clean()


"""

Area forms

"""


class AreaForm(UnitKwargMixin, forms.ModelForm):
    """
        Form for adding a single area to a unit
    """
    submit_label = 'Add Area to Unit'
    form_layout = Layout(FloatingField('name'))

    def clean(self):
        name = self.cleaned_data.get('name')
        if self.unit.areas.filter(name=name).exists():
            raise forms.ValidationError(
                {'name': 'An area with that name is already included in this unit.'})
        return super().clean()

    class Meta:
        model = models.Area
        fields = ['name']


class AreaUpdateForm(AreaForm):
    """
        Form for updating a single area to a unit
    """
    submit_label = 'Save Area'
    form_layout = Layout(
        FloatingField('name'),
        'projects',
        'students',
    )

    def init_fields(self):
        super().init_fields()
        self.fields['projects'] = forms.ModelMultipleChoiceField(
            queryset=self.unit.projects.all(), initial=self.instance.projects.all(), required=False)
        self.fields['students'] = forms.ModelMultipleChoiceField(
            queryset=self.unit.students.all(), initial=self.instance.students.all(), required=False)

    def clean(self):
        self.instance.projects.set(self.cleaned_data.get('projects'))
        self.instance.students.set(self.cleaned_data.get('students'))
        return super(forms.ModelForm, self).clean()

    class Meta(AreaForm.Meta):
        fields = ['name']


"""

Preferences form

"""


class PreferenceListForm(UnitKwargMixin, forms.Form):
    """
        Form for uploading a list of preferences
    """
    submit_label = 'Upload List of Preferences to Unit'
    form_layout = Layout(
        'file',
        'list_override',
        FloatingField('preference_rank_column'),
        FloatingField('student_id_column'),
        FloatingField('project_identifier_column'),
        HTML('<div class="alert alert-secondary">If a preference uses a project or student ID that cannot be found within the list of projects or students, then that preference will not be saved.</div>'),
        HTML('<div class="alert alert-secondary">The validity of preference ranks, including whether they are consecutive, start from one, and whether each student is assigned to the minimum number of preferences and less than the maximum number of preferences, will not be checked when uploading preferences from a file.</div>'),
        HTML('<div class="alert alert-danger">Uploading a list of preferences may override the current preferences.</div>')
    )

    def init_fields(self):
        self.initial['preference_rank_column'] = 'preference_rank'
        self.initial['student_id_column'] = 'student_id'
        self.initial['project_identifier_column'] = 'project_id'

    file = forms.FileField(label='')
    list_override = forms.BooleanField(
        label='Replace current preferences', required=False)
    preference_rank_column = forms.CharField(
        label='Preference Rank Column Name')
    student_id_column = forms.CharField(
        label='Student ID Column Name')
    project_identifier_column = forms.CharField(
        label='Project ID Column Name')

    def clean(self):
        valid_csv_file(self.cleaned_data.get('file'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'preference_rank_column',
                             self.cleaned_data.get('preference_rank_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'student_id_column',
                             self.cleaned_data.get('student_id_column'))
        column_exists_in_csv(self.cleaned_data.get('file'), 'project_identifier_column',
                             self.cleaned_data.get('project_identifier_column'))
        return super().clean()


"""

Allocation Forms

"""


class StartAllocationForm(UnitKwargMixin, forms.Form):
    """

    Start allocation form

    """
    submit_label = 'Start Allocation'
