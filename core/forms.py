from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, UserCreationForm, SetPasswordForm

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML
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
            ),
            HTML(
                """<a href="{% url 'register' %}" class="small text-muted link-underline link-underline-opacity-0 link-underline-opacity-75-hover">Register</a>"""),
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
                HTML(
                    """<a href="{% url 'account' %}" class="btn btn-secondary">Cancel</a>"""),
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


class AccountUpdateForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
    )

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop('user', None)

        super().__init__(*args, **kwargs)

        self.instance = self.user

        if self.instance.is_student:
            self.fields.get('username').disabled = True
            self.fields.get(
                'username').help_text = 'You cannot change your username as it is linked to your unit enrolments.'
        self.fields.get('username').initial = self.instance.username
        self.fields.get('email').initial = self.instance.email

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FloatingField('username'),
            FloatingField('email'),
            FloatingField('password'),
            HTML(
                """<a href="{% url 'password_change' %}" class="btn btn-sm btn-outline-primary mb-3">Change Password</a>"""),
            FormActions(
                Submit('submit', 'Save',
                       css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'index' %}" class="btn btn-secondary">Cancel</a>"""),
            )
        )

    def clean(self):
        # Validate that the password is correct
        password = self.cleaned_data.get('password')
        if not self.instance.check_password(password):
            raise forms.ValidationError(
                {'password': 'Your password was entered incorrectly. Please enter it again.'}
            )
        return super().clean()

    class Meta:
        model = models.User
        fields = ['username', 'email']


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
