from django.db import models
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import formset_factory
from django.db.models import Q, Count
from django.views.generic import ListView
from django.views.generic.edit import FormMixin

from core import models
from . import forms


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'core/index.html'
    model = models.Unit
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().filter(students__user__id=self.request.user.id).filter(is_active=True)

    def test_func(self):
        return self.request.user.is_student


class UnitDetailView(LoginRequiredMixin, UserPassesTestMixin, FormMixin, ListView):
    model = models.Project
    template_name = "student/unit_detail.html"

    def get_unit_object(self):
        if not hasattr(self, 'unit'):
            self.unit = models.Unit.objects.filter(
                pk=self.kwargs['pk']).prefetch_related('areas').first()
        return self.unit

    def get_student_object(self):
        if not hasattr(self, 'student_object'):
            self.student_object = self.request.user.enrollments.filter(
                unit_id=self.kwargs['pk']).prefetch_related('area').first()
        return self.student_object

    def get_students_preferences(self):
        if not hasattr(self, 'preferences'):
            self.preferences = self.get_student_object(
            ).project_preferences.all().select_related('project').prefetch_related('project__area')
        return self.preferences

    def get_form_class(self):
        min_preference_limit = self.get_unit_object().minimum_preference_limit
        return formset_factory(formset=forms.PreferenceFormSet, form=forms.PreferenceForm, extra=0, min_num=min_preference_limit if min_preference_limit else 0, validate_min=True if min_preference_limit else False)

    def get_initial(self):
        return [{'rank': preference.rank, 'project': preference.project, 'project_id': preference.project.id}
                for preference in self.get_students_preferences()]

    def get_success_url(self):
        return self.request.path

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        formset = self.get_form()
        if formset.is_valid():
            students_preferences = self.get_students_preferences()
            # Delete any preferences that are outside the number of submitted preferences
            for preference in students_preferences.all()[formset.total_form_count():]:
                preference.delete()

            for index, form in enumerate(formset):
                # Set the project for this form instance
                form.instance.project = models.Project.objects.get(
                    id=form.cleaned_data.get('project_id'))

                # Don't re-save existing records
                preference_exists = students_preferences.filter(
                    rank=form.instance.rank, project=form.instance.project)

                if not preference_exists.exists():
                    preference_at_current_rank = students_preferences.filter(
                        rank=form.instance.rank)
                    preference_with_current_project = students_preferences.filter(
                        project=form.instance.project)

                    if preference_at_current_rank.exists() and preference_with_current_project.exists():
                        preference_at_current_rank = preference_at_current_rank.first()
                        preference_with_current_project = preference_with_current_project.first()
                        if preference_at_current_rank.project != form.instance.project and preference_with_current_project.rank != form.instance.rank:
                            # Swap these records
                            preference_at_current_rank.rank = 0
                            preference_at_current_rank.save()

                            temp = preference_with_current_project.rank
                            preference_with_current_project.rank = form.instance.rank
                            preference_with_current_project.save()

                            preference_at_current_rank.rank = temp
                            preference_at_current_rank.save()
                    elif preference_at_current_rank.exists():
                        preference_at_current_rank = preference_at_current_rank.first()
                        # Replace preference at current rank with this project
                        preference_at_current_rank.project = form.instance.project
                        preference_at_current_rank.save()
                    elif preference_with_current_project.exists():
                        preference_with_current_project = preference_with_current_project.first()
                        # Replace preference with current project with new rank
                        preference_with_current_project.rank = form.instance.rank
                        preference_at_current_rank.save()
                    else:
                        # Create new record
                        form.instance.student = self.get_student_object()
                        form.instance.save()

            return self.form_valid(formset)
        else:
            return self.form_invalid(formset)

    def get_context_data(self, **kwargs):
        unit = self.get_unit_object()
        preference_querset = self.get_students_preferences()
        helper = forms.PreferenceFormSetHelper()

        formset = kwargs.get('form')
        preference_from_form = []
        if formset:
            # Reload with form values
            for form in formset:
                form.instance.project = models.Project.objects.get(
                    id=form.cleaned_data.get('project_id'))
                form.instance.student = self.get_student_object()
                preference_from_form.append(form.instance)

        preferences = preference_from_form if len(
            preference_from_form) else preference_querset
        preferred_projects = [
            preference.project for preference in preferences]

        return {**super().get_context_data(**kwargs), 'unit': unit, 'preferences': preferences, 'preferred_projects': preferred_projects, 'helper': helper}

    def get_queryset(self):
        qs = super().get_queryset().filter(
            unit_id=self.kwargs['pk']).prefetch_related('area')
        if self.get_unit_object().limit_by_major:
            qs = qs.annotate(area_count=Count('area')).filter(Q(area__in=self.get_student_object(
            ).area.all()) | Q(area_count=0)).distinct()
        return qs.order_by('number')

    def test_func(self):
        return self.request.user.is_student and self.get_student_object()
