import csv
from io import StringIO
import os

from django import forms
from django.db.models import Q, ExpressionWrapper, BooleanField
from django.templatetags.static import static

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField

from core import models


class ListForm(forms.Form):
    def clean(self):
        file = self.cleaned_data.get('file')

        # Check if CSV file
        if os.path.splitext(file.name)[1].casefold() != '.csv'.casefold():
            raise forms.ValidationError({'file': 'File must be CSV.'})

        # Check if CSV file has rows
        file.seek(0)
        csv_data = csv.DictReader(
            StringIO(file.read().decode('utf-8-sig')), delimiter=',')
        csv_len = sum(1 for row in csv_data)
        if csv_len == 0:
            raise forms.ValidationError(
                {'file': 'The uploaded file must have at least one row, other than the header row.'})

        # Make a dictionary of all the columns to be checked
        columns_to_check = {}
        if hasattr(self, 'columns_required'):
            for column in self.columns_required:
                columns_to_check[column] = self.cleaned_data.get(column)
        if hasattr(self, 'columns_optional'):
            for column in self.columns_optional:
                if self.cleaned_data.get(column) != '':
                    columns_to_check[column] = self.cleaned_data.get(column)

        # Check that the columns exist in the CSV file
        file.seek(0)
        csv_data = csv.DictReader(
            StringIO(file.read().decode('utf-8-sig')), delimiter=',')
        csv_row = next(csv_data)

        for field_name in columns_to_check:
            try:
                csv_row[columns_to_check[field_name]]
            except KeyError:
                raise forms.ValidationError(
                    {field_name: 'Please enter a valid column name for this file.'})

        return super().clean()


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
        self.cancel_url = kwargs.pop('cancel_url', None)
        self.disabled = kwargs.pop('disabled', None)

        if self.unit and not self.disabled:
            self.disabled = False
            if self.unit.celery_task:
                self.disabled = not self.unit.task_ready()

        super().__init__(*args, **kwargs)

        self.init_fields()

        if self.disabled:
            for field_name in self.fields:
                field = self.fields[field_name]
                field.disabled = True

        self.helper = FormHelper()
        self.submit_button = Submit('submit', self.submit_label if hasattr(
            self, 'submit_label') else 'Submit', css_class='btn ' + self.submit_button_variant if hasattr(self, 'submit_button_variant') else 'btn-primary', disabled=self.disabled)
        self.cancel_button = HTML(
            f"""<a class="btn btn-secondary" href="{self.cancel_url}">Cancel</a>""")
        self.form_actions = FormActions(self.submit_button, self.cancel_button)

        self.helper.layout = Layout(self.get_form_layout(), self.form_actions)

    def get_form_layout(self):
        return self.form_layout if hasattr(
            self, 'form_layout') and self.form_layout else None

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


class UnitCreateForm(forms.ModelForm):
    is_active = forms.BooleanField(
        label='Unit is current/active', required=False, help_text='Students will only be able to see the unit if this is checked.')

    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop('manager')

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

    def clean(self):
        cleaned = super().clean()
        # Validate unit uniqueness if values have changed
        if 'code' in self.changed_data or 'year' in self.changed_data or 'semester' in self.changed_data:
            # Validate that the unit is unique for this manager
            if self.manager.managed_units.filter(
                    code=self.cleaned_data.get('code'), year=self.cleaned_data.get('year'), semester=self.cleaned_data.get('semester')).exists():
                raise forms.ValidationError(
                    {'code': 'A unit with that code already exists for this semester and year.'})
        return cleaned

    class Meta:
        model = models.Unit
        fields = ['code', 'name', 'year', 'semester', 'is_active']


class UnitUpdateForm(UnitKwargMixin, UnitCreateForm):
    """
        Form for updating a unit
    """
    submit_label = 'Save Unit'

    preference_submission_start = SplitDateTimeField(
        required=False, label='Start')
    preference_submission_end = SplitDateTimeField(required=False, label='End')

    minimum_preference_limit = forms.IntegerField(
        required=False, label='Minimum')
    maximum_preference_limit = forms.IntegerField(
        required=False, label='Maximum')

    limit_by_major = forms.BooleanField(
        label='Limit project preference selection by major/area', required=False, help_text='This will limit each students project preference options to those which match the students area. If a student has no area, all projects will be displayed. If a project has no area, it will be displayed to all students.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        num_projects = self.unit.projects.count()
        if num_projects == 0:
            self.fields.get('minimum_preference_limit').disabled = True
            self.fields.get('maximum_preference_limit').disabled = True

    def get_form_layout(self):
        num_projects = self.unit.projects.count()
        return Layout(
            unit_form_layout_main,
            Fieldset(
                'Preference Submission Timeframe',
                Div(
                    Div('preference_submission_start',
                        css_class='col preference_submission_timeframe'),
                    Div('preference_submission_end',
                        css_class='col preference_submission_timeframe'),
                    css_class='row'
                ),
            ),
            Fieldset(
                'Preference Limit',
                HTML(
                    '<div class="alert alert-warning">You must add projects to the unit before the minimum and maximum preference limits can be set.</div>') if num_projects == 0 else None,
                Div(
                    Div('minimum_preference_limit',
                        css_class='col'),
                    Div('maximum_preference_limit',
                        css_class='col'),
                    css_class='row'
                ),
                HTML('<div id="hint_id_preference_limit" class="form-text mt-0 mb-3">Leave blank or set to 0 to have no minimum/maximum limit on the number of preferences students can submit.</div>')
            ),
            Fieldset(
                'Other Preference Submission Settings',
                'limit_by_major',
            ),
        )

    def clean(self):
        num_projects = self.unit.projects.count()
        minimum_preference_limit = self.cleaned_data.get(
            'minimum_preference_limit')
        maximum_preference_limit = self.cleaned_data.get(
            'maximum_preference_limit')
        if minimum_preference_limit and minimum_preference_limit < 0:
            raise forms.ValidationError(
                {'minimum_preference_limit': 'The minimum preference limit must not be negative.'})
        if maximum_preference_limit and maximum_preference_limit < 0:
            raise forms.ValidationError(
                {'maximum_preference_limit': 'The maximum preference limit must not be negative.'})
        if minimum_preference_limit and minimum_preference_limit > num_projects:
            raise forms.ValidationError(
                {'minimum_preference_limit': 'The minimum preference limit must be less than or equal to the total number of projects in the unit.'})
        if maximum_preference_limit and maximum_preference_limit > num_projects:
            raise forms.ValidationError(
                {'maximum_preference_limit': 'The maximum preference limit must be less than or equal to the total number of projects in the unit.'})

        return super().clean()

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
        FloatingField('name'),
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
        fields = ['student_id', 'name']


class AllocatedProjectChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{str(obj)}    (Current Group Size = {obj.allocated_students.count()})'


class StudentUpdateForm(UnitKwargMixin, forms.ModelForm):
    """
        Form for updating a student in a unit
    """
    submit_label = 'Save Student'
    form_layout = Layout(
        FloatingField('name'),
        'area'
    )

    def init_fields(self):
        self.fields['area'] = forms.ModelMultipleChoiceField(
            queryset=self.unit.areas, required=False, help_text='You must add an area to the unit before you can select it for a student. To deselect an area cmd/ctrl + click on the area you wish to deselect.')

    class Meta:
        model = models.Student
        fields = ['name', 'area']


class StudentAllocatedUpdateForm(StudentUpdateForm):
    """
        Form for updating a student in a unit that has been allocated
    """
    form_layout = Layout(
        FloatingField('name'),
        FloatingField('allocated_project',
                      css_class='my-3'),
        'area'
    )

    def init_fields(self):
        super().init_fields()
        self.fields['allocated_project'] = AllocatedProjectChoiceField(
            queryset=self.unit.projects.prefetch_related('allocated_students'), required=False, label='Allocated Project')

    class Meta(StudentUpdateForm.Meta):
        fields = ['name', 'allocated_project', 'area']


class StudentListForm(UnitKwargMixin, ListForm):
    """
        Form for uploading a list of students
    """
    submit_label = 'Upload List of Students to Unit'
    form_layout = Layout(
        'file',
        Div(
            HTML(
                f'<a class="small d-flex gap-2 link-offset-4 link-offset-4-hover link-underline link-secondary link-underline-opacity-0 link-underline-opacity-75-hover" href="{static("templates/Student-List-Template.csv")}"><i class="bi bi-download"></i><span>Student List Template (name and area columns are optional)</span></a>'),
            css_class='m-3'
        ),
        'list_override',
        FloatingField('student_id_column'),
        FloatingField('student_name_column'),
        FloatingField('area_column'),
        HTML("""<p>Please note: It may take a few moments for the students in the uploaded file to show up in the students list.</p>""")
    )

    file = forms.FileField(label='')
    list_override = forms.BooleanField(
        label='Replace current students', required=False)
    student_id_column = forms.CharField(
        label='Student ID Column Name')
    student_name_column = forms.CharField(
        label='Student Name Column Name', help_text='Leave blank if not required.', required=False)

    area_column = forms.CharField(
        label='Project Area Column Name', help_text='Leave blank if none. Multiple areas for a single project should be seperated using a semi-colon (;).', required=False)

    columns_required = ['student_id_column']
    columns_optional = ['student_name_column', 'area_column']

    def init_fields(self):
        self.fields['student_id_column'].initial = 'user_id'

    def clean(self):
        cleaned = super().clean()

        file = self.cleaned_data.get(
            'file')
        file.seek(0)
        csv_data = csv.DictReader(
            StringIO(file.read().decode('utf-8-sig')), delimiter=',')
        student_id_column = self.cleaned_data.get('student_id_column')
        student_name_column = self.cleaned_data.get('student_name_column')
        area_column = self.cleaned_data.get('area_column')

        errors = []

        for row in csv_data:
            if not all(row[field] == '' for field in row):
                student = models.Student()
                student.student_id = row[student_id_column].strip()
                student.unit = self.unit
                if student_name_column != '' and row[student_name_column].strip():
                    student.name = row[student_name_column].strip()
                if area_column != '' and row[area_column] and row[area_column].strip() != '':
                    areas = row[area_column].split(';')
                    for area in areas:
                        area = area.strip()
                        area = models.Area(name=area, unit=self.unit)
                        try:
                            area.full_clean(validate_unique=False,
                                            validate_constraints=False)
                        except forms.ValidationError as e:
                            for error in e:
                                for message in error[1]:
                                    errors.append(forms.ValidationError(
                                        f'The value for the "area" column in the row with the ID "{student.student_id}" produced the following error: {message}' if student.student_id != '' else f'The value for the "area" column in a row without an ID produced the following error: {message}'))
                try:
                    student.full_clean(validate_unique=False,
                                       validate_constraints=False)
                except forms.ValidationError as e:
                    for error in e:
                        if type(error) == tuple:
                            for message in error[1]:
                                if error[0] == '__all__':
                                    errors.append(forms.ValidationError(
                                        f'The row with the ID "{student.student_id}" in the inputted file produced the following error: {message}' if student.student_id != '' else f'A row without an ID in the inputted file produced the following error: {message}'))
                                else:
                                    errors.append(forms.ValidationError(
                                        f'The value for the "{error[0]}" column in the row with the ID "{student.student_id}" produced the following error: {message}' if student.student_id != '' else f'The value for the "{error[0]}" column in a row without an ID produced the following error: {message}'))
                        else:
                            errors.append(forms.ValidationError(
                                f'The row with the ID "{student.student_id}" in the inputted file produced the following error: {error}' if student.student_id != '' else f'A row without an ID in the inputted file produced the following error: {error}'))

        if errors != []:
            raise forms.ValidationError(errors)
        return cleaned


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


class ProjectListForm(UnitKwargMixin, ListForm):
    """
        Form for uploading a list of projects
    """
    submit_label = 'Upload List of Projects to Unit'
    form_layout = Layout(
        'file',
        Div(
            HTML(
                f'<a class="small d-flex gap-2 link-offset-4 link-offset-4-hover link-underline link-secondary link-underline-opacity-0 link-underline-opacity-75-hover" href="{static("templates/Project-List-Template.csv")}"><i class="bi bi-download"></i><span>Project List Template (description and area columns are optional)</span></a>'),
            css_class='m-3'
        ),
        'list_override',
        FloatingField('identifier_column'),
        FloatingField('name_column'),
        FloatingField('min_students_column'),
        FloatingField('max_students_column'),
        FloatingField('description_column'),
        FloatingField('area_column'),
        HTML("""<p>Please note: It may take a few moments for the projects in the uploaded file to show up in the projects list.</p>""")
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

    columns_required = ['identifier_column', 'name_column',
                        'min_students_column', 'max_students_column',]
    columns_optional = ['description_column', 'area_column']

    def clean(self):
        cleaned = super().clean()

        file = self.cleaned_data.get(
            'file')
        file.seek(0)
        csv_data = csv.DictReader(
            StringIO(file.read().decode('utf-8-sig')), delimiter=',')
        identifier_column = self.cleaned_data.get('identifier_column')
        name_column = self.cleaned_data.get('name_column')
        min_students_column = self.cleaned_data.get('min_students_column')
        max_students_column = self.cleaned_data.get('max_students_column')
        description_column = self.cleaned_data.get('description_column')
        area_column = self.cleaned_data.get('area_column')

        errors = []
        for row in csv_data:
            if not all(row[field] == '' for field in row):
                project = models.Project()
                project.identifier = row[identifier_column].strip()
                project.name = row[name_column].strip()
                project.min_students = row[min_students_column].strip()
                project.max_students = row[max_students_column].strip()
                project.unit = self.unit
                if description_column != '' and row[description_column] != '' and row[description_column] != None:
                    project.description = row[description_column].strip()
                if area_column != '' and row[area_column] != None and row[area_column].strip() != '':
                    areas = row[area_column].split(';')
                    for area_name in areas:
                        area_name = area_name.strip()
                        area = models.Area(name=area_name, unit=self.unit)
                        try:
                            area.full_clean(validate_unique=False,
                                            validate_constraints=False)
                        except forms.ValidationError as e:
                            for error in e:
                                for message in error[1]:
                                    errors.append(forms.ValidationError(
                                        f'The value for the "area" column in the row with the ID "{project.identifier}" produced the following error: {message}' if project.identifier != '' else f'The value for the "area" column in a row without an ID produced the following error: {message}'))
                try:
                    project.full_clean(validate_unique=False,
                                       validate_constraints=False)
                    models.project_min_lte_max_constraint.validate(
                        models.Project, project)
                except forms.ValidationError as e:
                    for error in e:
                        if type(error) == tuple:
                            for message in error[1]:
                                if error[0] == '__all__':
                                    errors.append(forms.ValidationError(
                                        f'The row with the Project ID "{project.identifier}" in the uploaded file produced the following error: {message}' if project.identifier != '' else f'A row without an ID in the uploaded file produced the following error: {message}'))
                                else:
                                    errors.append(forms.ValidationError(
                                        f'The value for the "{error[0]}" column in the row with the Project ID "{project.identifier}" produced the following error: {message}' if project.identifier != '' else f'The value for the "{error[0]}" column in a row without an ID produced the following error: {message}'))
                        else:
                            errors.append(forms.ValidationError(
                                f'The row with the Project ID "{project.identifier}" in the uploaded file produced the following error: {error}' if project.identifier != '' else f'A row without an ID in the uploaded file produced the following error: {error}'))
        if errors != []:
            raise forms.ValidationError(errors)
        return cleaned


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


class PreferenceListForm(UnitKwargMixin, ListForm):
    """
        Form for uploading a list of preferences
    """
    submit_label = 'Upload List of Preferences to Unit'
    form_layout = Layout(
        'file',
        Div(
            HTML(
                f'<a class="small d-flex gap-2 link-offset-4 link-offset-4-hover link-underline link-secondary link-underline-opacity-0 link-underline-opacity-75-hover" href="{static("templates/Preference-List-Template.csv")}"><i class="bi bi-download"></i><span>Preference List Template</span></a>'),
            css_class='m-3'
        ),
        FloatingField('preference_rank_column'),
        FloatingField('student_id_column'),
        FloatingField('project_identifier_column'),
        HTML("""
             <p>Please note:</p><ul class="list">
                <li>If a preference references a project ID or student ID that cannot be found within the list of projects or students, then that preference will not be saved.</li>
                <li>The validity of preference ranks, including whether they are consecutive, start from one, and whether each student has submitted at least the minimum number of preferences and at most the maximum number of preferences, will not be checked when uploading preferences from a file.</li>
                <li>If a student has multiple preferences with the same rank, only the first instance will be retained.</li>
                <li>It may take a few moments for the preferences in the uploaded file to show up in the preferences list.</li>
            </ul>
            <div class="alert alert-danger">Uploading a list of preferences will override all of the preferences for the current unit.</div>
        """)
    )

    def init_fields(self):
        self.initial['preference_rank_column'] = 'preference_rank'
        self.initial['student_id_column'] = 'student_id'
        self.initial['project_identifier_column'] = 'project_id'

    file = forms.FileField(label='')
    preference_rank_column = forms.CharField(
        label='Preference Rank Column Name')
    student_id_column = forms.CharField(
        label='Student ID Column Name')
    project_identifier_column = forms.CharField(
        label='Project ID Column Name')

    columns_required = ['preference_rank_column',
                        'student_id_column', 'project_identifier_column']


"""

Allocation Forms

"""


class StartAllocationForm(UnitKwargMixin, forms.Form):
    """

    Start allocation form

    """
    submit_label = 'Start Allocation'
