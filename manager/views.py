import csv
from io import StringIO

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count, Sum,  F, Avg
from django.db.models.functions import Round
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormMixin


from core import models
from . import forms


def user_is_manager(user):
    return user.is_manager


class UnitMixin:
    unit_id_arg = 'pk_unit'

    def get_unit_queryset(self):
        unit_pk = self.kwargs[self.unit_id_arg]
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = models.Unit.objects.filter(pk=unit_pk).annotate(students_count=Count(
                'enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))
        return models.Unit.objects.filter(pk=unit_pk).annotate(students_count=Count(
            'enrolled_students', distinct=True)).annotate(projects_count=Count('projects', distinct=True))

    def get_unit_object(self):
        if not hasattr(self, 'unit'):
            self.unit = self.get_unit_queryset().first()
        return self.unit

    def get_context_for_sidebar(self):
        unit = self.get_unit_object()
        nav_items = [
            {'url': 'manager:unit', 'label': unit, 'classes': 'fs-6'},
            # Allocator Settings / Setup
            {'label': 'Unit Actions', 'classes': 'fw-semibold'},
            {'url': 'manager:unit-students-new-list',
                'label': 'Upload Student List', 'classes': 'ms-3'},
            {'url': 'manager:unit-students-new',
                'label': 'Add Student', 'classes': 'ms-3'},
            {'url': 'manager:unit-projects-new-list',
                'label': 'Upload Project List', 'classes': 'ms-3'},
            {'url': 'manager:unit-projects-new',
                'label': 'Add Project', 'classes': 'ms-3'},
            {'url': 'manager:unit-allocation-start',
                'label': 'Start Allocation', 'classes': 'ms-3'},
            # Unit Information
            {'label': 'Unit Information', 'classes': 'fw-semibold'},
            {'url': 'manager:unit-students',
                'label': f'Student List ({unit.students_count})', 'classes': 'ms-3'},
            {'url': 'manager:unit-projects',
                'label': f'Project List ({unit.projects_count})', 'classes': 'ms-3'},
            {'url': 'manager:unit-preferences',
                'label': 'Preference Distribution', 'classes': 'ms-3'},

        ]
        if unit.is_allocated():
            nav_items.append({'url': 'manager:unit-allocation-results',
                              'url': 'manager:unit-allocation-results', 'label': 'Allocation Results', 'classes': 'ms-3'})
        return {'unit': unit, 'nav_items': nav_items}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **self.get_context_for_sidebar()}

    def unit_managed_by_user(self):
        unit = self.get_unit_object()
        return unit.manager.id == self.request.user.id

    def test_func(self):
        return user_is_manager(self.request.user) and self.unit_managed_by_user()


class IndexView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = models.Unit
    template_name = 'core/index.html'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.managed_units.all().order_by('-is_active')

    def test_func(self):
        return user_is_manager(self.request.user)

# Unit Views


class UnitCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = forms.CreateUnitForm
    template_name = 'manager/unit_new.html'
    success_url = reverse_lazy('manager:index')

    def post(self, request, *args, **kwargs):
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
        return user_is_manager(self.request.user)


class UnitDeleteView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = models.Unit
    success_url = reverse_lazy('index')
    template_name = 'manager/unit_confirm_delete.html'

    unit_id_arg = 'pk'


class UnitView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Unit
    form_class = forms.UpdateUnitForm
    template_name = 'manager/unit.html'

    unit_id_arg = 'pk'

    def get_success_url(self):
        return self.request.path


# Unit student views


class UnitStudentsListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
        List of students in unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_students.html'
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).prefetch_related('user').prefetch_related('project_preferences')


