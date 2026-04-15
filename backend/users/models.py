# users/models.py
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    rol = models.CharField(max_length=20, choices=[
        ('VENDEDOR', 'Vendedor'),
        ('DIRECTOR', 'Director'),
        ('ADMIN', 'Administrador')
    ], default='VENDEDOR')
    telefono = models.CharField(max_length=15, blank=True)
    color_identidad = models.CharField(max_length=7, default='#3498db')
    meta_clientes_mensual = models.IntegerField(default=0) # Cantidad, no dinero
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.rol})"

class CatTitulo(models.Model):
    nombre = models.CharField(max_length=50, unique=True, help_text="Ej: Dr., Dra., M.V.Z.")
    abreviatura = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Título de Cortesía'
        verbose_name_plural = 'Catálogo de Títulos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class CatUbicacion(models.Model):
    ciudad = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.ciudad}, {self.estado}"

class CatLada(models.Model):
    clave = models.CharField(max_length=3, unique=True, help_text="Clave Lada de 2 o 3 dígitos (Ej. '55')")
    estado_referencia = models.CharField(max_length=100, help_text="Nombre del Estado")
    ciudad_referencia = models.CharField(max_length=100, help_text="Nombre de la Ciudad o Municipio base")
    ubicacion_oficial = models.ForeignKey(
        CatUbicacion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='ladas_asociadas',
        help_text="Enlace al catálogo oficial. Déjalo en blanco si no se vende ahí."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Diccionario LADA'
        verbose_name_plural = 'Diccionario Nacional de LADAS'
        ordering = ['clave']

    def __str__(self):
        estatus = "🔗 Enlazado" if self.ubicacion_oficial else "❌ Sin enlace"
        return f"[{self.clave}] {self.ciudad_referencia}, {self.estado_referencia} ({estatus})"


class CatEspecialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    # El campo alias nos salvará la vida en las ingestas masivas
    alias = models.TextField(blank=True, null=True, help_text="Sinónimos separados por coma. Ej: vet, veterinaria, animales")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Especialidad'
        verbose_name_plural = 'Catálogo de Especialidades'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class CatProducto(models.Model):
    FAMILIA_CHOICES = [
        ('EQUIPO', 'Equipo Principal (Core Business)'),
        ('ACCESORIO', 'Accesorio / Consumible (Cross-selling)'),
        ('SERVICIO', 'Servicio Técnico / Mantenimiento'),
        ('EVENTO', 'Evento / Capacitación'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    familia = models.CharField(
        max_length=20, 
        choices=FAMILIA_CHOICES, 
        default='EQUIPO',
        help_text="Permite separar el modelo de negocio principal (FSM) de las ventas complementarias."
    )
    alias = models.TextField(blank=True, null=True, help_text="Sinónimos separados por coma. Ej: laser mini sport, laser ir sport")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Catálogo de Productos'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_familia_display()})"


class AsignacionTerritorio(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    ubicacion = models.ForeignKey(CatUbicacion, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

class SalesGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historial_metas')
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    cantidad_objetivo = models.IntegerField()