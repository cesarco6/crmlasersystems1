# backend/leads/services.py
import pandas as pd
from .models import CoreLead
from django.utils import timezone

class LeadIngestionService:
    @staticmethod
    def carga_inicial_director(file_path, director_user):
        """
        MODO CARGA INICIAL: Sin validación de los 5 casos.
        Pobla el sistema con el historial existente.
        """
        df = pd.read_excel(file_path) # Usamos pandas definido en requirements
        for _, row in df.iterrows():
            # Aquí mapeamos directamente las columnas al modelo
            # y metemos todo el sobrante a columnas_excel_historicas
            CoreLead.objects.create(
                phone_primary=row['telefono'],
                nombre=row['nombre'],
                owner=director_user,
                # ... resto de campos ...
            )

    @staticmethod
    def ingesta_operativa_m1(datos_fila, usuario_actual):
        """
        MODO OPERATIVO: Implementa los 5 casos de Ingesta y Adaptador.
        """
        # Aquí programaremos la lógica de:
        # Caso A: Nuevo -> Crear
        # Caso B: Mismo dueño -> Append Notas
        # Caso C: Arbitraje -> Crear LeadDispute
        # Caso D: Cliente -> Notificar
        # Caso E: Antiguo -> Marcar revisión
        pass