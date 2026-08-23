from functools import wraps
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.messages import Messages

def enforce_permissions(app_label, model_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            authentication = JWTAuthentication()
            try:
                authentication_result = authentication.authenticate(request)
            except Exception:
                authentication_result = None

            if authentication_result is None:
                return JsonResponse({"error": Messages.AUTHENTICATION_REQUIRED}, status=401)
                
            user, token = authentication_result
            request.user = user

            # Map HTTP method to permission action
            method_action_map = {
                'GET': 'view',
                'POST': 'add',
                'PUT': 'change',
                'PATCH': 'change',
                'DELETE': 'delete'
            }
            action = method_action_map.get(request.method)
            if action:
                perm = f"{app_label}.{action}_{model_name}"
                if not user.has_perm(perm):
                    return JsonResponse({"error": Messages.PERMISSION_DENIED.format(perm)}, status=403)
                    
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
