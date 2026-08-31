from django.http import JsonResponse

class ApiResponse:
    @staticmethod
    def success(message, data = None, status = 200):
        response = {
            "success": True,
            "message": message,
        }

        if data:
            response.update(data)

        return JsonResponse(response, status = status)

    @staticmethod
    def error(message, status = 400):
        return JsonResponse(
            {
                "success": False,
                "message": message,
            },
            status = status,
        )