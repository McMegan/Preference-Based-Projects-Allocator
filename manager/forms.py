import csv
from io import StringIO
import os

from django import forms
from django.db.models import Q, ExpressionWrapper, BooleanField

from crispy_forms.bootstrap import FormActions, InlineField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML, Field
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
                  'preference_submission_end', 'minimum_preference_limit', 'is_active', 'limit_by_major']


class UnitUpdateForm(CreateUnitForm):
    is_active = forms.BooleanField(
        label='Unit is current/active', required=False)
    limit_by_major = forms.BooleanField(
        label='Limit project preference selection by major', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            unit_form_layout_main,
            unit_form_layout_allocator,
            'is_active',
            'limit_by_major',
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
        if models.Student.objects.filter(student_id=student_id, unit_id=self.pk_unit).exists():
            raise forms.ValidationError(
                {'student_id': 'A student with that ID is already enrolled in this unit.'})
        return super().clean()

    class Meta:
        model = models.Student
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


class AllocatedProjectChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{str(obj)}    (Current Group Size = {obj.allocated_students.count()})'


class StudentUpdateForm(forms.ModelForm):
    """
        Form for updating a student's allocation in a unit
    """

    def __init__(self, *args, **kwargs):
        self.unit = kwargs.pop('unit', None)

        super().__init__(*args, **kwargs)

        self.fields['allocated_project'] = AllocatedProjectChoiceField(
            queryset=self.unit.projects.prefetch_related('allocated_students'), required=False, label='Allocated Project')

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FloatingField('allocated_project',
                          css_class='my-3'),
            FormActions(
                Submit('submit', 'Save Student Allocation',
                       css_class='btn btn-primary')
            )
        )

    def save(self, commit: bool = ...):
        # Update allocated preference
        if self.instance.allocated_project:
            allocated_project_pref = self.instance.project_preferences.filter(
                project_id=self.instance.allocated_project.id)
            self.instance.allocated_preference_rank = allocated_project_pref.first(
            ).rank if allocated_project_pref.exists() else None
        return super().save(commit)

    class Meta:
        model = models.Student
        fields = ['allocated_project']


class StudentDeleteForm(forms.Form):
    """
        Form for deleting a single student
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<p>Are you sure you want to remove this student?</p>'),
            FormActions(
                Submit('submit', 'Yes, Remove Student from Unit',
                       css_class='btn btn-danger'),
            )
        )


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
                Submit('submit', 'Yes, Remove All Students from Unit',
                       css_class='btn btn-danger'),
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
        self.unit = kwargs.pop('unit', None)

        super().__init__(*args, **kwargs)

        self.helper.layout = Layout(
            project_form_layout_main,
            FormActions(
                Submit('submit', 'Save Project',
                       css_class='btn btn-primary'),
            )
        )


class ProjectAllocatedUpdateForm(ProjectUpdateForm):
    """
        Form for updating a project in a unit
    """

    def __init__(self, *args, **kwargs):
        unit = kwargs.pop('unit')

        super().__init__(*args, **kwargs)

        self.fields['allocated_students'] = forms.ModelMultipleChoiceField(
            queryset=models.Student.objects.filter(unit_id=unit.id).annotate(is_assigned=ExpressionWrapper(Q(allocated_project_id=self.instance.id), output_field=BooleanField())).order_by('-is_assigned'), initial=self.instance.allocated_students.all(), required=False)

        self.helper.layout = Layout(
            project_form_layout_main,
            Fieldset('', Field('allocated_students', size=10)),
            FormActions(
                Submit('submit', 'Save Project',
                       css_class='btn btn-primary'),
            )
        )

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

    class Meta(ProjectForm.Meta):
        fields = ['number', 'name', 'description',
                  'min_students', 'max_students']


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
            column_exists_in_csv(self.cleaned_data.get('file'), 'description_column',
                                 self.cleaned_data.get('description_column'))

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


class ProjectDeleteForm(forms.Form):
    """
        Form for deleting a single project
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<p>Are you sure you want to remove this project?</p>'),
            FormActions(
                Submit('submit', 'Yes, Remove Project from Unit',
                       css_class='btn btn-danger'),
            )
        )


class ProjectListClearForm(forms.Form):
    """
        Form for clearing the list of projects
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<p>Are you sure you want to remove all projects from this unit?</p>'),
            FormActions(
                Submit('submit', 'Yes, Remove All Projects from Unit',
                       css_class='btn btn-danger'),
            )
        )


# Allocation forms


class StartAllocationForm(forms.Form):
    """
        Form for starting the allocation process
    """

    def __init__(self, *args, **kwargs):
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
                    This unit has already been allocated, allocating again will override the current allocation.<br>If this allocation fails, the previous successful allocation will be retained.
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
