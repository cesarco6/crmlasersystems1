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

class CatUbicacion(models.Model):
    ciudad = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.ciudad}, {self.estado}"

class AsignacionTerritorio(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    ubicacion = models.ForeignKey(CatUbicacion, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

class SalesGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historial_metas')
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    cantidad_objetivo = models.IntegerField()