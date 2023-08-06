import datetime
from django.contrib.auth.forms import AuthenticationForm, UsernameField, PasswordChangeForm, PasswordResetForm
from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit
from crispy_bootstrap5.bootstrap5 import FloatingField

from . import models


class SplitDateTimeWidget(forms.SplitDateTimeWidget):
    """
    A widget that splits datetime input into two <input type="text"> boxes,
    and uses HTML5 'date' and 'time' inputs.
    """

    def __init__(self, attrs=None, date_format=None, time_format=None, date_attrs=None, time_attrs=None):
        date_attrs = date_attrs or {}
        time_attrs = time_attrs or {}
        if "type" not in date_attrs:
            date_attrs["type"] = "date"
        if "type" not in time_attrs:
            time_attrs["type"] = "time"
        return super().__init__(
            attrs=attrs, date_format=date_format, time_format=time_format, date_attrs=date_attrs, time_attrs=time_attrs
        )


class SplitDateTimeField(forms.SplitDateTimeField):
    widget = SplitDateTimeWidget


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
            Submit('submit', 'Log In', css_class='btn btn-primary'),
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
            Submit('submit', 'Save', css_class='btn btn-primary'),
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
            Submit('submit', 'Reset Password', css_class='btn btn-primary'),
        )


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
                'preference_submission_start',
                'preference_submission_end',
                'minimum_preference_limit'
            ),
            Submit('submit', 'Save', css_class='btn btn-primary'),
        )

    pass

    class Meta:
        model = models.Unit
        fields = ['code', 'name', 'year', 'semester', 'preference_submission_start',
                  'preference_submission_end', 'minimum_preference_limit']