class UnitStudentsCreateView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Add a single student to the unit's student list
    """
    form_class = forms.StudentForm
    template_name = 'manager/students/unit_students_new.html'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'pk_unit': self.kwargs['pk_unit']}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            # Check if user account exists for student
            user = models.User.objects.filter(
                username=form.cleaned_data.get('student_id'))
            if user.exists():
                form.instance.user_id = user.first().id
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitStudentUploadListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Upload list of students to a unit
    """
    form_class = forms.StudentListForm
    template_name = 'manager/students/unit_students_new_list.html'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request, *args, **kwargs):
        # form = self.get_form()
        form = forms.StudentListForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('list_override'):
                # Clear previous enrolled students
                models.EnrolledStudent.objects.filter(
                    unit_id=self.kwargs['pk_unit']).delete()

            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            csv_data = csv.DictReader(
                StringIO(file.read().decode('utf-8-sig')), delimiter=',')
            student_id_column = form.cleaned_data.get('student_id_column')

            enrolled_students = []
            for row in csv_data:
                enrolled_student = models.EnrolledStudent()
                enrolled_student.student_id = row[student_id_column]
                enrolled_student.unit_id = self.kwargs['pk_unit']
                # Check if user account exists for student
                user = models.User.objects.filter(
                    username=row[student_id_column])
                if user.exists():
                    enrolled_student.user_id = user.first().id
                enrolled_students.append(enrolled_student)

            models.EnrolledStudent.objects.bulk_create(
                enrolled_students,
                update_conflicts=True,
                update_fields=['student_id', 'unit_id'],
            )

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitStudentsDetailView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
        View a single student in a unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_student_detail.html'

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset().prefetch_related('user').prefetch_related('project_preferences').prefetch_related('project_preferences__project')


class UnitStudentDeleteView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
        Remove a single student from a unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_student_confirm_delete.html'

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})


class UnitStudentsClearView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Clear the student list of a unit
    """
    model = models.EnrolledStudent
    template_name = 'manager/students/unit_students_confirm_delete.html'
    form_class = forms.StudentListClearForm

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            models.EnrolledStudent.objects.filter(
                unit_id=self.kwargs['pk_unit']).delete()

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('manager:unit-students', kwargs={'pk_unit': self.kwargs['pk_unit']})

# Unit project views


class UnitProjectsListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
        List of projects in unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_projects.html'
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().prefetch_related('unit').filter(unit=self.kwargs['pk_unit'])


class UnitProjectsCreateView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    form_class = forms.ProjectForm
    template_name = 'manager/projects/unit_projects_new.html'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'pk_unit': self.kwargs['pk_unit']}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.unit_id = self.kwargs['pk_unit']
            form.instance.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitProjectUploadListView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Upload list of projects
    """
    form_class = forms.ProjectListForm
    template_name = 'manager/projects/unit_projects_new_list.html'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})

    def post(self, request, *args, **kwargs):
        # form = self.get_form()
        form = forms.ProjectListForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('list_override'):
                # Clear previous enrolled projects
                models.Project.objects.filter(
                    unit_id=self.kwargs['pk_unit']).delete()

            # Reset file position after checking headers in form.clean()
            file = request.FILES['file']
            file.seek(0)

            csv_data = csv.DictReader(
                StringIO(file.read().decode('utf-8-sig')), delimiter=',')
            number_column = form.cleaned_data.get('number_column')
            name_column = form.cleaned_data.get('name_column')
            min_students_column = form.cleaned_data.get('min_students_column')
            max_students_column = form.cleaned_data.get('max_students_column')
            description_column = form.cleaned_data.get('description_column')

            project_list = []
            for row in csv_data:
                project = models.Project()
                project.number = row[number_column]
                project.name = row[name_column]
                project.min_students = row[min_students_column]
                project.max_students = row[max_students_column]
                if description_column != '':
                    project.description = row[description_column]
                project.unit_id = self.kwargs['pk_unit']
                project_list.append(project)

            models.Project.objects.bulk_create(
                project_list,
                update_conflicts=True,
                update_fields=['number', 'name'],
            )

            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class UnitProjectsDetailView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
        View a project in a unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_project_detail.html'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


