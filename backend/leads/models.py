# leads/models.py
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from users.models import CatUbicacion
from django_fsm import FSMField, transition
from django.utils import timezone

def default_notas_variadas():
    """Define la estructura base del JSONB según el esquema del usuario."""
    return {
        "notas": [],
        "columnas_excel_historicas": {}
    }

class CoreLead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='leads')
    ubicacion = models.ForeignKey(CatUbicacion, on_delete=models.PROTECT, related_name='leads_en_zona')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Identidad (UK y Datos Base)
    phone_primary = models.CharField(max_length=15)
    celular = models.CharField(max_length=15, blank=True)
    nombre = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=50)
    producto_interes = models.CharField(max_length=50)
    
    # Operación
    email = models.EmailField(blank=True, null=True)
    direccion_completa = models.CharField(max_length=255, blank=True)
    estatus = FSMField(default='PROSPECTO', protected=True)
    calificacion = models.IntegerField(default=0)
    plan = models.CharField(max_length=50, default='SEGUIMIENTO')
    # Usamos el método default para que cada lead nuevo tenga la estructura limpia
    notas_variadas = models.JSONField(default=default_notas_variadas)

    def save(self, *args, **kwargs):
        # Usamos _state.adding para saber si el registro ya existe en la DB
        if not self._state.adding:
            original = CoreLead.objects.get(pk=self.pk)
            # Candado de Integridad DDS 2.0 (Fase 2)
            if original.estatus != 'PROSPECTO':
                campos_bloqueados = ['phone_primary', 'nombre', 'especialidad', 'producto_interes']
                for campo in campos_bloqueados:
                    if getattr(self, campo) != getattr(original, campo):
                        raise ValidationError(f"Violación DDS: {campo} es inmutable.")
        super().save(*args, **kwargs)

    @transition(field=estatus, source='PROSPECTO', target='LEAD')
    def validar_identidad(self):
        """Fase 1 a 2: Identidad confirmada. Activa candados de edición."""
        pass

    @transition(field=estatus, source='LEAD', target='LEAD_CALIFICADO')
    def calificar_lead(self):
        """Fase 2: Presentación hecha. Requiere temperatura Alta/Media/Baja."""
        pass

    @transition(field=estatus, source='LEAD_CALIFICADO', target='CLIENTE')
    def formalizar_cliente(self):
        """Fase 3: Cierre exitoso. Bloqueante si no hay datos fiscales."""
        if not hasattr(self, 'fiscalprofile') or not self.fiscalprofile.rfc:
            raise Exception("No se puede formalizar a CLIENTE sin un Perfil Fiscal completo.")

    def pausar_seguimiento(self, fecha_reactivacion):
        """Fase 2: Acuerdo a futuro. Modifica PLAN, mantiene ESTATUS."""
        if not fecha_reactivacion:
            raise Exception("Debes indicar una fecha para volver a contactarlo.")
        self.plan = 'EN_ESPERA'
        self.next_action_date = fecha_reactivacion
        self.save()

    @transition(field=estatus, source=['PROSPECTO', 'LEAD', 'LEAD_CALIFICADO'], target='NO_CIERRE')
    def archivar_sin_exito(self, nota_motivo, usuario_id):
        """Fase 3: Archivo definitivo con justificación obligatoria."""
        if not nota_motivo:
            raise Exception("Debes escribir una nota aclaratoria explicando el rechazo.")
        
        nueva_nota = {
            "tipo": "descarte",
            "contenido": nota_motivo,
            "usuario": usuario_id,
            "fecha": timezone.now().isoformat()
        }
        if not isinstance(self.notas_variadas, dict):
            self.notas_variadas = {}
        self.notas_variadas.setdefault("notas", []).append(nueva_nota)
        
        self.plan = 'DESCARTADO'
        self.next_action_date = None

    @transition(field=estatus, source='NO_CIERRE', target='PROSPECTO')
    def reactivar_historico(self, nuevo_owner_id):
        """Caso D: Reactivación tras 1 año de inactividad."""
        self.owner_id = nuevo_owner_id
        self.plan = 'SEGUIMIENTO'
        self.next_action_date = timezone.now().date()

class FiscalProfile(models.Model):
    lead = models.OneToOneField(CoreLead, on_delete=models.CASCADE, related_name='perfil_fiscal')
    rfc = models.CharField(max_length=13)
    razon_social = models.CharField(max_length=200)
    regimen_fiscal = models.CharField(max_length=100)
    calle = models.CharField(max_length=100)
    colonia = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    cp = models.CharField(max_length=5)
