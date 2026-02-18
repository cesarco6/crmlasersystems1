# backend/leads/services.py
import uuid
import pandas as pd
from django.utils import timezone
from django.db import transaction
from .models import CoreLead, LeadDispute

class IngestionService:
    @staticmethod
    def _crear_nota_sistema(tipo, contenido, usuario_id):
        """Genera la estructura de nota según el esquema JSONB del usuario."""
        return {
            "id": str(uuid.uuid4()),
            "tipo": tipo,
            "contenido": contenido,
            "usuario": usuario_id,
            "fecha": timezone.now().isoformat()
        }

    @classmethod
    @transaction.atomic
    def carga_inicial_masiva(cls, df, director_user):
        """
        MODO CARGA INICIAL (Solo Director):
        Carga directa del historial sin validación de arbitraje.
        """
        leads_creados = 0
        for _, row in df.iterrows():
            # Creamos la nota de historial inicial
            nota_inicial = cls._crear_nota_sistema(
                "contacto", 
                "Carga masiva histórica de inicio de operación", 
                director_user.id
            )
            
            # Se crea el registro directamente (Carga Directa)
            CoreLead.objects.create(
                owner=director_user,
                phone_primary=str(row.get('telefono')),
                nombre=row.get('nombre'),
                especialidad=row.get('especialidad', 'General'),
                producto_interes=row.get('producto', 'Desconocido'),
                ubicacion_id=row.get('ubicacion_id'),
                notas_variadas={
                    "notas": [nota_inicial],
                    "campos_dinamicos": {},
                    "columnas_excel_historicas": row.to_dict() # Guardamos todo el excel original aquí
                }
            )
            leads_creados += 1
        return leads_creados

    @classmethod
    @transaction.atomic
    def ingesta_operativa_m1(cls, datos_fila, usuario_actual):
        """
        MODO OPERATIVO: Implementación de los 5 casos de Ingesta (DDS 2.0).
        Se ejecuta durante la operación diaria del CRM.
        """
        telefono = str(datos_fila.get('phone_primary'))
        lead_existente = CoreLead.objects.filter(phone_primary=telefono).first()

        # --- CASO A: REGISTRO NUEVO ---
        if not lead_existente:
            nueva_nota = cls._crear_nota_sistema("contacto", "Carga vía M1 Operativo", usuario_actual.id)
            return CoreLead.objects.create(
                owner=usuario_actual,
                phone_primary=telefono,
                nombre=datos_fila.get('nombre'),
                especialidad=datos_fila.get('especialidad'),
                producto_interes=datos_fila.get('producto_interes'),
                ubicacion_id=datos_fila.get('ubicacion_id'),
                notas_variadas={"notas": [nueva_nota], "campos_dinamicos": {}, "columnas_excel_historicas": {}}
            )

        # --- CASO B y D: MISMO DUEÑO ---
        if lead_existente.owner == usuario_actual:
            if lead_existente.estatus == 'CLIENTE':
                # CASO D: Notificar Cliente Histórico
                return {"status": "NOTIFICACION_CLIENTE", "lead": lead_existente}
            
            # CASO B: Actualización de historial JSON
            nueva_nota = cls._crear_nota_sistema("seguimiento", "Actualización M1", usuario_actual.id)
            lead_existente.notas_variadas["notas"].append(nueva_nota)
            lead_existente.save()
            return {"status": "ACTUALIZADO", "lead": lead_existente}

        # --- CASO C y E: DUEÑO DISTINTO ---
        diferencia_tiempo = timezone.now() - lead_existente.updated_at
        es_menor_un_ano = diferencia_tiempo.days < 365

        if es_menor_un_ano:
            # CASO C: ARBITRAJE (BLOQUEO Y DISPUTA)
            LeadDispute.objects.create(
                lead=lead_existente,
                claimant_user=usuario_actual,
                tipo_conflicto='DUPLICADO_IMPORT',
                notas_resolucion="Conflicto detectado en carga masiva operativa M1."
            )
            return {"status": "BLOQUEADO_DISPUTA", "lead": lead_existente}
        else:
            # CASO E: REGISTRO ANTIGUO (> 1 año)
            nota_e = cls._crear_nota_sistema("seguimiento", "Reactivación solicitada (> 1 año)", usuario_actual.id)
            lead_existente.notas_variadas["notas"].append(nota_e)
            lead_existente.save()
            return {"status": "MARCADO_REACTIVACION", "lead": lead_existente}