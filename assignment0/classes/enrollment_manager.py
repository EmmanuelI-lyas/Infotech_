class EnrollmentManager:

    def enroll(self, student, course):

        if not student.can_enroll():
            print("Student already has 3 courses.")
            return False
        if student.already_enrolled(course):
            print("Already enrolled in this course.")
            return False

        if student.has_time_conflict(course):
            print("Timing conflict.")
            return False

        if not course.has_seat():
            print("Course is full.")
            return False

        student.add_course(course)
        course.enroll_student()

        print("Enrollment successful.")
        return True