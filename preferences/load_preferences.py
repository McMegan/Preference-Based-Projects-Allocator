from core import models

from . import preferences_full


def load_prefs():
    print('\n\n ########## ')

    load_prefs_for_unit(unit_code='FULL00001',
                        pref_list=preferences_full.pref_list)

    print(' ##########\n\n ')


def load_prefs_for_unit(unit_code, pref_list):
    return
    print(f'\n ##### START: {unit_code} #####\n ')

    unit = models.Unit.objects.get(code=unit_code)
    students = unit.enrolled_students.all()
    student_count = students.count()
    projects = unit.projects.all()
    project_count = projects.count()

    print(projects)

    for student_index in range(0, min(student_count, len(pref_list))):
        student = students[student_index]
        preferences = pref_list[student_index].split(',')
        for rank, project_index in enumerate(preferences):
            project_index = int(project_index)
            if project_index < project_count:
                project = projects[project_index]
                preference = models.ProjectPreference(
                    unit_id=unit.id, project_id=project.id, student_id=student.user.id, rank=rank+1)
                print(preference)
            else:
                print(f'NO PROJECT: {project_index}')

    print(f'\n ###### END: {unit_code} ######\n')
