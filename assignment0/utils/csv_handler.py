








import csv
from classes.student import Student
from classes.course import Course
def load_students(path):

    students = {}

    with open(path, newline="") as file:

        reader = csv.DictReader(file)

        for row in reader:

            student = Student(
                row["student_id"],
                row["name"]
            )

            students[student.student_id] = student

    return students


def load_courses(path):

    courses = {}

    with open(path, newline="") as file:

        reader = csv.DictReader(file)

        for row in reader:

            course = Course(
                row["course_code"],
                row["course_name"],
                row["timing"],
                row["total_seats"],
                row["filled_seats"],
                row["empty_seats"]
            )

            courses[course.code] = course

    return courses


def save_courses(path, courses):

    with open(path, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "course_code",
            "course_name",
            "timing",
            "total_seats",
            "filled_seats",
            "empty_seats"
        ])

        for course in courses.values():

            writer.writerow([
                course.code,
                course.name,
                course.timing,
                course.total_seats,
                course.filled_seats,
                course.empty_seats
            ])


def save_enrollments(path, students):

    with open(path, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "student_id",
            "student_name",
            "course_code",
            "course_name"
        ])

        for student in students.values():

            for course in student.courses:

                writer.writerow([
                    student.student_id,
                    student.name,
                    course.code,
                    course.name
                ])
def load_enrollments(path, students, courses):

    try:

        with open(path, newline="") as file:

            reader = csv.DictReader(file)

            for row in reader:

                student_id = row["student_id"]
                course_code = row["course_code"]

                if student_id not in students:
                    continue

                if course_code not in courses:
                    continue

                student = students[student_id]
                course = courses[course_code]

                student.courses.append(course)

    except FileNotFoundError:
        pass