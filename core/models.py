from typing import Iterable, Optional
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


def ordinal(n: int) -> str:
    suffixes = ['st', 'nd', 'rd']
    suffix = 'th'
    unit = int(str(n)[-1])
    tens = int(str(n)[-2]) if n >= 10 else 0
    if tens != 1 and unit > 0 and unit <= 3:
        suffix = suffixes[unit - 1]
    return str(n) + suffix


class User(AbstractUser):
    is_manager = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)

    def __str__(self):
        if self.get_full_name() == '':
            return self.username
        return f'{self.get_full_name()} ({self.username})'

    def save(self, *args, **kwargs):
        if self.is_manager:
            self.is_staff = True
            # Give certain permissions
        super().save(*args, **kwargs)


class Unit(models.Model):
    code = models.CharField(max_length=15)
    name = models.CharField(max_length=255)
    year = models.CharField(max_length=4)
    semester = models.CharField(max_length=50)
    preference_submission_start = models.DateTimeField(null=True, blank=True)
    preference_submission_end = models.DateTimeField(null=True, blank=True)
    minimum_preference_limit = models.IntegerField(null=True, blank=True)

    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='managed_units', limit_choices_to={'is_manager': True})
    students = models.ManyToManyField(
        User, related_name='enrolled_units', limit_choices_to={'is_student': True}, blank=True)

    def __str__(self):
        return f'{self.code}: {self.name}'

    def clean(self) -> None:
        errors = {}
        if self.manager != None and not self.manager.is_manager:
            errors['manager'] = [
                'The manager must be a user with the manager flag.']
        if errors != {}:
            raise ValidationError(errors)
        return super().clean()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'year', 'semester'], name='%(app_label)s_%(class)s_unique')
        ]


class Project(models.Model):
    number = models.CharField(max_length=15)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, null=True, blank=True)
    min_students = models.IntegerField()
    max_students = models.IntegerField()

    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='projects')

    def __str__(self):
        return f'{self.number}: {self.name} ({self.unit.code})'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'number'], name='%(app_label)s_%(class)s_rank_unique'),
        ]


class ProjectPreference(models.Model):
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='student_project_preferences')
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='student_preferences')
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='project_preferences', limit_choices_to={'is_student': True})
    rank = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.student}\'s {self.unit.code} preference {ordinal(self.rank)}'

    def clean(self) -> None:
        errors = {}
        if hasattr(self, 'unit') and hasattr(self, 'project') and not self.unit.id == self.project.unit.id:
            errors['project'] = [
                'The project must belong to the specified unit.']
        if hasattr(self, 'unit') and hasattr(self, 'student') and not self.student.enrolled_units.filter(pk=self.unit.id).exists():
            errors['student'] = [
                'The student must be enrolled in the specified unit.']

        if hasattr(self, 'student') and hasattr(self, 'unit') and hasattr(self, 'rank'):
            # Ensure that the preference rank being entered aligns with the students existing preferences for this unit
            for preference in self.student.project_preferences.filter(unit_id=self.unit.id):
                if self.id != preference.id and self.rank == preference.rank:
                    errors['rank'] = [
                        'The student already has a preference at this rank for the specified unit.']

                print(self.rank)
                print(preference.rank)
                print(self.rank == preference.rank)

        # raise ValidationError('testing')
        if errors != {}:
            raise ValidationError(errors)
        return super().clean()

    class Meta:
        ordering = ['unit_id', 'student_id', 'rank']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'unit', 'rank'], name='%(app_label)s_%(class)s_rank_unique'),
            models.UniqueConstraint(
                fields=['student', 'unit', 'project'], name='%(app_label)s_%(class)s_project_unique')
        ]


class ProjectAssignment(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='members')
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='assigned_projects', limit_choices_to={'is_student': True})
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='project_assignments')

    def __str__(self):
        return f'Project Assignment for {self.student} in {self.unit.code}'

    def clean(self) -> None:
        errors = {}
        if hasattr(self, 'unit') and hasattr(self, 'project') and not self.unit.id == self.project.unit.id:
            errors['project'] = [
                'The project must belong to the specified unit.']
        if hasattr(self, 'unit') and hasattr(self, 'student') and not self.student.enrolled_units.filter(pk=self.unit.id).exists():
            errors['student'] = [
                'The student must be enrolled in the specified unit.']

        if errors != {}:
            raise ValidationError(errors)
        return super().clean()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'unit'], name='%(app_label)s_%(class)s_unique')
        ]
