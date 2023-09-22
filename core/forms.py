from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, UserCreationForm, SetPasswordForm
from django import forms

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField

from . import models

"""

Auth forms

"""


class StudentUserRegistrationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['email'].required = True

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FloatingField('username'),
            FloatingField('email'),
            FloatingField('password1'),
            FloatingField('password2'),
            FormActions(
                Submit('submit', 'Register', css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'login' %}" class="btn btn-outline-secondary">Log In</a>"""),
            )
        )

    def clean(self):
        # If an enrollment doesn't exist for this username / student id
        if self.cleaned_data.get('username') and not models.Student.objects.filter(
                student_id=self.cleaned_data.get('username')).exists():
            raise forms.ValidationError(
                {'username': 'Invalid student ID. This student ID has not been registered for any units.'})
        return super().clean()

    class Meta(UserCreationForm.Meta):
        model = models.User
        fields = ['username', 'email', 'password1', 'password2']
        labels = {
            'username': 'Student ID'
        }


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FloatingField('username'),
            FloatingField('password'),
            FormActions(
                Submit('submit', 'Log In', css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'register' %}" class="btn btn-outline-secondary">Register</a>"""),
            )
        )


class UserPasswordSetForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FloatingField('new_password1'),
            FloatingField('new_password2'),
            FormActions(
                Submit('submit', 'Save Password', css_class='btn btn-primary'),
            )
        )


class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FloatingField('old_password'),
            FloatingField('new_password1'),
            FloatingField('new_password2'),
            FormActions(
                Submit('submit', 'Save', css_class='btn btn-primary'),
            )
        )

    def clean(self):
        super().clean()
        old_password = self.cleaned_data.get('old_password')
        new_password = self.cleaned_data.get('new_password1')
        if old_password and new_password and self.cleaned_data.get('new_password2') and old_password == new_password:
            raise forms.ValidationError({'new_password2':
                                         'Your new password must not be the same as your old password.'})
        return self.cleaned_data


class UserPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FloatingField('email'),
            FormActions(
                Submit('submit', 'Reset Password',
                       css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'login' %}" class="btn btn-outline-secondary">Log In</a>"""),
            )
        )


"""

Admin forms

"""


class AdminUserRegistrationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Passwords are not required
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def clean(self):
        # Make sure email is included if no password is specified
        if not bool(self.cleaned_data.get('password1')) and not bool(self.cleaned_data.get('password2')) and not bool(self.cleaned_data.get('email')):
            raise forms.ValidationError(
                {'email': 'Email is required if no password is specified.'})
        # Make sure both passwords are inputted if a password is specified
        if bool(self.cleaned_data.get('password1')) ^ bool(self.cleaned_data.get('password2')):
            raise forms.ValidationError(
                {'password2': 'Please fill out both fields.'})
        return super().clean()


class AdminStudentAddForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student_id'].label = 'Student ID'
        self.fields['student_id'].help_text = 'If a user exists for this student ID, their user account will be linked automatically.'

    class Meta:
        model = models.Student
        fields = ['unit', 'student_id']


class AdminStudentChangeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['area'].queryset = models.Area.objects.filter(
            unit=self.instance.unit)
        self.fields['allocated_project'].queryset = models.Project.objects.filter(
            unit=self.instance.unit)

    class Meta(AdminStudentAddForm.Meta):
        model = models.Student
        fields = ['unit', 'user', 'student_id', 'area', 'allocated_project']
