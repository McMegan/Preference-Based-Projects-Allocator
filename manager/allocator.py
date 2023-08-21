from ortools.linear_solver import pywraplp
from django.db.models.query import QuerySet

from core import models

# Include for each model:
# Projects -> id, min_students & max_students
# Enrolled student -> id
# Preferences -> project_id, student_id, rank


class Allocator:
    def __init__(self):
        self.solver = pywraplp.Solver.CreateSolver('SCIP')

    def allocate(self, unit: QuerySet):
        projects = unit.projects.all()
        students = unit.enrolled_students.all()

        # Make variables for projects & students
        project_vars, student_vars = self.make_vars(projects, students)

        # Set constraints for projects & students
        self.make_student_constraints(
            projects, students, student_vars)
        self.make_project_constraints(
            projects, students, project_vars, student_vars)

        # Set objective
        self.make_objective(
            projects, students, project_vars, student_vars)

        # Solve
        status = self.solver.Solve()
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            # Save allocation
            self.save_allocation(unit, projects, students,
                                 project_vars, student_vars)
            return True
        return False

    def make_vars(self, projects, students):
        project_vars = {}
        student_vars = {}
        for project in projects:
            project_vars[project.id] = self.solver.BoolVar(
                'Pr_{}'.format(project.id))
            for student in students:
                student_vars[student.id, project.id] = self.solver.BoolVar('St_{}_{}'.format(
                    student.id, project.id))
        return project_vars, student_vars

    def make_student_constraints(self, projects, students, student_vars):
        for student in students:
            allocation = []
            allocation_preference = []
            for project in projects:
                allocation.append(student_vars[student.id, project.id])
                student_project_preference = self.get_preference_rank(
                    projects, student, project)
                if student_project_preference != None:
                    allocation_preference.append(
                        student_vars[student.id, project.id] * student_project_preference)
            # Each student must be assigned to a project
            self.solver.Add(self.solver.Sum(allocation) == 1)
            # Student must have selected the project
            self.solver.Add(self.solver.Sum(allocation_preference) >= 1)

    def make_project_constraints(self, projects, students, project_vars, student_vars):
        for project in projects:
            # Make a list of the student variables for this project
            projects_student_vars = [student_vars[student.id, project.id]
                                     for student in students]

            # .... CHECK!!!!!
            # self.solver.Add(projects_student_vars >= 1 and self.solver.Sum(
            #     [projects_student_vars * 9999]) >= self.solver.Sum(projects_student_vars))
            self.solver.Add(project_vars[project.id] == 1 and self.solver.Sum(
                [project_vars[project.id] * 9999]) >= self.solver.Sum(projects_student_vars))

            # Each project must be allocated to a permissable number of students
            self.solver.Add(self.solver.Sum(projects_student_vars)
                            <= project.max_students)
            self.solver.Add(self.solver.Sum(projects_student_vars) >=
                            project.min_students * project_vars[project.id])

    def make_objective(self, projects, students, project_vars, student_vars):
        allocated_preferences = []
        for project in projects:
            for student in students:
                student_project_preference = self.get_preference_rank(
                    projects, student, project)
                if student_project_preference != None:
                    allocated_preferences.append(student_vars[student.id, project.id] *
                                                 student_project_preference)
        self.solver.Minimize(self.solver.Sum(allocated_preferences))

    def get_preference_rank(self, projects, student, project):
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
                return None
        else:
            return projects.count() + 1

    def save_allocation(self, unit, projects, students, project_vars, student_vars):
        student_allocated = []
        for project in projects:
            if project_vars[project.id]:
                for student in students:
                    if student_vars[student.id, project.id].solution_value() > 0.5:
                        student.assigned_project_id = project.id
                        student_allocated.append(student)
        models.EnrolledStudent.objects.bulk_update(
            student_allocated, fields=['assigned_project'])

