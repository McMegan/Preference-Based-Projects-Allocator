from typing import Any, Dict, List, Optional
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy, resolve
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormMixin
from django.shortcuts import render, redirect
from django.db.models import Count

from core import models
from . import forms


class UserIsManagerMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_manager


# List the managed/enrolled units on the index page
class IndexView(UserIsManagerMixin, ListView):
    model = models.Unit
    template_name = 'manager/index.html'

    def get_queryset(self):
        if self.request.user.is_manager:
            return self.request.user.managed_units.all()
        elif self.request.user.is_student:
            return self.request.user.enrolled_units.all()
        return None


class UnitCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = forms.UnitForm
    template_name = 'manager/unit_new.html'

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        form = self.get_form()
        if form.is_valid():
            form.instance.manager_id = request.user.id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def test_func(self):
        return self.request.user.is_manager


class UnitDetailView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Unit
    form_class = forms.UnitForm
    # success_url = reverse_lazy('index')
    template_name = 'manager/unit_form.html'

    def get_success_url(self):
        return self.request.path

    def get_initial(self):
        initial = super().get_initial()
        object_dict = self.get_object().__dict__
        for field in self.form_class.Meta.fields:
            if field in object_dict:
                initial[field] = object_dict[field]
        return initial

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset().filter(pk=self.kwargs['pk'])
        return queryset.prefetch_related(
            'projects').prefetch_related('students').annotate(students_count=Count('students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))

    def test_func(self):
        return self.request.user.is_manager and self.get_queryset().filter(manager_id=self.request.user.id).exists()


class UnitDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_confirm_delete.html'

    def test_func(self):
        return self.request.user.is_manager and self.get_queryset().filter(manager_id=self.request.user.id).exists()


# Unit Enrolled Student Views
class UnitStudentsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.User
    template_name = 'manager/unit_students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.request.user.managed_units.get(
            pk=self.kwargs['pk_unit'])
        return context

    def get_queryset(self):
        return super().get_queryset().filter(enrolled_units=self.kwargs['pk_unit'])

    def test_func(self):
        return self.request.user.is_manager
        # and self.get_queryset().filter(manager_id=self.request.user.id).exists()
