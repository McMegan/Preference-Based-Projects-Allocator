from django.db import models
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormMixin

from core import models
from . import forms


def user_is_student(user):
    return user.is_student


def user_enrolled_in_unit(user, unit_id):
    return user.enrollments.filter(unit_id=unit_id).exists()


class UserIsStudentMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_student


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'core/index.html'
    model = models.Unit
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().filter(
            enrolled_students__user__id=self.request.user.id)

    def test_func(self):
        return user_is_student(self.request.user)


class UnitDetailView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    model = models.Unit
    template_name = "student/unit_detail.html"
    form_class = forms.PreferenceForm

    def post(self, request, *args, **kwargs):
        formset = forms.PreferenceFormset(self.request.POST)
        form = self.get_form()
        print(formset)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        # INITIAL FROM QUERYSET?
        formset = forms.PreferenceFormset(initial=[{'rank': 1}, {'rank': 2}])
        helper = forms.PreferenceFormSetHelper()
        return {**super().get_context_data(**kwargs), 'unit': self.get_object(kwargs), 'formset': formset, 'helper': helper}

    def get_object(self, *args, **kwargs):
        return models.Unit.objects.filter(pk=self.kwargs['pk']).prefetch_related(
            'projects').annotate(projects_count=Count('projects', distinct=True)).first()

    def test_func(self):
        return user_is_student(self.request.user) and self.get_object().enrolled_students.filter(user=self.request.user).exists()
