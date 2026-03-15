import os
import django
import json
import sys

# Preparar entorno Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from leads.parser_service import orquestar_ingesta_historica
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

casos_de_uso = [
    {
        "nombre": "Dr. Juan De La Garza Perez",
        "telefono": "55 1234 5678",
        "especialidad": "Dermatología",
        "ubicacion": "CDMX"
    },
    {
        "nombre": "Dra. Maria y Dr. Jose Lopez",
        "telefono": "55 1111 2222",
        "especialidad": "Odontología",
        "ubicacion": "GDL"
    },
    {
        "nombre": "CLINICA VETERINARIA DOGGIE",
        "telefono": "81 3333 4444",
        "especialidad": "Veterinaria",
        "ubicacion": "MTY"
    },
    {
        "nombre": "Pedro Ruiz",
        "telefono": "44 5555 6666",
        "especialidad": "Fisioterapia",
        "ubicacion": "QRO"
    }
]

print("Iniciando Simulacro de Ingesta Histórica (Dry Run)...")
reporte = orquestar_ingesta_historica(
    filas_data=casos_de_uso,
    admin_user=admin_user,
    dry_run=True
)

print("\n=== REPORTE DRY RUN ===")
print(json.dumps(reporte, indent=2, ensure_ascii=False))
print("=======================")
