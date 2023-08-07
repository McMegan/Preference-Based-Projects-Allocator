from django.db import models
from django.http import HttpRequest
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
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
        return self.request.user.managed_units.all()


class UnitCreateView(UserIsManagerMixin, CreateView):
    form_class = forms.UnitForm
    template_name = 'manager/unit_new.html'
    success_url = reverse_lazy('manager-index')

    def post(self, request: HttpRequest, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.manager_id = request.user.id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_queryset(self):
        return self.request.user.managed_units.all()

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
        return super().get_queryset().filter(pk=self.kwargs['pk']).prefetch_related(
            'projects').prefetch_related('enrolled_students').annotate(students_count=Count('enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))

    def test_func(self):
        return self.request.user.is_manager and self.get_queryset().filter(manager_id=self.request.user.id).exists()


class UnitDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_confirm_delete.html'

    def get_queryset(self):
        return self.request.user.managed_units.all()

    def test_func(self):
        return self.request.user.is_manager and self.get_queryset().filter(manager_id=self.request.user.id).exists()


# Unit Enrolled Student Views
class UnitStudentsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.EnrolledStudent
    template_name = 'manager/unit_students.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.request.user.managed_units.get(
            pk=self.kwargs['pk_unit'])
        return context

    def get_queryset(self):
        return super().get_queryset().prefetch_related('user').filter(unit=self.kwargs['pk_unit'])

    def test_func(self):
        return self.request.user.is_manager and self.request.user.managed_units.filter(pk=self.kwargs['pk_unit']).exists()


class UnitStudentsCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = forms.StudentForm
    template_name = 'manager/unit_students_new.html'

    def get_success_url(self):
        return self.request.path

    def post(self, request: HttpRequest, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit'] = self.request.user.managed_units.get(
            pk=self.kwargs['pk_unit'])
        return context

    def get_queryset(self):
        return super().get_queryset().prefetch_related('user').filter(unit=self.kwargs['pk_unit'])

    def test_func(self):
        return self.request.user.is_manager and self.request.user.managed_units.filter(pk=self.kwargs['pk_unit']).exists()


class UnitStudentsDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = models.EnrolledStudent
    template_name = 'manager/unit_students_detail.html'

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().prefetch_related('user').prefetch_related('user__project_preferences')

    def test_func(self):
        return self.request.user.is_manager and self.request.user.managed_units.filter(pk=self.kwargs['pk_unit']).exists()


class UnitStudentsDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_student_confirm_delete.html'

    def test_func(self):
        return self.request.user.is_manager and self.request.user.managed_units.filter(pk=self.kwargs['pk_unit']).exists()
