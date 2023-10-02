from django import forms
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q, F
from django.utils import timezone

from django.utils.translation import gettext_lazy as _


from django_celery_results.models import TaskResult


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)

    is_manager = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        save = super().save(*args, **kwargs)
        # Link to user
        student_objects = Student.objects.filter(student_id=self.username)
        if student_objects.exists():
            for student in student_objects:
                student.user = self
                student.save()
        return save


class Unit(models.Model):
    code = models.CharField(max_length=15)
    name = models.CharField(max_length=255)
    year = models.CharField(max_length=4)
    semester = models.CharField(max_length=50)

    preference_submission_start = models.DateTimeField(null=True, blank=True)
    preference_submission_end = models.DateTimeField(null=True, blank=True)

    minimum_preference_limit = models.IntegerField(null=True, blank=True)
    maximum_preference_limit = models.IntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    limit_by_major = models.BooleanField(default=False)

    manager = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, related_name='managed_units', limit_choices_to={'is_manager': True})

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
    allocation_status = models.CharField(
        max_length=2,
        choices=ALLOCATION_STATUS_CHOICES,
        null=True,
        blank=True
    )

    START_ALLOCATION_TASK = 'ALLOC'
    START_ALLOCATION_TASK_NAME = 'Start Allocation'
    EMAIL_ALLOCATION_RESULTS_TASK = 'EMALL'
    EMAIL_ALLOCATION_RESULTS_TASK_NAME = 'Email Allocation Results'
    EMAIL_PREFERENCES_TASK = 'EPREF'
    EMAIL_PREFERENCES_TASK_NAME = 'Email Preferences List'
    UPLOAD_PROJECTS_TASK = 'UPROJ'
    UPLOAD_PROJECTS_TASK_NAME = 'Upload Projects List'
    UPLOAD_STUDENTS_TASK = 'USTUD'
    UPLOAD_STUDENTS_TASK_NAME = 'Upload Students List'
    UPLOAD_PREFERENCES_TASK = 'UPREF'
    UPLOAD_PREFERENCES_TASK_NAME = 'Upload Preferences List'
    TASK_NAME = {
        START_ALLOCATION_TASK: START_ALLOCATION_TASK_NAME,
        EMAIL_ALLOCATION_RESULTS_TASK: EMAIL_ALLOCATION_RESULTS_TASK_NAME,
        EMAIL_PREFERENCES_TASK: EMAIL_PREFERENCES_TASK_NAME,
        UPLOAD_PROJECTS_TASK: UPLOAD_PROJECTS_TASK_NAME,
        UPLOAD_STUDENTS_TASK: UPLOAD_STUDENTS_TASK_NAME,
        UPLOAD_PREFERENCES_TASK: UPLOAD_PREFERENCES_TASK_NAME,
    }
    TASK_CHOICES = [
        (START_ALLOCATION_TASK, TASK_NAME[START_ALLOCATION_TASK]),
        (EMAIL_ALLOCATION_RESULTS_TASK,
         TASK_NAME[EMAIL_ALLOCATION_RESULTS_TASK]),
        (EMAIL_PREFERENCES_TASK, TASK_NAME[EMAIL_PREFERENCES_TASK]),
        (UPLOAD_PROJECTS_TASK, TASK_NAME[UPLOAD_PROJECTS_TASK]),
        (UPLOAD_STUDENTS_TASK, TASK_NAME[UPLOAD_STUDENTS_TASK]),
        (UPLOAD_PREFERENCES_TASK, TASK_NAME[UPLOAD_PREFERENCES_TASK]),
    ]
    task_name = models.CharField(
        max_length=5,
        choices=TASK_CHOICES,
        null=True,
        blank=True,
        verbose_name='Task Name',
        help_text='Name of the Task which was run'
    )
    task_id = models.CharField(
        unique=True,
        null=True,
        blank=True,
        max_length=255,
        verbose_name='Task ID',
        help_text='Celery ID for the Task that was run')

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

    def get_celery_task(self):
        if not hasattr(self, 'celery_task'):
            task = TaskResult.objects.filter(task_id=self.task_id)
            if task.exists():
                self.celery_task = task.first()
            else:
                self.celery_task = None
        return self.celery_task

    def task_ready(self):
        if self.task_id:
            if self.get_celery_task():
                return self.get_celery_task()
                # .status == 'SUCCESS'
            else:
                # Task not in results bc its not completed
                return False
        return True

    def preference_submission_set(self) -> bool:
        return self.preference_submission_start != None and self.preference_submission_end != None

    def preference_submission_open(self) -> bool:
        return self.preference_submission_set() and self.preference_submission_started() and not self.preference_submission_ended()

    def preference_submission_started(self) -> bool:
        return self.preference_submission_set() and timezone.now() > self.preference_submission_start

    def preference_submission_ended(self) -> bool:
        return self.preference_submission_set() and timezone.now() > self.preference_submission_end

    def get_preference_submission_start(self):
        return self.preference_submission_start.strftime('%a %d %b %Y, %I:%M%p')

    def get_preference_submission_end(self):
        return self.preference_submission_end.strftime('%a %d %b %Y, %I:%M%p')

    def is_allocating(self):
        if not hasattr(self, 'allocating'):
            self.allocating = False
        if self.task_id and self.task_name and self.task_name == Unit.START_ALLOCATION_TASK:
            self.allocating = not self.task_ready()
        return self.allocating

    def is_allocated(self) -> bool:
        return self.completed_allocation() and self.successfully_allocated()

    def completed_allocation(self) -> bool:
        return not self.is_allocating() and self.allocation_status is not None

    def successfully_allocated(self) -> bool:
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

    def calculate_project_spaces(self):
        self.too_few_students = None
        self.min_project_spaces = None
        self.too_many_students = None
        self.max_project_spaces = None

        projects_list = self.projects.all()
        if projects_list.exists():
            min_spaces = []
            max_spaces = []
            for project in projects_list.all():
                min_spaces.append(project.min_students)
                max_spaces.append(project.max_students)

            students_count = self.students.count()
            self.too_few_students = min(min_spaces) > students_count
            self.min_project_spaces = min(min_spaces)
            self.too_many_students = sum(max_spaces) < students_count
            self.max_project_spaces = sum(max_spaces)
            return True
        return False

    def get_too_few_students(self):
        if not hasattr(self, 'too_few_students'):
            self.calculate_project_spaces()
        return self.too_few_students

    def get_min_project_spaces(self):
        if not hasattr(self, 'min_project_spaces'):
            self.calculate_project_spaces()
        return self.min_project_spaces

    def get_too_many_students(self):
        if not hasattr(self, 'too_many_students'):
            self.calculate_project_spaces()
        return self.too_many_students

    def get_max_project_spaces(self):
        if not hasattr(self, 'max_project_spaces'):
            self.calculate_project_spaces()
        return self.max_project_spaces

    class Meta:
        ordering = ['code', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['manager', 'code', 'year', 'semester'], name='%(app_label)s_%(class)s_unique'),
            models.CheckConstraint(check=Q(preference_submission_start__isnull=True) | Q(preference_submission_end__isnull=True) | Q(
                preference_submission_start__lt=F('preference_submission_end')), name='preference_submission_start_lt_end', violation_error_message='The preference submission end must be after the preference submission start.'),
            models.CheckConstraint(check=Q(minimum_preference_limit__isnull=True) | Q(maximum_preference_limit__isnull=True) | Q(
                minimum_preference_limit=F('maximum_preference_limit')) | Q(
                minimum_preference_limit__lt=F('maximum_preference_limit')), name='minimum_preference_limit_lt_max', violation_error_message='The minimum preference limit must be less than or equal to the maximum preference limit.')
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
    # named number rather than ID as ID is reserved for PK
    identifier = models.CharField(max_length=20)
    # models.PositiveSmallIntegerField()
    # models.CharField(max_length=20)

    name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    min_students = models.IntegerField()
    max_students = models.IntegerField()

    area = models.ManyToManyField(to=Area, related_name='projects')

    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='projects')

    def __str__(self):
        return f'{self.identifier}: {self.name}'

    def get_preference_counts(self):
        if not hasattr(self, 'preference_counts'):
            self.preference_counts = self.student_preferences.values('rank').annotate(
                student_count=Count('student')).order_by('rank')
        return self.preference_counts

    def is_allocated(self) -> bool:
        if not hasattr(self, 'allocated'):
            self.allocated = self.allocated_students.count() > 0
        return self.allocated

    class Meta:
        ordering = ['unit', 'identifier']
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'identifier'], name='%(app_label)s_%(class)s_id_unique', violation_error_message='Each project in a unit must have a unique ID. A project with that ID is already included in this unit.'),
            project_min_lte_max_constraint
        ]


