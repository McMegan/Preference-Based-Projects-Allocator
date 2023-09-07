from typing import Any
from django.contrib.admin import SimpleListFilter
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import PasswordResetForm
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import format_html, urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


from . import models
from . import forms

admin.site.unregister(Group)


"""

User admin

"""


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

    list_display = ('username', 'email', 'is_staff',
                    'is_manager', 'managed_unit_count', 'is_student', 'enrolled_unit_count')
    list_filter = BaseUserAdmin.list_filter + ('is_manager', 'is_student')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(managed_unit_count=Count('managed_units')).annotate(enrolled_unit_count=Count('enrollments'))

    @admin.display(ordering='managed_unit_count')
    def managed_unit_count(self, user: models.User):
        url = (
            reverse('admin:core_unit_changelist')
            + '?'
            + urlencode({
                'manager_id': str(user.id)
            }))
        return format_html('<a href="{}">{}</a>', url, user.managed_unit_count)
    managed_unit_count.short_description = 'managed unit count'

    @admin.display(ordering='enrolled_unit_count')
    def enrolled_unit_count(self, user: models.User):
        url = (
            reverse('admin:core_student_changelist')
            + '?'
            + urlencode({
                'user_id': str(user.id)
            }))
        return format_html('<a href="{}">{}</a>', url, user.enrolled_unit_count)
    enrolled_unit_count.short_description = 'enrollment count'

    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),
        (_('Permissions'), {
         'fields': ('is_active', 'is_staff', 'is_superuser'), },),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        ('User type', {'fields': ('is_manager', 'is_student')}),
    )
    readonly_fields = [
        'date_joined', 'last_login'
    ]

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


"""

Unit admin

"""


@admin.register(models.Unit)
class UnitAdmin(admin.ModelAdmin):
    autocomplete_fields = ['manager']
    list_select_related = ['manager']
    list_display = ['code', 'name', 'year', 'semester', 'manager_link', 'students_count', 'projects_count', 'preference_submission_start',
                    'preference_submission_end', 'minimum_preference_limit', 'maximum_preference_limit', 'is_active', 'limit_by_major', 'is_allocating', 'allocation_status']
    list_filter = ['is_active', 'year', 'semester', 'preference_submission_start',
                   'preference_submission_end', 'allocation_status']
    search_fields = ['code', 'name']

    fieldsets = (
        ('Unit Information', {
            'fields': (('code', 'name'), ('year', 'semester'), ('manager'))
        }),
        ('Unit Settings', {
            'fields': (('preference_submission_start', 'preference_submission_end'), ('minimum_preference_limit', 'maximum_preference_limit'), ('is_active', 'limit_by_major'), ('is_allocating', 'allocation_status')),
        }),
    )
    readonly_fields = ('is_allocating', 'allocation_status')

    @admin.display(ordering='manager_id')
    def manager_link(self, unit):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse('admin:core_user_change', args=(unit.manager.pk,)),
            unit.manager
        ))
    manager_link.short_description = 'manager'

    @admin.display(ordering='students_count')
    def students_count(self, unit: models.Unit):
        url = (
            reverse('admin:core_student_changelist')
            + '?'
            + urlencode({
                'unit_id': str(unit.id)
            }))
        return format_html('<a href="{}">{}</a>', url, unit.students_count)
    students_count.short_description = 'no. students'

    @admin.display(ordering='projects_count')
    def projects_count(self, unit):
        url = (
            reverse('admin:core_project_changelist')
            + '?'
            + urlencode({
                'unit_id': str(unit.id)
            }))
        return format_html('<a href="{}">{}</a>', url, unit.projects_count)
    projects_count.short_description = 'no. projects'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_manager:
            queryset = queryset.filter(manager_id=request.user.id)
        return queryset.annotate(
            students_count=Count('students', distinct=True), projects_count=Count('projects', distinct=True)
        )


"""

Student admin

"""


class RegisteredFilter(SimpleListFilter):
    title = 'Is Registered'
    parameter_name = 'is_registered'

    def lookups(self, request, model_admin):
        return [(True, 'Yes'), (False, 'No')]

    def queryset(self, request, queryset):
        if self.value() == None:
            return queryset
        is_registered = self.value() == 'True'
        return queryset.filter(user__isnull=not is_registered).distinct()


class PreferencesFilter(SimpleListFilter):
    title = 'Submitted Preferences'
    parameter_name = 'submitted_preferences'

    def lookups(self, request, model_admin):
        return [(True, 'Yes'), (False, 'No')]

    def queryset(self, request, queryset):
        if self.value() == None:
            return queryset
        submitted_preferences = self.value() == 'True'
        return queryset.annotate(preference_count=Count('project_preferences')).filter(~Q(preference_count=0) if submitted_preferences else Q(preference_count=0)).distinct()


