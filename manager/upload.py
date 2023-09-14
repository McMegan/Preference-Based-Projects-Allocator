import csv
import base64
import tempfile
import os

from core import models


def upload_projects_list(unit_id, manager_id, file_bytes_base64_str, override_list, identifier_column, name_column, min_students_column, max_students_column, description_column, area_column):
    file_bytes_base64 = file_bytes_base64_str.encode('utf-8')
    file_bytes = base64.b64decode(file_bytes_base64)
    # Write the file to a temporary location, deletion is guaranteed
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, 'blank.zip')
        with open(tmp_file, 'wb') as file:
            file.write(file_bytes)
        with open(tmp_file, 'r', encoding='utf-8-sig') as file:
            # Process the file
            unit = models.Unit.objects.get(pk=unit_id)
            unit_projects = models.Project.objects.filter(unit_id=unit_id)

            csv_data = csv.DictReader(file, delimiter=',')

            project_create_list = []
            project_update_list = []
            area_create_list = []
            project_areas_list = []
            for row in csv_data:
                if not all(row[field] == '' for field in row):
                    project = models.Project()
                    project.identifier = row[identifier_column].strip()
                    project.name = row[name_column].strip()
                    project.min_students = row[min_students_column].strip()
                    project.max_students = row[max_students_column].strip()
                    project.unit_id = unit_id
                    project.description = row[description_column].strip(
                    ) if description_column != '' and row[description_column] and row[description_column].strip() != '' else None
                    if area_column != '' and row[area_column] != None and row[area_column].strip() != '':
                        areas = row[area_column].split(';')
                        for area in areas:
                            area = area.strip()
                            area = models.Area(name=area, unit=unit)
                            area_create_list.append(area)
                            project_areas_list.append((project, area))
                    existing_project = unit_projects.filter(
                        identifier=project.identifier)
                    if existing_project.exists():
                        unit_projects = unit_projects.exclude(
                            identifier=project.identifier)
                        no_update_project = existing_project.filter(
                            name=project.name, min_students=project.min_students, max_students=project.max_students, description=project.description)
                        if not no_update_project.exists():
                            project.id = existing_project.first().id
                            project_update_list.append(project)
                    else:
                        project_create_list.append(project)

            if override_list:
                unit_projects.delete()
            models.Project.objects.bulk_create(
                project_create_list,
                ignore_conflicts=True
            )
            models.Project.objects.bulk_update(
                project_update_list,
                fields=['name', 'description', 'min_students', 'max_students'],
            )
            models.Area.objects.bulk_create(
                area_create_list, ignore_conflicts=True)

            # Add area
            project_areas_create = []
            project_areas_model = models.Project.area.through
            for project, area in project_areas_list:
                project = unit.projects.filter(identifier=project.identifier)
                area = unit.areas.filter(name=area.name)
                if project.exists() and area.exists():
                    project = project.first()
                    area = area.first()
                    project_areas_create.append(project_areas_model(
                        project_id=project.id, area_id=area.id))

            project_areas_model.objects.bulk_create(
                project_areas_create, ignore_conflicts=True)

            return 'Success'
        return 'Failed'


def upload_students_list(unit_id, manager_id, file_bytes_base64_str, override_list, student_id_column, student_name_column, area_column):
    file_bytes_base64 = file_bytes_base64_str.encode('utf-8')
    file_bytes = base64.b64decode(file_bytes_base64)
    # Write the file to a temporary location, deletion is guaranteed
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, 'blank.zip')
        with open(tmp_file, 'wb') as file:
            file.write(file_bytes)
        with open(tmp_file, 'r', encoding='utf-8-sig') as file:
            # Process the file
            unit = models.Unit.objects.get(pk=unit_id)
            unit_students = models.Student.objects.filter(unit_id=unit_id)

            csv_data = csv.DictReader(file, delimiter=',')

            student_create_list = []
            area_create_list = []
            student_areas_list = []
            for row in csv_data:
                if not all(row[field] == '' for field in row):
                    student = models.Student()
                    student.student_id = row[student_id_column].strip()
                    student.unit_id = unit_id
                    if student_name_column != '' and row[student_name_column].strip():
                        student.name = row[student_name_column].strip()
                    # Check if user account exists for student
                    user = models.User.objects.filter(
                        username=row[student_id_column])
                    if user.exists():
                        student.user_id = user.first().id
                    if area_column != '' and row[area_column] != '' and row[area_column] != None:
                        areas = row[area_column].split(';')
                        for area in areas:
                            area = area.strip()
                            area = models.Area(
                                name=area, unit=unit)
                            area_create_list.append(area)
                            student_areas_list.append((student, area))
                    existing_student = unit_students.filter(
                        student_id=student.student_id)
                    if existing_student.exists():
                        unit_students = unit_students.exclude(
                            student_id=student.student_id)
                    if not existing_student.exists() or existing_student.first().user_id != student.user_id:
                        student_create_list.append(student)

            if override_list:
                # Clear previous students
                unit_students.delete()
            models.Student.objects.bulk_create(
                student_create_list,
                unique_fields=['student_id', 'unit_id'],
                update_conflicts=True,
                update_fields=['user']
            )
            models.Area.objects.bulk_create(
                area_create_list, ignore_conflicts=True)

            # Add area
            student_areas_create = []
            student_areas_model = models.Student.area.through
            for student, area in student_areas_list:
                student = unit.students.filter(student_id=student.student_id)
                area = unit.areas.filter(name=area.name)
                if student.exists() and area.exists():
                    student = student.first()
                    area = area.first()
                    student_areas_create.append(student_areas_model(
                        student_id=student.id, area_id=area.id))

            student_areas_model.objects.bulk_create(
                student_areas_create, ignore_conflicts=True)
            return 'Success'
        return 'Failed'


def upload_preferences_list(unit_id, manager_id, file_bytes_base64_str, preference_rank_column, student_id_column, project_identifier_column):
    file_bytes_base64 = file_bytes_base64_str.encode('utf-8')
    file_bytes = base64.b64decode(file_bytes_base64)
    # Write the file to a temporary location, deletion is guaranteed
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, 'blank.zip')
        with open(tmp_file, 'wb') as file:
            file.write(file_bytes)
        with open(tmp_file, 'r', encoding='utf-8-sig') as file:
            # Process the file
            unit = models.Unit.objects.get(pk=unit_id)
            unit_preferences = models.ProjectPreference.objects.prefetch_related('project').filter(
                project__unit_id=unit_id)

            csv_data = csv.DictReader(file, delimiter=',')

            unit_projects = unit.projects
            unit_students = unit.students

            preference_create_list = []
            student_update_list = []
            for row in csv_data:
                if not all(row[field] == '' for field in row):
                    student_id = row[student_id_column].strip()
                    project_identifier = row[project_identifier_column].strip()
                    student = unit_students.filter(student_id=student_id)
                    project = unit_projects.filter(
                        identifier=project_identifier)
                    rank = row[preference_rank_column].strip()
                    if student.exists() and project.exists():
                        student = student.first()
                        project = project.first()
                        if unit_preferences.filter(student=student, project=project, rank=rank).exists():
                            unit_preferences = unit_preferences.exclude(
                                student=student, project=project, rank=rank)
                        else:
                            preference = models.ProjectPreference()
                            preference.rank = rank
                            preference.student = student
                            preference.project = project
                            if student.allocated_project == project:
                                student.allocated_preference_rank = preference.rank
                                student_update_list.append(student)
                            preference_create_list.append(preference)

            unit_preferences.delete()
            models.ProjectPreference.objects.bulk_create(
                preference_create_list,
                ignore_conflicts=True
            )
            models.Student.objects.bulk_update(
                student_update_list,
                fields=['allocated_preference_rank']
            )
            return 'Success'
        return 'Failed'
