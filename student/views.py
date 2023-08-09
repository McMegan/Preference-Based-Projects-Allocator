from django.db import models
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView

from core import models

from . import forms


class UserIsStudentMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_student


class IndexView(UserIsStudentMixin, ListView):
    template_name = "student/index.html"
    model = models.Unit

    def get_queryset(self):
        return super().get_queryset().filter(
            enrolled_students__user__id=self.request.user.id)


# FormMixin
class UnitDetailView(UserIsStudentMixin, DetailView):
    model = models.Unit
    success_url = reverse_lazy('student-index')
    template_name = "student/unit_detail.html"

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().filter(pk=self.kwargs['pk']).prefetch_related(
            'projects').annotate(projects_count=Count('projects', distinct=True))

    def test_func(self):
        return super().get_queryset().filter(
            enrolled_students__user__id=self.request.user.id)
        return self.get_queryset().filter(
            students__id=self.request.user.id).exists()
