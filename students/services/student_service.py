from students.models import Student

class StudentService:

    @staticmethod
    def create_student(data):
        Student.objects.create(
            first_name=data["first_name"],
            last_name=data["last_name"],
            student_email=data["student_email"],
            parents_phone_number=data["parents_phone_number"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
            address=data["address"],
            student_group=data["student_group"],
            is_active=True if data.get("is_active") else False,
        )

    @staticmethod
    def get_all_students():
        return Student.objects.all()        