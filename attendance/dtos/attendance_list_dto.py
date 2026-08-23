class AttendanceListDTO:
    def __init__(self, id, date, status, remarks, enrollment):
        self.id = id
        self.date = date
        self.status = status
        self.remarks = remarks
        self.enrollment = enrollment

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "status": self.status,
            "remarks": self.remarks,
            "enrollment": self.enrollment,
        }
