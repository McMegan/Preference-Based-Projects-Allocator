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


# List the managed/enrolled units on the index page
class IndexView(UserIsManagerMixin, ListView):
    template_name = "manager/index.html"
    model = models.Unit

    def get_queryset(self):
        if self.request.user.is_manager:
            return self.request.user.managed_units.all()
        elif self.request.user.is_student:
            return self.request.user.enrolled_units.all()
        return None


class UnitCreateView(UnitMixin, CreateView):
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


class UnitDetailView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, DetailView):
    model = models.Unit
    success_url = reverse_lazy('index')
    form_class = forms.UnitForm

    def get_initial(self):
        initial = super().get_initial()
        object_dict = self.get_object().__dict__
        for field in self.form_class.Meta.fields:
            if field in object_dict:
                initial[field] = object_dict[field]
        return initial

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset().filter(pk=self.kwargs['pk'])
        if self.request.user.is_manager:
            return queryset.prefetch_related(
                'projects').prefetch_related('students').annotate(students_count=Count('students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))
        elif self.request.user.is_student:
            return queryset.prefetch_related(
                'projects').annotate(projects_count=Count('projects', distinct=True))

    def test_func(self):
        if self.request.user.is_manager:
            return self.get_queryset().filter(
                manager_id=self.request.user.id).exists()
        elif self.request.user.is_student:
            return self.get_queryset().filter(
                students__id=self.request.user.id).exists()
        return self.request.user.is_manager or self.request.user.is_student


class UnitDeleteView(UnitMixin, DeleteView):
    success_url = reverse_lazy('index')


# Unit Enrolled Student Views
class UnitStudentsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.User
    template_name = 'manager/unit_students.html'
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