class Student(models.Model):
    student_id = models.CharField(max_length=15)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='enrollments', limit_choices_to={'is_student': True}, null=True, blank=True)
    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='students')

    allocated_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, related_name='allocated_students', blank=True)
    allocated_preference_rank = models.PositiveIntegerField(
        null=True, blank=True)

    area = models.ManyToManyField(to=Area, related_name='students', blank=True)

    name = models.CharField(_("name"), max_length=150, blank=True)

    def __str__(self):
        return self.student_id

    def get_is_registered(self):
        if not hasattr(self, 'is_registered'):
            self.is_registered = self.user != None
        return self.is_registered

    def clean(self):
        if self.user != None and self.student_id != None and self.student_id != '':
            if self.user.username != self.student_id:
                raise forms.ValidationError(
                    'The chosen user\'s username must match the specified student ID.')
        return super().clean()

    def save(self, *args, **kwargs):
        if self.user == None and self.student_id != '':
            # Link to user
            user = User.objects.filter(username=self.student_id)
            if user.exists():
                self.user = user.first()
        elif self.user != None and self.student_id == '':
            self.student_id = self.user.username
        if self.allocated_project:
            allocated_project_pref = self.project_preferences.filter(
                project_id=self.allocated_project.id)
            self.allocated_preference_rank = allocated_project_pref.first(
            ).rank if allocated_project_pref.exists() else None
        else:
            self.allocated_preference_rank = None
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['student_id']
        constraints = [
            models.UniqueConstraint(
                fields=['student_id', 'unit'], name='%(app_label)s_%(class)s_unique_id'),
            models.UniqueConstraint(
                fields=['user', 'unit'], name='%(app_label)s_%(class)s_unique_user'),
        ]


class ProjectPreference(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='student_preferences')
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='project_preferences')
    rank = models.PositiveIntegerField()

    def __str__(self):
        return f'Student_{self.student}-Unit_{self.student.unit.code}-Rank_{self.rank}-Project_{self.project.identifier}'

    class Meta:
        ordering = ['student__student_id', 'rank', 'project_id',]
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'rank'], name='%(app_label)s_%(class)s_rank_unique'),
            models.UniqueConstraint(
                fields=['student', 'project'], name='%(app_label)s_%(class)s_project_unique')
        ]
