from django.urls import reverse_lazy, resolve
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from . import models

# Mixin for unit views


class UnitMixin(LoginRequiredMixin, UserPassesTestMixin):
    model = models.Unit

    def get_queryset(self):
        return models.Unit.objects.select_related('manager').filter(manager_id=self.request.user.id)

    def test_func(self):
        return self.request.user.is_manager

# List the managed/enrolled units on the index page


class IndexView(LoginRequiredMixin, ListView):
    template_name = "core/index.html"

    model = models.Unit
    paginate_by = 100

    def get_context_data(self, **kwargs):
        print(self.request)
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        return models.Unit.objects.filter(manager_id=self.request.user.id)

    def test_func(self):
        return self.request.user.is_manager


class UnitListView(UnitMixin, ListView):
    model = models.Unit
    paginate_by = 100


class UnitDetailView(UnitMixin, DetailView):
    pass


class UnitCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = models.Unit
    fields = ['code', 'name', 'year', 'semester', 'preference_submission_start',
              'preference_submission_end', 'minimum_preference_limit']

    def test_func(self):
        return self.get_object().manager.id == self.request.user.id


class UnitUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Unit
    fields = ['code', 'name', 'year', 'semester', 'preference_submission_start',
              'preference_submission_end', 'minimum_preference_limit']

    def test_func(self):
        return self.get_object().manager.id == self.request.user.id


class UnitDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = models.Unit
    success_url = reverse_lazy('unit-list')

    def test_func(self):
        return self.get_object().manager.id == self.request.user.id
