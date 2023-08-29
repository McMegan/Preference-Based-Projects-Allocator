from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q, F
from django.utils import timezone

from django.utils.translation import gettext_lazy as _


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

    is_active = models.BooleanField(default=True)
    limit_by_major = models.BooleanField(default=False)

    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='managed_units', limit_choices_to={'is_manager': True})

    OPTIMAL = 'OP'
    FEASIBLE = 'FS'
    INFEASIBLE = 'IF'
    UNBOUNDED = 'UN'
    ABNORMAL = 'AB'
    MODEL_INVALID = 'MI'
    NOT_SOLVED = 'NO'
    ALLOCATION_STATUS = {
        OPTIMAL: 'Successful (Optimal)',
        FEASIBLE: 'Successful (Feasible)',
        INFEASIBLE: 'Failed (Proven Infeasible)',
        UNBOUNDED: 'Failed (Proven Unbounded)',
        ABNORMAL: 'Failed (Abnormal)',
        MODEL_INVALID: 'Failed (Model Invalid)',
        NOT_SOLVED: 'Failed (Not Solved)',
    }
    ALLOCATION_STATUS_CHOICES = [
        (OPTIMAL, ALLOCATION_STATUS[OPTIMAL]),
        (FEASIBLE, ALLOCATION_STATUS[FEASIBLE]),
        (INFEASIBLE, ALLOCATION_STATUS[INFEASIBLE]),
        (UNBOUNDED, ALLOCATION_STATUS[UNBOUNDED]),
        (ABNORMAL, ALLOCATION_STATUS[ABNORMAL]),
        (MODEL_INVALID, ALLOCATION_STATUS[MODEL_INVALID]),
        (NOT_SOLVED, ALLOCATION_STATUS[NOT_SOLVED]),
    ]
    is_allocating = models.BooleanField(default=False)
    allocation_status = models.CharField(
        max_length=2,
        choices=ALLOCATION_STATUS_CHOICES,
        null=True
    )

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

    def preference_submission_set(self) -> bool:
        return self.preference_submission_start != None and self.preference_submission_end != None

    def preference_submission_open(self) -> bool:
        return self.preference_submission_set() and self.preference_submission_started() and not self.preference_submission_ended()

    def preference_submission_started(self) -> bool:
        return timezone.now() > self.preference_submission_start

    def preference_submission_ended(self) -> bool:
        return timezone.now() > self.preference_submission_end

    def is_allocated(self) -> bool:
        return self.completed_allocation() and self.successfully_allocated()

    def completed_allocation(self):
        return not self.is_allocating and self.allocation_status

    def successfully_allocated(self):
        return self.allocation_status in {self.OPTIMAL, self.FEASIBLE}

    def get_allocation_descriptive(self):
        return self.ALLOCATION_STATUS[self.allocation_status]

    def get_allocated_student_count(self):
        if not hasattr(self, 'allocated_student_count'):
            self.allocated_student_count = self.students.filter(
                allocated_project__isnull=False).count()
        return self.allocated_student_count

    def get_unallocated_student_count(self):
        return self.students.count() - self.get_allocated_student_count()

    class Meta:
        ordering = ['code', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'year', 'semester'], name='%(app_label)s_%(class)s_unique'),
            models.CheckConstraint(check=Q(preference_submission_start__isnull=True) | Q(preference_submission_end__isnull=True) | Q(
                preference_submission_start__lt=F('preference_submission_end')), name='preference_submission_start_lt_end', violation_error_message='The preference submission end must be after the preference submission start.')
        ]


class Area(models.Model):
    name = models.CharField(max_length=150)
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='areas')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'name'], name='%(app_label)s_%(class)s_rank_unique', violation_error_message='Each area in a unit must be unique. An area with that name is already included in this unit.'),
        ]


project_min_lte_max_constraint = models.CheckConstraint(check=Q(min_students__isnull=True) | Q(max_students__isnull=True) | Q(
    min_students__lte=F('max_students')), name='min_lte_max', violation_error_message='The minimum number of students for a project must not be less than the maximum number of students.')


class Project(models.Model):
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    min_students = models.IntegerField()
    max_students = models.IntegerField()

    area = models.ManyToManyField(to=Area, related_name='projects')

    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='projects')

    def __str__(self):
        return f'{self.number}: {self.name}'

    def get_preference_counts(self):
        if not hasattr(self, 'preference_counts'):
            self.preference_counts = self.student_preferences.all().values('rank').annotate(
                student_count=Count('student')).order_by('rank')
        return self.preference_counts

    def is_allocated(self) -> bool:
        if not hasattr(self, 'allocated'):
            self.allocated = self.allocated_students.count() > 0
        return self.allocated

    class Meta:
        ordering = ['number', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'number'], name='%(app_label)s_%(class)s_rank_unique', violation_error_message='Each project in a unit must have a unique number. A project with that number is already included in this unit.'),
            project_min_lte_max_constraint
        ]


class Student(models.Model):
    student_id = models.CharField(max_length=15)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='enrollments', limit_choices_to={'is_student': True}, null=True, blank=True)
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='students')

    allocated_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, related_name='allocated_students')
    allocated_preference_rank = models.PositiveIntegerField(null=True)

    area = models.ManyToManyField(to=Area, related_name='students')

    def __str__(self):
        return self.student_id

    def get_is_registered(self):
        if not hasattr(self, 'is_registered'):
            self.is_registered = self.user != None
        return self.is_registered

    class Meta:
        ordering = ['student_id']
        constraints = [
            models.UniqueConstraint(
                fields=['student_id', 'unit'], name='%(app_label)s_%(class)s_unique'),
        ]


class ProjectPreference(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='student_preferences')
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='project_preferences')
    rank = models.PositiveIntegerField()

    def __str__(self):
        return f'Student_{self.student}-Unit_{self.student.unit.code}-Rank_{self.rank}-Project_{self.project.number}'

    class Meta:
        ordering = ['student__student_id', 'rank', 'project_id',]
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'rank'], name='%(app_label)s_%(class)s_rank_unique'),
            models.UniqueConstraint(
                fields=['student', 'project'], name='%(app_label)s_%(class)s_project_unique')
        ]
