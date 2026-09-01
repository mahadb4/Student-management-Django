class AttendanceTeacherListDTO:
    def __init__(self, id, date, status, remarks, enrollment_id, student_name):
        self.id = id
        self.date = date
        self.status = status
        self.remarks = remarks
        self.enrollment_id = enrollment_id
        self.student_name = student_name

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "status": self.status,
            "remarks": self.remarks,
            "enrollment_id": self.enrollment_id,
            "student_name": self.student_name,
        }
