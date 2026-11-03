from django.shortcuts import redirect

from .models import Rol
from .permissions import es_admin_roa


class RestringirSupervisoresMiddleware:
    """Los supervisores de clientes solo pueden consultar reportes."""

    RUTAS_PERMITIDAS = (
        '/reportes/',
        '/ingresar/',
        '/logout/',
        '/static/',
        '/media/',
        '/favicon.ico',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user
            and user.is_authenticated
            and getattr(user, 'rol', None) == Rol.SUPERVISOR
            and not es_admin_roa(user)
        ):
            ruta = request.path_info
            if not any(ruta.startswith(permitida) for permitida in self.RUTAS_PERMITIDAS):
                return redirect('analytics:dashboard')
        return self.get_response(request)
