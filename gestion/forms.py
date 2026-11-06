from django import forms
from django.contrib.auth.forms import UserCreationForm

from inventory.models import Cliente, Empresa
from users.models import Rol, Tecnico


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ('nombre', 'nit', 'logo', 'activo')
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SedeForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ('empresa', 'codigo', 'nombre', 'dir_cliente', 'activo')
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'dir_cliente': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SupervisorCreateForm(UserCreationForm):
    empresas_visibles = forms.ModelMultipleChoiceField(
        queryset=Empresa.objects.order_by('nombre'),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Empresas visibles',
        help_text='El supervisor solo podrá consultar reportes de estas empresas.',
    )

    class Meta(UserCreationForm.Meta):
        model = Tecnico
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'activo', 'empresas_visibles',
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Rol.SUPERVISOR
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario


class SupervisorUpdateForm(forms.ModelForm):
    empresas_visibles = forms.ModelMultipleChoiceField(
        queryset=Empresa.objects.order_by('nombre'),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Empresas visibles',
        help_text='El supervisor solo podrá consultar reportes de estas empresas.',
    )

    class Meta:
        model = Tecnico
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'activo', 'empresas_visibles',
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Rol.SUPERVISOR
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario
