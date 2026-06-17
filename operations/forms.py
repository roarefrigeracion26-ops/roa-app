"""
Formularios para SGMAA.
"""
from django import forms
from django.utils import timezone
from .models import TipoMantenimiento, EquipoIntervenido, MedicionUCA, MedicionSplit, MedicionCondensadoraRack, Actividad

REFRIGERANTE_CHOICES = [
    ('', '— Seleccionar —'),
    ('R410A', 'R410A'),
    ('R22', 'R22'),
    ('R32', 'R32'),
    ('R407C', 'R407C'),
    ('R134A', 'R134A'),
    ('R404A', 'R404A'),
    ('Otro', 'Otro'),
]

TIPO_EQUIPO_CHOICES = [
    ('', '— Seleccionar —'),
    ('UCA', 'UCA — Unidad Condensadora'),
    ('UMA', 'UMA — Unidad Manejadora'),
    ('SPLIT', 'Split'),
    ('CASSETTE', 'Cassette'),
    ('PISO_TECHO', 'Piso Techo'),
    ('PAQUETE', 'Paquete'),
    ('CONDENSADORA_RACK', 'Condensadora Rack Refrigeración'),
    ('OTRO', 'Otro'),
]


def _num_input(placeholder='', step='0.01'):
    return forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': placeholder,
        'inputmode': 'decimal',
        'step': step,
    })


def _text_input(placeholder=''):
    return forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': placeholder,
    })


class NuevaOrdenForm(forms.Form):
    """Paso 1: Tipo de mantenimiento, radicado y datos generales del encabezado."""
    tipo = forms.ChoiceField(
        choices=TipoMantenimiento.choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Tipo de mantenimiento',
    )
    radicado_numero = forms.CharField(
        max_length=10,
        label='Número de radicado',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '9167',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
        help_text='Solo los dígitos, sin el prefijo MP/MC.',
    )
    cliente_nombre = forms.CharField(
        max_length=200, label='Cliente',
        widget=_text_input('Ej: OLIMPICA S.A.'),
    )
    dir_cliente = forms.CharField(
        max_length=300, label='Dir. Cliente', required=False,
        widget=_text_input('Ej: 1059'),
    )
    fecha = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        initial=timezone.localdate,
    )
    mes = forms.CharField(
        max_length=20, label='Mes', required=False,
        widget=_text_input('Ej: 8/2025'),
    )

    def get_radicado(self):
        """Construye el radicado completo: 'MP1234' o 'MC1234'."""
        tipo = self.cleaned_data.get('tipo', '')
        numero = self.cleaned_data.get('radicado_numero', '')
        return f'{tipo}{numero}'

