from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.views import View

from .forms import LoginForm


class LoginView(View):
    """Solo usuarios activos pueden ingresar. Supervisor → reportes, Técnico → inicio."""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('analytics:dashboard' if request.user.is_supervisor else 'inventory:clientes')
        return render(request, 'users/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('analytics:dashboard' if user.is_supervisor else 'inventory:clientes')
        return render(request, 'users/login.html', {'form': form})

