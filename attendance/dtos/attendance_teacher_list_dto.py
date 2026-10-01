class AttendanceTeacherListDTO:
    def __init__(self, id, date, status, enrollment_id):
        self.id = id
        self.date = date
        self.status = status
        self.enrollment_id = enrollment_id

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "status": self.status,
            "enrollment_id": self.enrollment_id,
        }
