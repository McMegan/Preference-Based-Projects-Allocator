from django.utils.html import format_html
from django.urls import reverse

import django_tables2 as tables

from core import models


class ProjectTable(tables.Table):
    actions = tables.Column(empty_values=(), orderable=False, verbose_name='')

    class Meta:
        attrs = {'class': 'table table-striped'}

        model = models.Project
        template_name = "django_tables2/bootstrap5.html"
        fields = ('number', 'name', 'min_students', 'max_students')

        row_attrs = {'data-id': lambda record: record.pk}

    def render_number(self, value, record):
        return format_html(f"""<a class="link-offset-2 link-offset-3-hover link-underline link-underline-opacity-0 link-underline-opacity-75-hover" href="{reverse('manager:unit-project-detail', kwargs={'pk_unit': record.unit.id, 'pk': record.id})}">{record.number}</a>""")

    def render_name(self, value, record):
        return record.name
        if record.description:
            return format_html(f"""
                <div class="d-flex align-items-center justify-content-between">
                    <span>{record.name}</span>
                    <button type="button" class="btn btn-sm" data-bs-toggle="modal" data-bs-target="#record-{record.id}-modal"><i class="bi bi-plus-lg"></i></button>
                </div>
                <div class="modal fade" id="record-{record.id}-modal" tabindex="-1" aria-labelledby="record-{record.id}-modal-label" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
                        <div class="modal-content">
                        <div class="modal-header">
                            <h1 class="modal-title fs-5" id="record-{record.id}-modal-label">{record.name}</h1>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            {record.description}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                        </div>
                    </div>
                </div>
            """)
        return record.name

    def render_actions(self, value, record):
        return format_html(f"""<div class="d-flex gap-2 justify-content-end">
                                <a class="btn btn-primary btn-sm" href="{reverse('manager:unit-project-update', kwargs={'pk_unit': record.unit.id, 'pk': record.id})}">Edit</a>
                                <a class="btn btn-danger btn-sm" href="{reverse('manager:unit-project-remove', kwargs={'pk_unit': record.unit.id, 'pk': record.id})}">Remove</a>
                            </div>
                            """)
