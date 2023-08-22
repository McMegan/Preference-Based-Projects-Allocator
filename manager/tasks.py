import csv

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.http import HttpResponse
from django.urls import reverse

from celery import shared_task

from core import models
from .allocator import Allocator


@shared_task
def start_allocation(unit_id, manager_id, results_url):
    unit = models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'enrolled_students').prefetch_related('enrolled_students__project_preferences').first()

    allocator = Allocator(unit=unit)

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
        email.attach_alternative(email_message_html, "text/html")
        email.send()

    del allocator
    return models.Unit.ALLOCATION_STATUS[unit.allocation_status]


"""
@shared_task
def export_allocation_results(unit_id, manager_id):
    unit = models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'enrolled_students').prefetch_related('enrolled_students__project_preferences').first()

    response = HttpResponse(
        content_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{unit.code}-project-allocation.csv"'},
    )

    # Write to file
    writer = csv.writer(response)
    # Add headers to file
    writer.writerow(['student_id', 'project_number', 'project_name'])
    # Write students to file
    for student in unit.enrolled_students.all():
        writer.writerow(
            [student.student_id, student.assigned_project.number, student.assigned_project.name])

    # Email with result...??
    manager = models.User.objects.filter(pk=manager_id).first()
    if manager.email != None:
        send_mail(
            subject=f'{unit.name}: Project Allocation Results',
            message='The results of the allocation of students to projects for {unit.name} are attached.',
            from_email=None,
            recipient_list=[manager.email],
            fail_silently=False,
            attachments=[response]
        )
"""
