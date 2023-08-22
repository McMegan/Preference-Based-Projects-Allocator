from celery import shared_task
from core import models
from .allocator import Allocator


@shared_task
def start_allocation(unit_id):
    allocator = Allocator()
    result = allocator.allocate(unit=models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'enrolled_students').prefetch_related('enrolled_students__project_preferences').first())
    # Email with result...??

    del allocator
    return result
