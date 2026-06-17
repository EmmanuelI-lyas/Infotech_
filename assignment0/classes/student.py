class Student:

    MAX_COURSES = 3

    def __init__(self, student_id, name):
        self.student_id = student_id
        self.name = name
        self.courses = []

    def can_enroll(self):
        return len(self.courses) < Student.MAX_COURSES

    def has_time_conflict(self, course):
        for enrolled_course in self.courses:
            if enrolled_course.timing == course.timing:
                return True
        return False

    def add_course(self, course):
        self.courses.append(course)
    def already_enrolled(self, course):

     for enrolled_course in self.courses:

        if enrolled_course.code == course.code:
            return True

     return False
        