@admin.register(models.Student)
class StudentAdmin(admin.ModelAdmin):
    list_select_related = ['user', 'unit']
    list_display = ['student_id', 'is_registered',
                    'user_link', 'unit_link', 'submitted_preferences', 'preferences_count', 'allocated_project_link', 'allocated_preference_rank']
    list_filter = [RegisteredFilter, PreferencesFilter]
    search_fields = ['student_id']

    form = forms.AdminStudentChangeForm
    add_form = forms.AdminStudentAddForm

    # Add fields/sets
    add_fields = ['unit', 'student_id']
    add_fieldset = (
        ('', {
            'fields': ('unit', 'student_id')
        }),
    )

    # Change fields/sets
    fieldsets = (
        ('', {
            'fields': (('user', 'student_id'),)
        }),
        ('Unit', {
            'description': 'A student object\'s unit cannot be changed. You must create a new student object to add this student to a different unit.',
            'fields': ('unit',)
        }),
        ('Area', {
            'fields': ('area',)
        }),
        ('Allocation', {
            'fields': ('allocated_project',
                       'allocated_preference_rank')
        }),
    )
    readonly_fields = ('unit', 'allocated_preference_rank')

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldset
        return super().get_fieldsets(request, obj)

    def get_fields(self, request, obj=None):
        if obj is None:
            return self.add_fields
        return super().get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return super().get_readonly_fields(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    @admin.display(ordering='user')
    def is_registered(self, student):
        return student.user != None
    is_registered.short_description = 'is registered'
    is_registered.boolean = True

    @admin.display(ordering='project_preferences')
    def submitted_preferences(self, student):
        return student.project_preferences.exists()
    submitted_preferences.short_description = 'submitted preferences'
    submitted_preferences.boolean = True

    @admin.display(ordering='user')
    def user_link(self, student):
        if student.user:
            url = (
                reverse('admin:core_user_changelist')
                + '?'
                + urlencode({
                    'id': str(student.user_id)
                }))
            return format_html('<a href="{}">{}</a>', url, student.user)
        return '-'
    user_link.short_description = 'user'

    @admin.display(ordering='unit')
    def unit_link(self, student):
        url = (
            reverse('admin:core_unit_changelist')
            + '?'
            + urlencode({
                'id': str(student.unit_id)
            }))
        return format_html('<a href="{}">{}</a>', url, student.unit)
    unit_link.short_description = 'unit'

    @admin.display(ordering='preferences_count')
    def preferences_count(self, student):
        url = (
            reverse('admin:core_projectpreference_changelist')
            + '?'
            + urlencode({
                'student_id': str(student.id)
            }))
        return format_html('<a href="{}">{}</a>', url, student.preferences_count)
    preferences_count.short_description = 'no. preference(s)'

    @admin.display(ordering='allocated_project')
    def allocated_project_link(self, student):
        if student.allocated_project:
            url = (
                reverse('admin:core_project_changelist')
                + '?'
                + urlencode({
                    'id': str(student.allocated_project_id)
                }))
            return format_html('<a href="{}">{}</a>', url, student.allocated_project)
        return '-'
    user_link.short_description = 'user'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('project_preferences').annotate(preferences_count=Count('project_preferences', distinct=True))


"""

Projects admin

"""


class ProjectStudentInlineModelAdmin(admin.TabularInline):
    model = models.Student
    verbose_name = 'Allocated Student'

    fields = ['student_id', 'allocated_preference_rank']
    readonly_fields = ['student_id', 'allocated_preference_rank']

    extra = 0

    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'unit_link']
    search_fields = ['name', 'number']

    fields = ('unit', 'number', 'name', 'description',
              'area', 'min_students', 'max_students')

    def get_inlines(self, request, obj=None):
        if obj is not None:
            return [ProjectStudentInlineModelAdmin]
        return super().get_inlines(request, obj)

    @admin.display(ordering='unit')
    def unit_link(self, project):
        url = (
            reverse('admin:core_unit_changelist')
            + '?'
            + urlencode({
                'id': str(project.unit_id)
            }))
        return format_html('<a href="{}">{}</a>', url, project.unit)
    unit_link.short_description = 'unit'


"""

Preferences admin

"""


@admin.register(models.ProjectPreference)
class ProjectPreferenceAdmin(admin.ModelAdmin):
    list_select_related = ['student', 'project', 'student__unit']
    list_display = ['unit_link',  'student_link', 'rank', 'project_link']
    search_fields = ['student__student_id', 'project__number', 'project__name']

    ordering = ['student__unit', 'student', 'rank']

    @admin.display(ordering='student__unit')
    def unit_link(self, projectpreference):
        url = (
            reverse('admin:core_unit_changelist')
            + '?'
            + urlencode({
                'id': str(projectpreference.student.unit_id)
            }))
        return format_html('<a href="{}">{}</a>', url, projectpreference.student.unit)
    unit_link.short_description = 'unit'

    @admin.display(ordering='student')
    def student_link(self, projectpreference):
        url = (
            reverse('admin:core_student_changelist')
            + '?'
            + urlencode({
                'id': str(projectpreference.student_id)
            }))
        return format_html('<a href="{}">{}</a>', url, projectpreference.student.student_id)
    student_link.short_description = 'student'

    @admin.display(ordering='project')
    def project_link(self, projectpreference):
        url = (
            reverse('admin:core_project_changelist')
            + '?'
            + urlencode({
                'id': str(projectpreference.id)
            }))
        return format_html('<a href="{}">{}: {}</a>', url, projectpreference.project.number, projectpreference.project.name)
    project_link.short_description = 'project'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


"""

Area admin

"""


@admin.register(models.Area)
class AreaAdmin(admin.ModelAdmin):
    list_select_related = ['unit']
    list_display = ['name', 'unit_link']
    search_fields = ['unit_link', 'name']

    ordering = ['unit', 'name']

    @admin.display(ordering='student__unit')
    def unit_link(self, area):
        url = (
            reverse('admin:core_unit_changelist')
            + '?'
            + urlencode({
                'id': str(area.unit_id)
            }))
        return format_html('<a href="{}">{}</a>', url, area.unit)
    unit_link.short_description = 'unit'
