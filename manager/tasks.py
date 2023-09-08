import base64
import tempfile
import os

from django.core.mail import EmailMultiAlternatives

from celery import shared_task

from core import models
from .allocator import Allocator
from . import export
from . import upload


@shared_task
def start_allocation(unit_id, manager_id, results_url):
    unit = models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'students').prefetch_related('students__project_preferences').first()

    Allocator(unit=unit)

    # Email with result...??
    manager = models.User.objects.filter(pk=manager_id).first()
    if manager.email != None:
        email_message = f'The allocation of students to projects for {unit.name} was successful.'
        email_message_html = f'The allocation of students to projects for {unit.name} was successful. <a href="{results_url}">View the results of the allocation</a>.'
        if not unit.allocation_status:
            email_message = f'The allocation of students to projects for {unit.name} failed.'
            email_message_html = f'The allocation of students to projects for {unit.name} failed.'
        email = EmailMultiAlternatives(
            subject=f'{unit.name}: Project Allocation Finished',
            body=email_message,
            to=[manager.email],
        )
        email.attach_alternative(email_message_html, 'text/html')
        result = email.send(fail_silently=False)
        return 'Email successful' if result else 'Email failed', unit.get_allocation_descriptive()

    return 'No email specified', unit.get_allocation_descriptive()


@shared_task
def email_allocation_results_csv_task(*args, **kwargs):
    return export.email_allocation_results_csv(*args, **kwargs)


@shared_task
def email_preferences_csv_task(*args, **kwargs):
    return export.email_preferences_csv(*args, **kwargs)


@shared_task
def upload_projects_list_task(*args, **kwargs):
    return upload.upload_projects_list(*args, **kwargs)


@shared_task
def upload_students_list_task(*args, **kwargs):
    return upload.upload_students_list(*args, **kwargs)


@shared_task
def upload_preferences_list_task(*args, **kwargs):
    return upload.upload_preferences_list(*args, **kwargs)
