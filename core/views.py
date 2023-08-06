from typing import Any, Dict, List, Optional
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy, resolve
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect
from django.db.models import Count

from . import models
from . import forms

# Mixin for unit views


class UnitMixin(LoginRequiredMixin, UserPassesTestMixin):
    model = models.Unit
    success_url = reverse_lazy('index')

    def get_queryset(self):
        if self.request.user.is_manager:
            return self.request.user.managed_units.all()
        elif self.request.user.is_student:
            return self.request.user.enrolled_units.all()
        return None

    def test_func(self):
        # print(self)
        # MANAGER ONLY FOR CREATE & DELETE
        return self.request.user.is_superuser or self.request.user.is_manager or self.request.user.is_student

# List the managed/enrolled units on the index page


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "core/index.html"
    model = models.Unit

    def get_queryset(self):
        if self.request.user.is_manager:
            return self.request.user.managed_units.all()
        elif self.request.user.is_student:
            return self.request.user.enrolled_units.all()
        return None

    def test_func(self):
        # print(self)
        # MANAGER ONLY FOR CREATE & DELETE
        return self.request.user.is_superuser or self.request.user.is_manager or self.request.user.is_student


class UnitDetailView(UnitMixin, DetailView):
    pass


class UnitCreateView(UnitMixin, CreateView):
    form_class = forms.UnitForm
    template_name = 'core/unit_new.html'

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        form = self.get_form()
        if form.is_valid():
            form.instance.manager_id = request.user.id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitUpdateView(UnitMixin, UpdateView):
    form_class = forms.UnitForm

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().prefetch_related(
            'projects').prefetch_related('students').annotate(students_count=Count('students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))


class UnitDeleteView(UnitMixin, DeleteView):
    success_url = reverse_lazy('index')


# Unit Enrolled Student Views
class UnitStudentsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.User
    template_name = 'core/unit_students.html'
    # form_class

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.request.user.managed_units.get(
            pk=self.kwargs['pk_unit'])
        return context

    def get_queryset(self):
        return super().get_queryset().filter(enrolled_units=self.kwargs['pk_unit'])

    def test_func(self):
        return self.request.user.is_manager
