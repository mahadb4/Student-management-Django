from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = list(request.user.groups.values_list("name", flat=True))

        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "role": groups[0] if groups else None,
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
        })