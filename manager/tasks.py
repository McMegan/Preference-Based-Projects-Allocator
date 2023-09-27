from celery import shared_task

from core.models import Unit

from . import allocator
from . import export
from . import upload


@shared_task(name=Unit.START_ALLOCATION_TASK_NAME)
def start_allocation_task(unit_id, manager_id, results_url):
    return allocator.start_allocation(unit_id, manager_id, results_url)


@shared_task(name=Unit.EMAIL_ALLOCATION_RESULTS_TASK_NAME)
def email_allocation_results_csv_task(*args, **kwargs):
    return export.email_allocation_results_csv(*args, **kwargs)


@shared_task(name=Unit.EMAIL_PREFERENCES_TASK_NAME)
def email_preferences_csv_task(*args, **kwargs):
    return export.email_preferences_csv(*args, **kwargs)


@shared_task(name=Unit.UPLOAD_PROJECTS_TASK_NAME)
def upload_projects_list_task(*args, **kwargs):
    return upload.upload_projects_list(*args, **kwargs)


@shared_task(name=Unit.UPLOAD_STUDENTS_TASK_NAME)
def upload_students_list_task(*args, **kwargs):
    return upload.upload_students_list(*args, **kwargs)


@shared_task(name=Unit.UPLOAD_PREFERENCES_TASK_NAME)
def upload_preferences_list_task(*args, **kwargs):
    return upload.upload_preferences_list(*args, **kwargs)