class UnitProjectsUpdateView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
        Update a project in a unit
    """
    form_class = forms.ProjectUpdateForm
    model = models.Project
    template_name = 'manager/projects/unit_project_update.html'

    def get_success_url(self):
        return reverse('manager:unit-project-detail', kwargs={'pk': self.kwargs['pk'], 'pk_unit': self.kwargs['pk_unit']})


class UnitProjectDeleteView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
        Remove a single project from a unit
    """
    model = models.Project
    template_name = 'manager/projects/unit_project_confirm_delete.html'

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


class UnitProjectsClearView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        Clear the project list of a unit
    """
    template_name = 'manager/projects/unit_projects_confirm_delete.html'
    form_class = forms.StudentListClearForm

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            models.Project.objects.filter(
                unit_id=self.kwargs['pk_unit']).delete()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('manager:unit-projects', kwargs={'pk_unit': self.kwargs['pk_unit']})


# Unit Preference Views

class UnitPreferencesView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
        Show the distribution of preferences for projects in unit
    """
    model = models.Project
    template_name = 'manager/preferences/unit_preferences.html'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'submitted_prefs_students_count': models.EnrolledStudent.objects.filter(
            unit=self.kwargs['pk_unit']).annotate(project_preference_count=Count('project_preferences')).filter(project_preference_count__gt=0).count()}

    def get_queryset(self):
        total_projects = models.Project.objects.filter(
            unit_id=self.kwargs['pk_unit']).count()
        return super().get_queryset().filter(unit_id=self.kwargs['pk_unit']).prefetch_related('student_preferences').annotate(popularity=Sum(total_projects - F('student_preferences__rank')))


# Unit Allocation Views


class UnitAllocationStartView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, TemplateView):
    """
        View for starting/viewing allocation
    """
    form_class = forms.StartAllocationForm
    template_name = 'manager/allocation/unit_allocation_start.html'

    def get_unit_queryset(self):
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = super().get_unit_queryset().prefetch_related('projects').annotate(
                avg_allocated_pref_rounded=Round(Avg('projects__avg_allocated_pref'), 2))
        return self.unit_queryset

    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'unit': self.get_unit_object()}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            from .tasks import start_allocation
            start_allocation.delay(unit_id=self.kwargs['pk_unit'])
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'submitted_prefs_students_count': models.EnrolledStudent.objects.filter(
            unit=self.kwargs['pk_unit']).annotate(project_preference_count=Count('project_preferences')).filter(project_preference_count__gt=0).count()}


class UnitAllocationResultsView(UnitMixin, LoginRequiredMixin, UserPassesTestMixin, FormMixin, ListView):
    """
        View allocation results & stats
    """
    model = models.Project
    template_name = 'manager/allocation/unit_allocation_results.html'
    paginate_by = 25

    form_class = forms.ExportAllocationForm

    def get_success_url(self):
        return self.request.path

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        return self.make_allocation_results_csv()

    def get_unit_queryset(self):
        if not hasattr(self, 'unit_queryset'):
            self.unit_queryset = super().get_unit_queryset().prefetch_related('projects').annotate(
                avg_allocated_pref_rounded=Round(Avg('projects__avg_allocated_pref'), 2))
        return self.unit_queryset

    def get_queryset(self):
        return super().get_queryset().filter(unit=self.kwargs['pk_unit']).prefetch_related('assigned_students').annotate(avg_allocated_pref_rounded=Round(F('avg_allocated_pref'), 2))

    def test_func(self):
        return super().test_func() and self.get_unit_object().is_allocated()

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'submitted_prefs_students_count': models.EnrolledStudent.objects.filter(
            unit=self.kwargs['pk_unit']).annotate(project_preference_count=Count('project_preferences')).filter(project_preference_count__gt=0).count()}

    def make_allocation_results_csv(self):
        unit = self.get_unit_object()

        response = HttpResponse(
            content_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{unit.code}-project-allocation.csv"'},
        )

        # Write to file
        writer = csv.writer(response)
        # Add headers to file
        writer.writerow(['student_id', 'project_number', 'project_name'])
        # Write students to file
        for student in unit.enrolled_students.all():
            writer.writerow(
                [student.student_id, student.assigned_project.number, student.assigned_project.name])

        return response
