from ortools.linear_solver import pywraplp
from core.models import Project, EnrolledStudent, ProjectPreference
from django.db.models.query import QuerySet


# Include for each model:
# Projects -> id, min_students & min_students
# Enrolled student -> id
# Preferences -> project_id, student_id, rank


class Allocator:
    def __init__(self):
        self.solver = pywraplp.Solver.CreateSolver('SCIP')

    def allocate(self, projects: QuerySet, students: QuerySet, preferences: QuerySet):
        project_vars, student_vars = self.make_vars(projects, students)

        self.make_student_constraints(
            projects, students, preferences, student_vars)
        self.make_project_constraints(
            projects, students, project_vars, student_vars)
        self.make_objective(
            projects, students, preferences, project_vars, student_vars)

        status = self.solver.Solve()
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            return project_vars, student_vars
        return False

    def make_vars(self, projects, students):
        project_vars = {project.id: self.solver.BoolVar(
            'Pr_{}'.format(project.id)) for project in projects}
        student_vars = {(student.id, project.id): self.solver.BoolVar('St_{}_{}'.format(
            student.id, project.id)) for project in projects for student in students}
        return student_vars, project_vars

    def make_student_constraints(self, projects, students, preferences, student_vars):
        for student in students:
            allocation = []
            allocation_preference = []
            student_preferences = preferences.filter(student_id=student.id)
            for project in projects:
                allocation.append(student_vars[student.id, project.id])
                # If the student submitted preferences, then find the rank for this project (if it was preferred) and add it to the allocation_preferences
                if student_preferences.exists():
                    preference = student_preferences.filter(
                        project_id=project.id)
                    if preference.exists():
                        allocation_preference.append(
                            student_vars[student.id, project.id] * preference.first().rank)
                # If the student didn't submit preferences, then set the preference rank for every project to a number greater than the project count
                else:
                    allocation_preference.append(
                        student_vars[student.id, project.id] * (projects.count() + 1))
            # Each student must be assigned to a project
            self.solver.Add(self.solver.Sum(allocation) == 1)
            # Student must have selected the project
            self.solver.Add(self.solver.Sum(allocation_preference) >= 1)

    def make_project_constraints(self, solver, projects, students, project_vars, student_vars):
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

    def make_objective(self, solver, projects, students, preferences, project_vars, student_vars):
        allocated_preferences = []
        for project in projects:
            for student in students:
                allocated_preferences.append(student_vars[student.id, project.id] *
                                             self.data.getStudent(student.id).preferences[project.id])
        self.solver.Minimize(self.solver.Sum(allocated_preferences))

    def get_preference_rank(self, preferences, projects, student, project):
        """
            Get the value for the preference for this student and this project
        """
        student_preferences = preferences.filter(student_id=student.id)
        if student_preferences.exists():
            preference = student_preferences.filter(project_id=project.id)
            if preference.exists():
                return preference.first().rank
            else:
                return None
        else:
            return projects.count() + 1
