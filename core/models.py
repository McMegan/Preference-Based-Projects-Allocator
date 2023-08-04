from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_manager = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'number'], name="%(app_label)s_%(class)s_rank_unique"),
        ]


class ProjectPreference(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='student_preferences')
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='project_preferences', limit_choices_to={'is_student': True})
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='student_project_preferences')
    rank = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'unit', 'rank'], name="%(app_label)s_%(class)s_rank_unique"),
            models.UniqueConstraint(
                fields=['student', 'unit', 'project'], name="%(app_label)s_%(class)s_project_unique")
        ]


class ProjectAssignment(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='members')
    student = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='assigned_projects', limit_choices_to={'is_student': True})
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='project_assignments')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'unit'], name="%(app_label)s_%(class)s_unique")
        ]
