from django.db.models import Count

from core import models

from . import preferences_full

LOAD_PREFS = False


def load_prefs():
    if LOAD_PREFS:
        print('\n\n ########## ')

        load_prefs_for_unit(unit_code='SMALL',
                            pref_list=preferences_full.pref_list)

        load_prefs_for_unit(unit_code='FULL00001',
                            pref_list=preferences_full.pref_list)

        print(' ##########\n\n ')


def load_prefs_for_unit(unit_code, pref_list):
    result = f'\n ##### {unit_code}: '

    unit = models.Unit.objects.get(code=unit_code)
    students = unit.enrolled_students.all()
    student_count = students.count()

    projects = unit.projects.all()
    project_count = projects.count()

    if students.annotate(preference_count=Count(
            'project_preferences')).filter(preference_count__gt=0).count() == 0:
        result = result + 'SET PREFS'

        all_preferences = []
        for student_index in range(0, min(student_count, len(pref_list))):
            student = students[student_index]
            preferences = pref_list[student_index].split(',')
            for rank, project_index in enumerate(preferences):
                project_index = int(project_index) - 1
                if project_index < project_count:
                    project = projects[project_index]
                    preference = models.ProjectPreference(
                        project_id=project.id, student_id=student.id, rank=rank+1)
                    all_preferences.append(preference)
                else:
                    print(f'NO PROJECT: {project_index}')

        models.ProjectPreference.objects.bulk_create(all_preferences)
    else:
        result = result + 'ALREADY SET PREFS'

    result = result + ' ######\n'

    print(result)
