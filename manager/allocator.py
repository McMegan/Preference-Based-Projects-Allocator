from ortools.linear_solver import pywraplp

from core import models


class Allocator:
    def allocate(self, unit):
        self.solver = pywraplp.Solver.CreateSolver('SCIP')

        self.unit = unit
        self.projects = unit.projects.all()
        self.students = unit.enrolled_students.all()

        # Make variables for projects & students
        self.make_vars()

        # Set constraints for projects & students
        self.make_student_constraints()
        self.make_project_constraints()

        # Set objective
        self.make_objective()

        # Solve
        status = self.solver.Solve()
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            # Save allocation
            self.save_allocation()
            return True
        return False

    def make_vars(self):
        self.project_vars = {}
        self.student_vars = {}
        for project in self.projects:
            self.project_vars[project.id] = self.solver.BoolVar(
                'Pr_{}'.format(project.id))
            for student in self.students:
                self.student_vars[student.id, project.id] = self.solver.BoolVar('St_{}_{}'.format(
                    student.id, project.id))

    def make_student_constraints(self):
        for student in self.students:
            allocation = []
            allocation_preference = []
            for project in self.projects:
                allocation.append(self.student_vars[student.id, project.id])
                student_project_preference = self.get_preference_rank(
                    student, project)
                if student_project_preference != None:
                    allocation_preference.append(
                        self.student_vars[student.id, project.id] * student_project_preference)
            # Each student must be assigned to a project
            self.solver.Add(self.solver.Sum(allocation) == 1)
            # Student must have selected the project
            self.solver.Add(self.solver.Sum(allocation_preference) >= 1)

    def make_project_constraints(self):
        for project in self.projects:
            # Make a list of the student variables for this project
            projects_student_vars = [self.student_vars[student.id, project.id]
                                     for student in self.students]

            # .... CHECK!!!!!
            # self.solver.Add(projects_student_vars >= 1 and self.solver.Sum(
            #     [projects_student_vars * 9999]) >= self.solver.Sum(projects_student_vars))
            self.solver.Add(self.project_vars[project.id] == 1 and self.solver.Sum(
                [self.project_vars[project.id] * 9999]) >= self.solver.Sum(projects_student_vars))

            # Each project must be allocated to a permissable number of students
            self.solver.Add(self.solver.Sum(projects_student_vars)
                            <= project.max_students)
            self.solver.Add(self.solver.Sum(projects_student_vars) >=
                            project.min_students * self.project_vars[project.id])

    def make_objective(self):
        allocated_preferences = []
        for project in self.projects:
            for student in self.students:
                student_project_preference = self.get_preference_rank(
                    student, project)
                if student_project_preference != None:
                    allocated_preferences.append(self.student_vars[student.id, project.id] *
                                                 student_project_preference)
        self.solver.Minimize(self.solver.Sum(allocated_preferences))

    def save_allocation(self):
        project_updated = []
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

                        student.assigned_project_id = project.id
                        student.assigned_preference_rank = rank
                        student_allocated.append(student)
                if len(project_allocated_ranks) != 0:
                    project.avg_allocated_pref = sum(
                        project_allocated_ranks) / len(project_allocated_ranks)
                    project_updated.append(project)

        models.EnrolledStudent.objects.bulk_update(
            student_allocated, fields=['assigned_project', 'assigned_preference_rank'])
        models.Project.objects.bulk_update(
            project_updated, fields=['avg_allocated_pref'])

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
                return None
        else:
            return self.projects.count() + 1
