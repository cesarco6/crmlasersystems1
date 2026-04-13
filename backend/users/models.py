# users/models.py
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """Extended user profile extending Django's auth User model.
    
    Implements the RBAC (Role-Based Access Control) properties, contact details,
    and business logic specific attributes like identity color and sales goals.

    Attributes:
        user (OneToOneField): Link to Django's native User model.
        rol (CharField): Enum value establishing access scope (e.g., SELLER, DIRECTOR, ADMIN).
        telefono (CharField): Contact phone number.
        color_identidad (CharField): Hex color code for calendar/UI distinguishability.
        meta_clientes_mensual (IntegerField): Monthly target for converted leads (quantity, not currency).
        is_active (BooleanField): Soft delete flag.
    """
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
    """Catalog for professional titles and courtesies.
    
    Normalizes the lead titles before ingestion to avoid unstructured data (e.g., Dr., Dra.).

    Attributes:
        nombre (CharField): Full name of the title.
        abreviatura (CharField): Shorthand representation.
        is_active (BooleanField): Soft delete toggle.
    """
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
    """Geographical catalog for leads and territories.
    
    Stores standardized locations to calculate spatial assignments for sales agents.

    Attributes:
        ciudad (CharField): Name of the city.
        estado (CharField): Name of the state.
        is_active (BooleanField): Soft delete toggle.
    """
    ciudad = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.ciudad}, {self.estado}"

class CatEspecialidad(models.Model):
    """Catalog for medical specialties.
    
    Operates closely with the ingestion adapter to normalize incoming heterogeneous Excel
    data into standardized taxonomy representations using the 'alias' field.

    Attributes:
        nombre (CharField): Standardized name of the specialty.
        alias (TextField): Comma-separated list of synonyms for automated ingestion mapping.
        is_active (BooleanField): Soft delete toggle.
    """
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
    """Catalog representing the business products and services.
    
    Differentiates between Core Business items (equipment) and Cross-selling items
    (accessories/services). Acts as the foundation for the FSM lifecycle transitions.

    Attributes:
        nombre (CharField): Commercial designation of the product.
        familia (CharField): Macro-category definition (e.g., EQUIPO, ACCESORIO).
        alias (TextField): Mapping synonyms for mass CSV ingestions.
        is_active (BooleanField): Soft delete toggle.
    """
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
    """M2M relational model mapping users to geographical locations.
    
    Attributes:
        user_profile (ForeignKey): Linked agent profile.
        ubicacion (ForeignKey): Assigned geographical area.
        fecha_asignacion (DateTimeField): Timestamp of the territory assignment.
    """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    ubicacion = models.ForeignKey(CatUbicacion, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

class SalesGoal(models.Model):
    """Defines temporal performance goals for agents.
    
    Attributes:
        user (ForeignKey): Link to the agent's account.
        periodo_inicio (DateField): Target period start date.
        periodo_fin (DateField): Target period end date.
        cantidad_objetivo (IntegerField): Total converted leads expected in the period.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historial_metas')
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    cantidad_objetivo = models.IntegerField()