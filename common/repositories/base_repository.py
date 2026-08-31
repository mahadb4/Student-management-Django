class BaseRepository:

    def __init__(self, model):
        self.model = model

    def get(self, object_id):
        queryset = self.model.objects

        if hasattr(self.model, "is_deleted"):
            queryset = queryset.filter(is_deleted = False)

        return queryset.get(id = object_id)

    def get_all(self):
        queryset = self.model.objects

        if hasattr(self.model, "is_deleted"):
            queryset = queryset.filter(is_deleted = False)

        return queryset.all()

    def delete(self, object_id):
        obj = self.get(object_id)

        if hasattr(obj, "is_deleted"):
            obj.is_deleted = True
            update_fields = ["is_deleted"]

            if hasattr(obj, "updated_at"):
                update_fields.append("updated_at")

            obj.save(update_fields = update_fields)
        else:
            obj.delete()