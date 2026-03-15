# leads/models.py
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from users.models import CatUbicacion, CatEspecialidad, CatProducto, CatTitulo
from users.models import UserProfile
from django_fsm import FSMField, transition
from django.utils import timezone
from django.conf import settings

def default_notas_variadas():
    """Define la estructura base del JSONB según el esquema del usuario."""
    return {
        "notas": [],
        "columnas_excel_historicas": {}
    }

class Clinica(models.Model):
    nombre = models.CharField(max_length=200)
    telefono_master = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Clínica / Grupo'
        verbose_name_plural = 'Clínicas y Grupos Corporativos'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.telefono_master})"

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
    
    # --- FASE 2: IDENTIDAD ATÓMICA ---
    titulo_cortesia = models.ForeignKey(CatTitulo, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    nombre_pila = models.CharField(max_length=100, null=True, blank=True)
    apellido_paterno = models.CharField(max_length=100, null=True, blank=True)
    apellido_materno = models.CharField(max_length=100, null=True, blank=True)

    especialidad = models.CharField(max_length=50)
    producto_interes = models.CharField(max_length=50)
    # --- NUEVOS CAMPOS RELACIONALES (Catálogos Limpios) ---
    especialidad_cat = models.ForeignKey(CatEspecialidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    producto_cat = models.ForeignKey(CatProducto, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    clinica = models.ForeignKey(Clinica, on_delete=models.SET_NULL, null=True, blank=True, related_name='medicos')
    
    # Operación
    email = models.EmailField(blank=True, null=True)
    direccion_completa = models.CharField(max_length=255, blank=True)
    estatus = FSMField(default='PROSPECTO', protected=True)
    calificacion = models.IntegerField(default=0)
    plan = models.CharField(max_length=50, default='SEGUIMIENTO')
    # LO ÚNICO NUEVO QUE VAMOS A AGREGAR ES ESTO:
    next_action_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Próximo Contacto")
    # Usamos el método default para que cada lead nuevo tenga la estructura limpia
    notas_variadas = models.JSONField(default=default_notas_variadas)

    @property
    def nombre_completo_mdm(self):
        """
        Concatena de forma inteligente los campos atómicos para no romper el Frontend.
        Si hay datos atómicos, los prioriza. Si no, usa el campo 'nombre' histórico.
        """
        if self.nombre_pila or self.apellido_paterno:
            partes = []
            if self.titulo_cortesia:
                partes.append(self.titulo_cortesia.nombre)
            if self.nombre_pila:
                partes.append(self.nombre_pila)
            if self.apellido_paterno:
                partes.append(self.apellido_paterno)
            if self.apellido_materno:
                partes.append(self.apellido_materno)
            return " ".join(partes)
        return self.nombre or ""

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
        if not hasattr(self, 'perfil_fiscal') or not self.perfil_fiscal.rfc:
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

class LeadStaging(models.Model):
    ESTATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente de Revisión'),
        ('RESUELTO', 'Resuelto / Inyectado'),
        ('DESCARTADO', 'Descartado / Basura'),
    ]
    
    # UUID para seguridad y ofuscación en URLs
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Quién subió el archivo que contenía este registro defectuoso
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads_staging')
    
    # La fila exacta de Excel convertida a diccionario JSON
    datos_crudos = models.JSONField(default=dict)
    
    # Lo que el parser intentó deducir (Nombres atomizados, etc)
    datos_parseados = models.JSONField(default=dict)
    
    # ¿Por qué este Lead cayó en Staging?
    motivo_conflicto = models.TextField()
    
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='PENDIENTE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Lead en Cuarentena'
        verbose_name_plural = 'Leads en Cuarentena'

    def __str__(self):
        return f"Staging {self.id} - {self.estatus}"

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


class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('estancamiento', 'Lead Estancado (> 30 días)'),
        ('reactivacion', 'Reactivación Programada'),
        ('no_cierre', 'Revisión de No Cierre'),
        ('fidelizacion', 'Seguimiento Post-Venta'),
        ('general', 'Aviso General'),
    ]

    # ¿A quién le aparece la alerta en su pantalla? (Vendedor o Director)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    
    # ¿Sobre qué Lead es la alerta? (Permite que al darle clic, lo lleve al perfil del cliente)
    lead = models.ForeignKey('CoreLead', on_delete=models.CASCADE, null=True, blank=True, related_name='notificaciones')
    
    mensaje = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    
    # El interruptor del Badge Rojo: False = Alerta encendida, True = Alerta apagada/atendida
    leida = models.BooleanField(default=False)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion'] # Las más nuevas aparecen primero
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'

    def __str__(self):
        return f"{self.tipo} para {self.usuario} - Leída: {self.leida}"

class VentaTransaccional(models.Model):
    """
    Tabla satélite para registrar ventas complementarias (Cross-selling) 
    sin afectar la máquina de estados de prospección principal (FSM).
    Aplica para: ACCESORIO, SERVICIO, EVENTO.
    """
    ESTATUS_CHOICES = [
        ('PENDIENTE', '🟡 Pendiente (Por contactar)'),
        ('EN_GESTION', '🔵 En Gestión (Contactado / Negociando)'),
        ('CONCRETADO', '🟢 Concretado (Ganado / Pagado)'),
        ('DESCARTADO', '🔴 Descartado (Perdido / No le interesa)'),
    ]
    lead = models.ForeignKey(CoreLead, on_delete=models.CASCADE, related_name='compras_extra')
    producto = models.ForeignKey(CatProducto, on_delete=models.PROTECT, related_name='ventas_transaccionales')
    vendedor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ventas_extra')
    
    fecha_venta = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='PENDIENTE')
    class Meta:
        ordering = ['-fecha_venta']
        verbose_name = 'Venta Transaccional'
        verbose_name_plural = 'Ventas Transaccionales'

    def __str__(self):
        return f"{self.producto.nombre} vendido a {self.lead.nombre}"

class Evento(models.Model):
    ESTATUS_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]
    TIPO_CHOICES = [
        ('EXPO', 'Expo / Congreso'),
        ('TALLER', 'Taller / Capacitación')
    ]
    LINEA_CHOICES = [
        ('SPORT', 'Línea Sport'),
        ('PET', 'Línea Pet'),
        ('DENTAL', 'Línea Dental'),
        ('PODOLOGICO', 'Línea Podológica'),
        ('BEAUTY', 'Línea Beauty'),
        ('TODAS', 'Todas las Líneas')
    ]
    
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='EXPO')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    lugar = models.CharField(max_length=255)
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='ACTIVO')
    
    linea_producto = models.CharField(max_length=20, choices=LINEA_CHOICES, default='TODAS')
    estados_objetivo = models.JSONField(default=list, help_text="Lista de nombres de estados")
    
    vendedores_asignados = models.ManyToManyField(User, related_name='eventos_asignados', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Evento / Campaña'
        verbose_name_plural = 'Eventos y Campañas'

    def __str__(self):
        return f"{self.nombre} ({self.estatus})"
