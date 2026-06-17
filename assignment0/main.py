from classes.enrollment_manager import EnrollmentManager
from utils.csv_handler import (
    load_enrollments,
    load_students,
    load_courses,
    save_courses,
    save_enrollments
)

students = load_students("data/students.csv")
courses = load_courses("data/courses.csv")
load_enrollments(
    "data/enrollments.csv",
    students,
    courses
)

manager = EnrollmentManager()

while True:

    print("\n===== Course Registration System =====")
    print("1. Enroll Student")
    print("2. Exit")

    choice = input("Choice: ")

    if choice == "1":

        print("\nAvailable Students:")
        for student in students.values():
            print(f"{student.student_id} - {student.name}")

        print("\nAvailable Courses:")
        for course in courses.values():
            print(
                f"{course.code} - {course.name} "
                f"(Timing: {course.timing}) "
                f"- Remaining Seats: {course.empty_seats}"
            )

        student_id = input("\nEnter Student ID: ")
        course_code = input("Enter Course Code: ")

        if student_id not in students:
            print("Student not found.")
            continue

        if course_code not in courses:
            print("Course not found.")
            continue

        manager.enroll(
            students[student_id],
            courses[course_code]
        )

    elif choice == "2":

        save_courses(
            "data/courses.csv",
            courses
        )

        save_enrollments(
            "data/enrollments.csv",
            students
        )

        print("Data saved successfully.")
        print("Goodbye!")
        break

    else:
        print("Invalid choice. Please try again.")