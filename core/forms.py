from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, UserCreationForm
from django import forms

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField

from . import models


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


class StudentUserRegistrationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['email'].required = True

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                FloatingField('username'),
                FloatingField('email'),
                FloatingField('password1'),
                FloatingField('password2'),
            ),
            FormActions(
                Submit('submit', 'Register', css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'login' %}" class="btn btn-outline-secondary">Log In</a>"""),
            )
        )

    def clean(self):
        # If an enrollment doesn't exist for this username / student id
        if self.cleaned_data.get('username') and not models.EnrolledStudent.objects.filter(
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
            Fieldset(
                '',
                FloatingField('username'),
                FloatingField('password'),
            ),
            FormActions(
                Submit('submit', 'Log In', css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'register' %}" class="btn btn-outline-secondary">Register</a>"""),
            )
        )


class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                FloatingField('old_password'),
                FloatingField('new_password1'),
                FloatingField('new_password2'),
            ),
            FormActions(
                Submit('submit', 'Save', css_class='btn btn-primary'),
            )
        )


class UserPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                '',
                FloatingField('email'),
            ),
            FormActions(
                Submit('submit', 'Reset Password',
                       css_class='btn btn-primary'),
                HTML(
                    """<a href="{% url 'login' %}" class="btn btn-outline-secondary">Log In</a>"""),
            )
        )
