from celery import shared_task
from .allocator import Allocator
from core import models


@shared_task
def start_allocation(unit_id):
    result = Allocator().allocate(unit=models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'enrolled_students').prefetch_related('enrolled_students__project_preferences').first())
    # Email with result...??
