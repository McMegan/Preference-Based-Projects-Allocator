import random

from django.db.models import Count

from core import models
from . import preferences_full
from . import preferences_big

LOAD_PREFS = False
LOAD_STUDENTS = False
LOAD_PROJECTS = False
LOAD_BIG = False


def load_data():
    if LOAD_BIG:
        load_big_unit()
    if LOAD_STUDENTS:
        pass
    if LOAD_PROJECTS:
        pass
    if LOAD_PREFS:
        # load_prefs(unit_code='SMALL',pref_list=preferences_full.pref_list, replace=True)
        load_prefs(unit_code='FULL00001',
                   pref_list=preferences_full.pref_list, replace=True)


def load_big_unit():
    n_students = 500
    n_projects = 100
    n_no_prefs = n_students * 0.05
    min_prefs = 5
    max_prefs = 15

    load_students(unit_code='BIG', n_students=n_students)
    load_projects(unit_code='BIG', n_projects=n_projects)

    pref_list = []
    for student_num in range(0, n_students):
        if student_num < n_students - n_no_prefs:
            numPrefs = random.randint(min_prefs, max_prefs)
            prefs = random.sample(range(1, n_projects+1), numPrefs)
            pref_list.append(prefs)

    load_prefs(unit_code='BIG',
               pref_list=pref_list, replace=True, csv_prefs=False)


def load_students(unit_code, n_students, replace=False):
    unit = models.Unit.objects.get(code=unit_code)
    students = unit.students.all()
    student_count = students.count()
    if replace:
        students.delete()
        student_count = 0

    new_students = []
    for student_num in range(student_count + 1, n_students + 1):
        new_students.append(models.Student(
            student_id=f'stu{student_num}', unit=unit))
    models.Student.objects.bulk_create(new_students)


def load_projects(unit_code, n_projects, replace=False):
    unit = models.Unit.objects.get(code=unit_code)
    projects = unit.projects.all()
    project_count = projects.count()
    if replace:
        projects.delete()
        project_count = 0

    new_projects = []
    for project_number in range(project_count + 1, n_projects + 1):
        new_projects.append(models.Project(
            number=project_number, name=f'Project {project_number}', min_students=4, max_students=6, unit=unit))
    models.Project.objects.bulk_create(new_projects)


def load_prefs(unit_code, pref_list, replace=False, csv_prefs=True):
    result = f'\n ##### {unit_code}: '

    unit = models.Unit.objects.get(code=unit_code)
    students = unit.students.all()
    student_count = students.count()

    projects = unit.projects.all()
    project_count = projects.count()

    if replace:
        for student in students:
            student.project_preferences.all().delete()

    if replace or students.annotate(preference_count=Count(
            'project_preferences')).filter(preference_count__gt=0).count() == 0:
        result = result + 'SET PREFS'

        all_preferences = []
        for student_index in range(0, min(student_count, len(pref_list))):
            rank = 1
            student = students[student_index]
            preferences = pref_list[student_index].split(
                ',') if csv_prefs else pref_list[student_index]
            for project_index in preferences:
                project_index = int(project_index) - 1
                if project_index < project_count:
                    project = projects[project_index]
                    preference = models.ProjectPreference(
                        project_id=project.id, student_id=student.id, rank=rank)
                    all_preferences.append(preference)
                    rank += 1
                else:
                    print(f'NO PROJECT: {project_index}')

        models.ProjectPreference.objects.bulk_create(all_preferences)
    else:
        result = result + 'ALREADY SET PREFS'

    result = result + ' ######\n'

    print(result)
