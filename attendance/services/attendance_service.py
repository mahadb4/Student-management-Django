from datetime import date
from common.messages import Messages


class AttendanceService:
    def __init__(self, validator, repository):
        self.validator = validator
        self.repository = repository

    def get(self, attendance_id):
        return self.repository.get(attendance_id)

    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        enrollment = data["enrollment"]
        attendance_date = data["date"]

        if self.repository.attendance_exists(enrollment, attendance_date):
            raise ValueError(Messages.ATTENDANCE_ALREADY_EXISTS.format(enrollment.id if hasattr(enrollment, "id") else enrollment, attendance_date))

        return self.repository.create(data)

    def update(self, attendance_id, data, partial = False):
        attendance = self.repository.get(attendance_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(attendance, data)

        self.validator.validate(data)

        enrollment = data["enrollment"]
        attendance_date = data["date"]

        if self.repository.attendance_exists(enrollment, attendance_date, attendance_id):
            raise ValueError(Messages.ATTENDANCE_ALREADY_EXISTS.format(enrollment.id if hasattr(enrollment, "id") else enrollment, attendance_date))

        return self.repository.update(attendance, data)

    def delete(self, attendance_id):
        self.repository.delete(attendance_id)

    def mark_bulk(self, attendance_data):
        records = []

        for data in attendance_data:
            self.validator.validate(data)

            enrollment = data["enrollment"]
            attendance_date = data["date"]

            if self.repository.attendance_exists(enrollment, attendance_date):
                raise ValueError(Messages.ATTENDANCE_ALREADY_EXISTS.format(enrollment.id if hasattr(enrollment, "id") else enrollment, attendance_date))

            records.append(self.repository.create(data))

        return records

    def _merge_data(self, attendance, data):
        return {
            "enrollment": data.get("enrollment", attendance.enrollment_id),
            "date": data.get("date", attendance.date),
            "status": data.get("status", attendance.status),
            "remarks": data.get("remarks", attendance.remarks or ""),
        }
