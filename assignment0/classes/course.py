class Course:

    def __init__(
        self,
        code,
        name,
        timing,
        total_seats,
        filled_seats,
        empty_seats
    ):
        self.code = code
        self.name = name
        self.timing = timing

        self.total_seats = int(total_seats)
        self.filled_seats = int(filled_seats)
        self.empty_seats = int(empty_seats)
        if int(total_seats) <= 0:
         raise ValueError(
         f"Invalid total seats for {code}"
         )
        if (
           int(filled_seats)
           + int(empty_seats)
           != int(total_seats)
           ):
         raise ValueError(
         f"Seat counts invalid for {code}"
         )

    def has_seat(self):
        return self.empty_seats > 0

    def enroll_student(self):
        self.filled_seats += 1
        self.empty_seats -= 1
        