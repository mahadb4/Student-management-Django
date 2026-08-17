class BaseService:
    def __init__(self, model):
        self.model = model

    def get(self, object_id):
        return self.model.objects.get(id=object_id)

    def get_all(self):
        return self.model.objects.all()

    def delete(self, object_id):
        obj = self.get(object_id)
        obj.delete()