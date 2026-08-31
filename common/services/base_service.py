class BaseService:
    def __init__(self,model):
        self.model = model

    def get(self,object_id):
        return self.model.objects.get(id = object_id,is_deleted = False) if hasattr(self.model,"is_deleted") else self.model.objects.get(id = object_id)

    def get_all(self):
        return self.model.objects.filter(is_deleted = False) if hasattr(self.model,"is_deleted") else self.model.objects.all()

    def delete(self,object_id):
        obj = self.get(object_id)
        if hasattr(obj,"is_deleted"):
            obj.is_deleted = True
            obj.save(update_fields = ["is_deleted","updated_at"] if hasattr(obj,"updated_at") else ["is_deleted"])
        else:
            obj.delete()