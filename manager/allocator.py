from django.core.mail import EmailMultiAlternatives

from ortools.linear_solver import pywraplp

from core import models


def start_allocation(unit_id, manager_id, results_url):
    unit = models.Unit.objects.filter(pk=unit_id).prefetch_related('projects').prefetch_related(
        'students').prefetch_related('students__project_preferences').first()

    Allocator(unit=unit)

    # Email with result...??
    manager = models.User.objects.filter(pk=manager_id).first()
    if manager.email != None:
        email_message = f'The allocation of students to projects for {unit.name} was successful.'
        email_message_html = f'The allocation of students to projects for {unit.name} was successful. <a href="{results_url}">View the results of the allocation</a>.'
        if not unit.allocation_status:
            email_message = f'The allocation of students to projects for {unit.name} failed.'
            email_message_html = f'The allocation of students to projects for {unit.name} failed.'
        email = EmailMultiAlternatives(
            subject=f'{unit.name}: Project Allocation Finished',
            body=email_message,
            to=[manager.email],
        )
        email.attach_alternative(email_message_html, 'text/html')
        result = email.send(fail_silently=False)
        return 'Email successful' if result else 'Email failed', unit.get_allocation_descriptive()

    return 'No email specified', unit.get_allocation_descriptive()


class Allocator:
    def __init__(self, unit: models.Unit):
        previous_allocation_status = unit.allocation_status

        self.solver = pywraplp.Solver.CreateSolver('SCIP')

        self.unit = unit
        self.projects = unit.projects.all()
        self.students = unit.students.all()

        # Make variables for projects & students
        self.make_vars()

        # Set constraints for projects & students
        self.make_student_constraints()
        self.make_project_constraints()

        # Set objective
        self.make_objective()

        # Solve
        status = self.solver.Solve()

        result = {
            pywraplp.Solver.OPTIMAL: models.Unit.OPTIMAL,
            pywraplp.Solver.FEASIBLE: models.Unit.FEASIBLE,
            pywraplp.Solver.INFEASIBLE: models.Unit.INFEASIBLE,
            pywraplp.Solver.UNBOUNDED: models.Unit.UNBOUNDED,
            pywraplp.Solver.ABNORMAL: models.Unit.ABNORMAL,
            pywraplp.Solver.MODEL_INVALID: models.Unit.MODEL_INVALID,
            pywraplp.Solver.NOT_SOLVED: models.Unit.NOT_SOLVED,
        }[status]

        allocation_successful = result == models.Unit.OPTIMAL or result == models.Unit.FEASIBLE
        previous_allocation_successful = previous_allocation_status == models.Unit.OPTIMAL or previous_allocation_status == models.Unit.FEASIBLE
        if allocation_successful:
            self.save_allocation()
        unit.allocation_status = result if allocation_successful or not previous_allocation_successful else previous_allocation_status
        unit.save()

    def make_vars(self):
        self.project_vars = {}
        self.student_vars = {}
        for project in self.projects:
            self.project_vars[project.id] = self.solver.IntVar(
                0, 1, 'Pr_{}'.format(project.id))
            for student in self.students:
                self.student_vars[student.id, project.id] = self.solver.IntVar(
                    0, 1, 'St_{}_{}'.format(student.id, project.id))

    def make_student_constraints(self):
        for student in self.students:
            allocation = []
            allocation_preference = []
            for project in self.projects:
                allocation.append(
                    self.student_vars[student.id, project.id])
                allocation_preference.append(
                    self.student_vars[student.id, project.id] * self.get_preference_rank(student, project))
            # Each student must be assigned to a project
            self.solver.Add(self.solver.Sum(allocation) == 1)
            # Student must have selected the project
            self.solver.Add(self.solver.Sum(allocation_preference) >= 1)

    def make_project_constraints(self):
        for project in self.projects:
            # Make a list of the student variables for this project
            projects_student_vars = [self.student_vars[student.id, project.id]
                                     for student in self.students]
            self.solver.Add(self.project_vars[project.id] == 1 and self.solver.Sum(
                [self.project_vars[project.id] * 99999]) >= self.solver.Sum(projects_student_vars))
            # Each project must be allocated to a permissable number of students
            self.solver.Add(self.solver.Sum(projects_student_vars)
                            <= project.max_students)
            self.solver.Add(self.solver.Sum(projects_student_vars) >=
                            (project.min_students * self.project_vars[project.id]))

    def make_objective(self):
        allocated_preferences = []
        for project in self.projects:
            for student in self.students:
                allocated_preferences.append(
                    self.student_vars[student.id, project.id] * self.get_preference_rank(student, project))
        self.solver.Minimize(self.solver.Sum(allocated_preferences))

    def get_preference_rank(self, student, project):
        """
            Get the value for the preference for this student and this project
        """
        student_preferences = student.project_preferences.filter(
            student_id=student.id)
        if student_preferences.exists():
            preference = student_preferences.filter(project_id=project.id)
            if preference.exists():
                return preference.first().rank
            else:
                return self.projects.count() * 10
        else:
            return self.projects.count() + 1

    def get_bool_var_value(self, variable):
        return 1 if variable > 0.5 else 0

    def save_allocation(self):
        student_allocated = []
        for project in self.projects:
            if self.project_vars[project.id]:
                project_allocated_ranks = []
                for student in self.students:
                    if self.student_vars[student.id, project.id].solution_value() > 0.5:
                        rank = student.project_preferences.filter(
                            project=project)
                        if student.project_preferences.filter(project=project).exists():
                            rank = student.project_preferences.filter(
                                project=project).first().rank
                            project_allocated_ranks.append(rank)
                        else:
                            rank = None

                        student.allocated_project_id = project.id
                        student.allocated_preference_rank = rank
                        student_allocated.append(student)

        models.Student.objects.bulk_update(
            student_allocated, fields=['allocated_project', 'allocated_preference_rank'])
