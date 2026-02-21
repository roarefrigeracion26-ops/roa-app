"""
Formularios para parámetros de entrada (check-in) y salida (check-out).
Corriente por compresor según rack; presiones fijas. Estructura en datos_entrada/datos_salida JSON.
"""
from django import forms

MAX_COMPRESORES = 24  # límite para no generar demasiados campos


def _corriente_field(numero, etiqueta_extra=''):
    """Campo de corriente (A) para un compresor."""
    label = f'Corriente compresor {numero} (A)'
    if etiqueta_extra:
        label = f'Corriente compresor {numero} {etiqueta_extra} (A)'
    return forms.DecimalField(
        label=label,
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'A'})
    )


class ParametrosEntradaForm(forms.Form):
    """
    Check-in: corriente por compresor (según rack) + presiones.
    Recibe rack en __init__ para generar N campos de corriente.
    """
    # Presiones fijas
    presion_succion_media = forms.DecimalField(
        label='Presión succión media temperatura (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    presion_succion_baja = forms.DecimalField(
        label='Presión succión baja temperatura (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    presion_descarga = forms.DecimalField(
        label='Presión descarga (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    presion_entrada_condensacion = forms.DecimalField(
        label='Presión entrada condensación (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    presion_salida_condensacion = forms.DecimalField(
        label='Presión salida condensación (psi)',
        required=False,
        min_value=0,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    def __init__(self, *args, rack=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rack = rack
        if rack:
            n = min(rack.total_compresores or 0, MAX_COMPRESORES)
            media = rack.compresores_media or 0
            for i in range(1, n + 1):
                if i <= media:
                    etiqueta = '(media)'
                else:
                    etiqueta = '(baja)'
                self.fields[f'corriente_compresor_{i}'] = _corriente_field(i, etiqueta)

    def to_json(self):
        from decimal import Decimal
        data = {}
        for k, v in self.cleaned_data.items():
            if v is not None and v != '':
                if isinstance(v, Decimal):
                    data[k] = float(v)
                elif isinstance(v, (int, float)):
                    data[k] = v
                else:
                    data[k] = str(v)
        return data


class ParametrosSalidaForm(ParametrosEntradaForm):
    """Mismos campos que entrada (corriente por compresor + presiones) para comparar al cierre."""
    pass


class CierreForm(forms.Form):
    """Check-out: observación del trabajo realizado."""
    observaciones = forms.CharField(
        label='Observaciones del trabajo realizado',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Ej: Cambio de compresor, recarga de gas, ajuste de presiones...'
        })
    )
