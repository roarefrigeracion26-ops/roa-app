from inventory.models import Empresa

from .models import Rol


def es_admin_roa(user):
    """True para staff o superusuario de ROA."""
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_staff or user.is_superuser)


def empresas_visibles(user):
    """Empresas activas que el usuario puede consultar."""
    if not user or not user.is_authenticated:
        return Empresa.objects.none()
    if es_admin_roa(user):
        return Empresa.objects.filter(activo=True)
    if getattr(user, 'rol', None) == Rol.SUPERVISOR:
        return user.empresas_visibles.filter(activo=True)
    return Empresa.objects.none()
