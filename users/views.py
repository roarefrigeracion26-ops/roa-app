from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.views import View

from .forms import LoginForm
from .permissions import es_admin_roa


def _destino_por_rol(user):
    if user.is_supervisor or es_admin_roa(user):
        return 'analytics:dashboard'
    return 'inventory:empresas'


class LoginView(View):
    """Solo usuarios activos pueden ingresar. Supervisores y admin ROA → reportes."""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(_destino_por_rol(request.user))
        return render(request, 'users/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect(_destino_por_rol(user))
        return render(request, 'users/login.html', {'form': form})

