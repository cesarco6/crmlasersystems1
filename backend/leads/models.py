import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from users.models import CatUbicacion

def default_notas_variadas():
    """Define la estructura base del JSONB según el esquema del usuario."""
    return {
        "notas": [],
        "campos_dinamicos": {},
        "columnas_excel_historicas": {}
    }

class CoreLead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='leads')
    ubicacion = models.ForeignKey(CatUbicacion, on_delete=models.PROTECT, related_name='leads_en_zona')
    
    # Identidad (UK y Datos Base)
    phone_primary = models.CharField(max_length=15, unique=True)
    celular = models.CharField(max_length=15, blank=True)
    nombre = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=50)
    producto_interes = models.CharField(max_length=50)
    
    # Operación
    email = models.EmailField(blank=True, null=True)
    direccion_completa = models.CharField(max_length=255, blank=True)
    estatus = models.CharField(max_length=20, default='PROSPECTO')
    calificacion = models.IntegerField(default=0)
    plan = models.CharField(max_length=50, default='SEGUIMIENTO')
    # Usamos el método default para que cada lead nuevo tenga la estructura limpia
    notas_variadas = models.JSONField(default=default_notas_variadas)

    def save(self, *args, **kwargs):
        if self.pk:
            original = CoreLead.objects.get(pk=self.pk)
            # Candado de Integridad DDS 2.0 (Fase 2)
            if original.estatus != 'PROSPECTO':
                campos_bloqueados = ['phone_primary', 'nombre', 'especialidad', 'producto_interes']
                for campo in campos_bloqueados:
                    if getattr(self, campo) != getattr(original, campo):
                        raise ValidationError(f"Violación DDS: {campo} es inmutable.")
        super().save(*args, **kwargs)

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

class LeadDispute(models.Model):
    lead = models.ForeignKey(CoreLead, on_delete=models.CASCADE, related_name='conflictos')
    claimant_user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Quien reclama")
    tipo_conflicto = models.CharField(max_length=30, choices=[
        ('DUPLICADO_IMPORT', 'Duplicado en Importación'),
        ('RECLAMO_MANUAL', 'Reclamo Manual de Propiedad')
    ])
    status = models.CharField(max_length=20, choices=[
        ('PENDIENTE', 'Pendiente'),
        ('RESUELTO', 'Resuelto'),
        ('RECHAZADO', 'Rechazado')
    ], default='PENDIENTE')
    notas_resolucion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)