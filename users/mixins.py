"""Mixins para restringir vistas por rol (técnico vs supervisor)."""
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Rol
from .permissions import es_admin_roa


class TecnicoRequiredMixin(LoginRequiredMixin):
    """Solo usuarios con rol Técnico. Supervisores se redirigen al dashboard."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if getattr(request.user, 'rol', None) != Rol.TECNICO:
            return redirect('analytics:dashboard')
        return super().dispatch(request, *args, **kwargs)


class SupervisorRequiredMixin(LoginRequiredMixin):
    """Permite supervisores y admin ROA; los técnicos van al inventario."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        es_supervisor = getattr(request.user, 'rol', None) == Rol.SUPERVISOR
        if not (es_supervisor or es_admin_roa(request.user)):
            return redirect('inventory:empresas')
        return super().dispatch(request, *args, **kwargs)


class StaffRequiredMixin(LoginRequiredMixin):
    """Solo admin ROA (staff o superusuario)."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not es_admin_roa(request.user):
            if getattr(request.user, 'rol', None) == Rol.SUPERVISOR:
                return redirect('analytics:dashboard')
            return redirect('inventory:empresas')
        return super().dispatch(request, *args, **kwargs)
