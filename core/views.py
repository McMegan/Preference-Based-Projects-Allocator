from typing import Any, Dict
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


class IndexView(UnitMixin, ListView):
    template_name = "core/index.html"

    model = models.Unit
    # paginate_by = 100

    def get_context_data(self, **kwargs):
        print(self.request)
        return super().get_context_data(**kwargs)


class UnitDetailView(UnitMixin, DetailView):
    pass


class UnitCreateView(UnitMixin, CreateView):
    # fields = ['code', 'name', 'year', 'semester', 'preference_submission_start','preference_submission_end', 'minimum_preference_limit']
    success_url = reverse_lazy('index')
    form_class = forms.UnitForm
    template_name = 'core/unit_add.html'

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        form = self.get_form()
        if form.is_valid():
            form.instance.manager_id = request.user.id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitUpdateView(UnitMixin, UpdateView):
    fields = ['code', 'name', 'year', 'semester', 'preference_submission_start',
              'preference_submission_end', 'minimum_preference_limit']
    # success_url = reverse_lazy('index')
    form_class = forms.UnitForm

    def get_queryset(self):
        return super().get_queryset().annotate(students_count=Count('students'), projects_count=Count('projects'))

# def unit_update_view(request, pk):
#     band = Band.objects.get(id=id)
#     form = BandForm(instance=band) 
#     return render(request,'core/unit_form.html',{'form': form})


class UnitDeleteView(UnitMixin, DeleteView):
    success_url = reverse_lazy('index')
# listings/views.py
