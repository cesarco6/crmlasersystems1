# backend/leads/services.py
from django.utils import timezone
from .models import CoreLead

class IngestionService:
    @classmethod
    def procesar_fila_m1(cls, datos_fila, usuario_ejecutor):
        """
        Protocolo de Ingesta Simplificado (DDS 2.0).
        
        """
        telefono = str(datos_fila.get('phone_primary'))
        lead_existente = CoreLead.objects.filter(phone_primary=telefono).first()

        # --- CASO A: REGISTRO NUEVO ---
        if not lead_existente:
            return {
                "accion": "CREAR",
                "data": {**datos_fila, "owner": usuario_ejecutor, "estatus": "PROSPECTO"}
            }

        # Cálculo de antigüedad basado en la última actividad
        antiguedad_dias = (timezone.now() - lead_existente.updated_at).days
        es_activo = antiguedad_dias <= 365

        # --- CASO D: CLIENTE HISTÓRICO ---
        if lead_existente.estatus == 'CLIENTE':
            return {"accion": "IGNORAR_CLIENTE", "lead": lead_existente}

        # --- CASO E: REACTIVACIÓN (> 1 AÑO) ---
        if not es_activo:
            # El lead estaba "dormido". El nuevo vendedor puede solicitar reactivarlo.
            return {"accion": "REVISION_MANUAL_REACTIVACION", "lead": lead_existente}

        # --- CASO B: PROPIEDAD AJENA ACTIVA (< 1 AÑO) ---
        if lead_existente.owner != usuario_ejecutor:
            # Bloqueo automático por sistema: El lead le pertenece a alguien más.
            return {
                "accion": "AVISO_BLOQUEO_PROPIEDAD", 
                "lead": lead_existente,
                "mensaje": f"Lead activo protegido. Pertenece a {lead_existente.owner.username}"
            }

        # --- MISMO OWNER ---
        return {"accion": "AVISO_MISMO_OWNER", "lead": lead_existente}