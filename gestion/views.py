from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, View

from inventory.models import Cliente, Empresa
from users.mixins import StaffRequiredMixin
from users.models import Rol, Tecnico

from .forms import (
    EmpresaForm,
    SedeForm,
    SupervisorCreateForm,
    SupervisorUpdateForm,
)


class GestionIndexView(StaffRequiredMixin, TemplateView):
    template_name = 'gestion/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_empresas'] = Empresa.objects.count()
        context['total_sedes'] = Cliente.objects.count()
        context['total_supervisores'] = Tecnico.objects.filter(
            rol=Rol.SUPERVISOR
        ).count()
        return context


class EmpresaListView(StaffRequiredMixin, ListView):
    model = Empresa
    template_name = 'gestion/empresa_list.html'
    context_object_name = 'empresas'

    def get_queryset(self):
        return Empresa.objects.annotate(total_sedes=Count('sedes')).order_by('nombre')


class EmpresaCreateView(StaffRequiredMixin, CreateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'gestion/empresa_form.html'
    success_url = reverse_lazy('gestion:empresas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva empresa'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Empresa creada correctamente.')
        return super().form_valid(form)


class EmpresaUpdateView(StaffRequiredMixin, UpdateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'gestion/empresa_form.html'
    success_url = reverse_lazy('gestion:empresas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar empresa'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Empresa actualizada correctamente.')
        return super().form_valid(form)


class EmpresaToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        empresa = get_object_or_404(Empresa, pk=pk)
        empresa.activo = not empresa.activo
        empresa.save(update_fields=['activo'])
        estado = 'activada' if empresa.activo else 'desactivada'
        messages.success(request, f'Empresa {estado} correctamente.')
        return redirect('gestion:empresas')


class SedeListView(StaffRequiredMixin, ListView):
    model = Cliente
    template_name = 'gestion/sede_list.html'
    context_object_name = 'sedes'

    def get_queryset(self):
        queryset = Cliente.objects.select_related('empresa').order_by(
            'empresa__nombre', 'nombre'
        )
        empresa_id = self.request.GET.get('empresa', '').strip()
        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresas'] = Empresa.objects.order_by('nombre')
        context['empresa_seleccionada'] = self.request.GET.get('empresa', '')
        return context


class SedeCreateView(StaffRequiredMixin, CreateView):
    model = Cliente
    form_class = SedeForm
    template_name = 'gestion/sede_form.html'
    success_url = reverse_lazy('gestion:sedes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva sede'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Sede creada correctamente.')
        return super().form_valid(form)


class SedeUpdateView(StaffRequiredMixin, UpdateView):
    model = Cliente
    form_class = SedeForm
    template_name = 'gestion/sede_form.html'
    success_url = reverse_lazy('gestion:sedes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar sede'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Sede actualizada correctamente.')
        return super().form_valid(form)


class SedeToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        sede = get_object_or_404(Cliente, pk=pk)
        sede.activo = not sede.activo
        sede.save(update_fields=['activo'])
        estado = 'activada' if sede.activo else 'desactivada'
        messages.success(request, f'Sede {estado} correctamente.')
        return redirect('gestion:sedes')


class SupervisorListView(StaffRequiredMixin, ListView):
    model = Tecnico
    template_name = 'gestion/supervisor_list.html'
    context_object_name = 'supervisores'

    def get_queryset(self):
        return Tecnico.objects.filter(rol=Rol.SUPERVISOR).prefetch_related(
            'empresas_visibles'
        ).order_by('username')


class SupervisorCreateView(StaffRequiredMixin, CreateView):
    model = Tecnico
    form_class = SupervisorCreateForm
    template_name = 'gestion/supervisor_form.html'
    success_url = reverse_lazy('gestion:supervisores')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo supervisor'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Supervisor creado correctamente.')
        return super().form_valid(form)


class SupervisorUpdateView(StaffRequiredMixin, UpdateView):
    model = Tecnico
    form_class = SupervisorUpdateForm
    template_name = 'gestion/supervisor_form.html'
    success_url = reverse_lazy('gestion:supervisores')

    def get_queryset(self):
        return Tecnico.objects.filter(rol=Rol.SUPERVISOR)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar supervisor'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Supervisor actualizado correctamente.')
        return super().form_valid(form)


class SupervisorToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        supervisor = get_object_or_404(Tecnico, pk=pk, rol=Rol.SUPERVISOR)
        supervisor.activo = not supervisor.activo
        supervisor.save(update_fields=['activo'])
        estado = 'activado' if supervisor.activo else 'desactivado'
        messages.success(request, f'Supervisor {estado} correctamente.')
        return redirect('gestion:supervisores')
