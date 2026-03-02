"""Mixins para restringir vistas por rol (técnico vs supervisor)."""
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Rol


class TecnicoRequiredMixin(LoginRequiredMixin):
    """Solo usuarios con rol Técnico. Supervisores se redirigen al dashboard."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if getattr(request.user, 'rol', None) != Rol.TECNICO:
            return redirect('analytics:dashboard')
        return super().dispatch(request, *args, **kwargs)


class SupervisorRequiredMixin(LoginRequiredMixin):
    """Solo usuarios con rol Supervisor. Técnicos se redirigen al escáner."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if getattr(request.user, 'rol', None) != Rol.SUPERVISOR:
            return redirect('inventory:clientes')
        return super().dispatch(request, *args, **kwargs)
