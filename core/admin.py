from typing import Any, Optional
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http.request import HttpRequest
from django.utils.html import format_html, urlencode
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.models import Group

from django.contrib.auth.forms import PasswordResetForm
from django.utils.crypto import get_random_string

from . import models
from . import forms


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    add_form_template = 'registration/add_form.html'
    add_form = forms.AdminUserRegistrationForm
    add_fieldsets = (
        (None, {'fields': ('username', 'email')}),
        ('Password', {'fields': ('password1', 'password2'),
         'classes': ('collapse', 'collapse-closed'), }),
        ('User type', {'fields': ('is_manager', 'is_student')}),
    )

    list_display = BaseUserAdmin.list_display + \
        ('groups_list', 'is_manager', 'is_student', 'last_login')
    list_filter = BaseUserAdmin.list_filter + ('is_manager', 'is_student')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('User type', {'fields': ('is_manager', 'is_student')}),
    )

    readonly_fields = [
        'date_joined', 'last_login'
    ]

    def groups_list(self, user):
        return [group.name for group in user.groups.all()]
    groups_list.short_description = 'groups'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('groups')

    def save_model(self, request, obj, form, change):
        if not change and (not form.cleaned_data['password1'] or not obj.has_usable_password()):
            # Create a temporary random password as the reset form won't reset an un-set password.
            obj.set_password(get_random_string(10))

            super().save_model(request, obj, form, change)

            reset_form = PasswordResetForm({'email': obj.email})
            assert reset_form.is_valid()
            reset_form.save(
                request=request,
                use_https=request.is_secure(),
                subject_template_name='registration/account_creation_subject.txt',
                email_template_name='registration/account_creation_email.html',
            )
        else:
            super().save_model(request, obj, form, change)


@admin.register(models.Unit)
class UnitAdmin(admin.ModelAdmin):
    autocomplete_fields = ['manager']
    list_select_related = ['manager']
    list_display = ['code', 'name', 'year', 'semester', 'manager_link', 'students_count', 'projects_count', 'preference_submission_start',
                    'preference_submission_end', 'minimum_preference_limit']
    search_fields = ['code', 'name', 'year', 'semester']

    @admin.display(ordering='manager_id')
    def manager_link(self, unit):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse('admin:core_user_change', args=(unit.manager.pk,)),
            unit.manager
        ))
    manager_link.short_description = 'manager'

    @admin.display(ordering='students_count')
    def students_count(self, unit):
        url = (
            reverse('admin:core_user_changelist')
            + '?'
            + urlencode({
                'enrolled_units__id': str(unit.id)
            }))
        return format_html('<a href="{}">{}</a>', url, unit.students_count)
    students_count.short_description = 'no. students'

    @admin.display(ordering='projects_count')
    def projects_count(self, unit):
        return unit.projects_count
        url = (
            reverse('admin:core_project_change')
            + '?'
            + urlencode({
                'unit__id': str(unit.id)
            }))
        return format_html('<a href="{}">{}</a>', url, unit.projects_count)
    projects_count.short_description = 'no. projects'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_manager:
            queryset = queryset.filter(manager_id=request.user.id)
        return queryset.annotate(
            students_count=Count('enrolled_students'), projects_count=Count('projects')
        )


@admin.register(models.EnrolledStudent)
class EnrolledStudentAdmin(admin.ModelAdmin):
    list_display = ['id', 'student_id', 'user', 'unit']


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'number', 'description',
                    'min_students', 'max_students']
    search_fields = ['name', 'number']
    # add unit?


@admin.register(models.ProjectPreference)
class ProjectPreferenceAdmin(admin.ModelAdmin):
    list_display = ['rank', 'project', 'student']

    # No staff should be able to alter preferences...?
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
