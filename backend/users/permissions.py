# backend/users/permissions.py
from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(allowed_roles=[]):
    """
    Decorador para restringir el acceso según el rol definido en UserProfile.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Verificamos si el usuario tiene perfil y si su rol está permitido
            if not hasattr(request.user, 'profile') or request.user.profile.rol not in allowed_roles:
                raise PermissionDenied("No tienes permisos para realizar esta acción.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator