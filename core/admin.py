from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html, urlencode
from django.db.models import Count
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.models import Group

from . import models

admin.site.unregister(Group)


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + \
        ('is_manager', 'is_student', 'last_login')
    list_filter = BaseUserAdmin.list_filter + ('is_manager', 'is_student')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('User type', {'fields': ('is_manager', 'is_student')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('User type', {'fields': ('is_manager', 'is_student')}),
    )

    readonly_fields = [
        'date_joined', 'last_login'
    ]

    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(models.Unit)
class UnitAdmin(admin.ModelAdmin):
    autocomplete_fields = ['manager']
    list_select_related = ['manager']
    list_display = ['id', 'code', 'name', 'year', 'semester', 'manager_link', 'students_count', 'student_list', 'preference_submission_start',
                    'preference_submission_end', 'minimum_preference_limit']
    search_fields = ['code', 'name', 'year', 'semester']

    @admin.display(ordering='manager_id')
    def manager_link(self, unit):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse('admin:core_user_change', args=(unit.manager.pk,)),
            unit.manager
        ))
    manager_link.short_description = 'manager'

    def student_list(self, unit):
        return [student for student in unit.students.all()]

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

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            students_count=Count('students')
        )


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'number', 'description',
                    'min_students', 'max_students']
    search_fields = ['name', 'number']
    # add unit?


@admin.register(models.ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'unit', 'project', 'student']
    autocomplete_fields = ['unit', 'project', 'student']
    fieldsets = (
        (None, {'fields': ('unit', 'project', 'student')}),
    )


@admin.register(models.ProjectPreference)
class ProjectPreferenceAdmin(admin.ModelAdmin):
    list_display = ['rank', 'unit', 'project', 'student']

    # No staff should be able to alter preferences...?
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
