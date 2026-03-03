import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from operations.models import OrdenServicio
from django.contrib.auth import get_user_model

User = get_user_model()

def check_order(pk):
    try:
        orden = OrdenServicio.objects.get(pk=pk)
        print(f"Orden ID: {orden.pk}")
        print(f"Radicado: {orden.radicado}")
        print(f"Estado: {orden.estado}")
        print(f"Tecnico: {orden.tecnico.username} (ID: {orden.tecnico.pk})")
        print(f"Fecha: {orden.fecha}")
        
        print("\nUsuarios en el sistema:")
        for user in User.objects.all():
            print(f"- {user.username} (ID: {user.pk})")
            
    except OrdenServicio.DoesNotExist:
        print(f"Error: La orden con ID {pk} no existe.")

if __name__ == "__main__":
    check_order(5)