class NuevaOrdenClienteForm(NuevaOrdenForm):
    """Formulario para la tienda. Fuerza el tipo MP y esconde la selección de MC."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].initial = 'MP'
        self.fields['tipo'].widget = forms.HiddenInput()


class EquipoIntervenidoForm(forms.ModelForm):
    """Datos completos de cada equipo intervenido en la orden."""
    refrigerante = forms.ChoiceField(
        choices=REFRIGERANTE_CHOICES, required=False, label='Refrigerante',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    tipo_equipo = forms.ChoiceField(
        choices=TIPO_EQUIPO_CHOICES, required=False, label='Tipo de equipo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = EquipoIntervenido
        fields = [
            'nombre_equipo', 'ubicacion', 'tipo_equipo', 'marca', 'modelo',
            'capacidad', 'refrigerante', 'voltaje',
            'corriente_l1', 'corriente_l2', 'corriente_l3',
            'amperaje_l1', 'amperaje_l2', 'amperaje_l3',
            'fases', 'tipo_correa', 'activo_fijo',
        ]
        widgets = {
            'nombre_equipo': _text_input('Ej: UCA 1'),
            'ubicacion': _text_input('Ej: AZOTEA'),
            'marca': _text_input('Ej: CONFORTFRESH'),
            'modelo': _text_input('Ej: CPV13300X2-B3'),
            'capacidad': _text_input('Ej: 25TR'),
            'voltaje': _text_input('Ej: 220 V'),
            'corriente_l1': _num_input('L1'),
            'corriente_l2': _num_input('L2'),
            'corriente_l3': _num_input('L3'),
            'amperaje_l1': _num_input('L1'),
            'amperaje_l2': _num_input('L2'),
            'amperaje_l3': _num_input('L3'),
            'fases': _text_input('Ej: 3 PH 60HZ'),
            'tipo_correa': _text_input('Ej: BX38'),
            'activo_fijo': _text_input('Ej: 1433977'),
        }
        labels = {
            'nombre_equipo': 'Nombre del equipo',
            'corriente_l1': 'Corriente L1 (A)',
            'corriente_l2': 'Corriente L2 (A)',
            'corriente_l3': 'Corriente L3 (A)',
            'amperaje_l1': 'Amperaje L1 (A)',
            'amperaje_l2': 'Amperaje L2 (A)',
            'amperaje_l3': 'Amperaje L3 (A)',
        }


class MedicionUCAForm(forms.ModelForm):
    """Presiones por circuito para equipos UCA."""
    class Meta:
        model = MedicionUCA
        fields = ['circuito', 'baja_p_antes', 'baja_p_despues', 'alta_p_antes', 'alta_p_despues']
        widgets = {
            'circuito': forms.HiddenInput(),
            'baja_p_antes': _num_input('PSI'),
            'baja_p_despues': _num_input('PSI'),
            'alta_p_antes': _num_input('PSI'),
            'alta_p_despues': _num_input('PSI'),
        }


class MedicionSplitForm(forms.ModelForm):
    """Temperaturas suministro/retorno para UMA y SPLIT."""
    class Meta:
        model = MedicionSplit
        fields = ['temp_sumin_antes', 'temp_sumin_despues', 'temp_retorno_antes', 'temp_retorno_despues']
        widgets = {
            'temp_sumin_antes': _num_input('°C'),
            'temp_sumin_despues': _num_input('°C'),
            'temp_retorno_antes': _num_input('°C'),
            'temp_retorno_despues': _num_input('°C'),
        }


class ActividadForm(forms.ModelForm):
    """Formulario individual para editar/marcar una actividad del checklist."""
    class Meta:
        model = Actividad
        fields = ['texto', 'marcada']
        widgets = {
            'texto': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'marcada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ActividadCorrectivForm(forms.Form):
    """Para correctivos: texto libre de actividades realizadas."""
    actividades_texto = forms.CharField(
        label='Actividades realizadas',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Describa las actividades realizadas durante el mantenimiento correctivo...',
        })
    )


class MedicionCondensadoraRackForm(forms.ModelForm):
    """Mediciones para lavado de condensadora de rack de refrigeración."""
    class Meta:
        model = MedicionCondensadoraRack
        fields = [
            'corriente_l1_antes', 'corriente_l2_antes', 'corriente_l3_antes',
            'presion_entrada_antes', 'temp_salida_antes',
            'corriente_l1_despues', 'corriente_l2_despues', 'corriente_l3_despues',
            'presion_entrada_despues', 'temp_salida_despues', 'temp_ambiente_despues',
            'total_abanicos', 'abanicos_operativos',
        ]
        widgets = {
            'corriente_l1_antes': _num_input('L1'),
            'corriente_l2_antes': _num_input('L2'),
            'corriente_l3_antes': _num_input('L3'),
            'presion_entrada_antes': _num_input('PSI'),
            'temp_salida_antes': _num_input('°C'),
            'corriente_l1_despues': _num_input('L1'),
            'corriente_l2_despues': _num_input('L2'),
            'corriente_l3_despues': _num_input('L3'),
            'presion_entrada_despues': _num_input('PSI'),
            'temp_salida_despues': _num_input('°C'),
            'temp_ambiente_despues': _num_input('°C'),
            'total_abanicos': forms.NumberInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'step': '1'}),
            'abanicos_operativos': forms.NumberInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'step': '1'}),
        }


class ObservacionForm(forms.Form):
    """Observación libre por equipo intervenido."""
    texto = forms.CharField(
        label='Observaciones',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ej: Serpín evaporador y condensador se presentaba suciedad leve.',
        })
    )
