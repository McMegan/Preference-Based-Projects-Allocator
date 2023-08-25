import datetime
import csv
from io import StringIO

from django.core.mail import EmailMessage
from django.http import HttpResponse

from core import models


def generate_allocation_results_csv(unit):
    file_output = StringIO()
    # Write to file
    writer = csv.writer(file_output, delimiter=',', quoting=csv.QUOTE_ALL)

    # Add headers to file
    writer.writerow(['student_id', 'project_number', 'project_name'])
    # Write students to file
    for student in unit.enrolled_students.all():
        if student.assigned_project:
            writer.writerow(
                [student.student_id, student.assigned_project.number, student.assigned_project.name])
        else:
            writer.writerow(
                [student.student_id, '', ''])

    file_output.seek(0)
    return file_output


def generate_allocation_results_filename(unit):
    return datetime.datetime.now().strftime('%Y%m%d-%H_%M_%S')+f'-{unit.code.lower()}-project-allocation.csv'


def download_allocation_results_csv(unit_id):
    unit = models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'enrolled_students').prefetch_related('enrolled_students__project_preferences').first()

    response = HttpResponse(
        content_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{generate_allocation_results_filename(unit)}"'},
        content=generate_allocation_results_csv(unit)
    )

    return response


def email_allocation_results_csv(unit_id, manager_id):
    unit = models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'enrolled_students').prefetch_related('enrolled_students__project_preferences').first()

    attachment = generate_allocation_results_csv(unit)

    # Email with attached file
    manager = models.User.objects.filter(pk=manager_id).first()
    if manager.email != None:
        email = EmailMessage(
            subject=f'{unit.name}: Project Allocation Results',
            body=f'The results of the allocation of students to projects for {unit.name} are attached.',
            from_email=None,
            to=[manager.email]
        )
        email.attach(generate_allocation_results_filename(
            unit), attachment.read(), 'text/csv')
        result = email.send(fail_silently=False)
        return 'Email successful' if result else 'Email failed'
    return 'No email specified'
