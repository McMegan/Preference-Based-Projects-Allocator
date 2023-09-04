from django.core.mail import EmailMessage, EmailMultiAlternatives

from celery import shared_task

from core import models
from .allocator import Allocator
from .export import *


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
            from_email=None,
            to=[manager.email],
        )
        email.attach_alternative(email_message_html, 'text/html')
        result = email.send(fail_silently=False)
        return 'Email successful' if result else 'Email failed', models.Unit.ALLOCATION_STATUS[unit.allocation_status]

    return 'No email specified', models.Unit.ALLOCATION_STATUS[unit.allocation_status]


@shared_task
def email_allocation_results(unit_id, manager_id):
    return email_allocation_results_csv(unit_id, manager_id)


@shared_task
def email_preferences(unit_id, manager_id):
    return email_preferences_csv(unit_id, manager_id)
