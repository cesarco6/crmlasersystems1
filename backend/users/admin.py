# users/admin.py
from django.contrib import admin
from .models import UserProfile, CatUbicacion, CatLada

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rol')
    list_filter = ('rol',)
    search_fields = ('user__username',)

@admin.register(CatUbicacion)
class CatUbicacionAdmin(admin.ModelAdmin):
    # Columnas que verá el Admin en la lista
    list_display = ('ciudad', 'estado')
    
    # Barra de búsqueda (puede buscar por ciudad o estado)
    search_fields = ('ciudad', 'estado')
    
    # Filtro lateral derecho (para filtrar rápido por estado)
    list_filter = ('estado',)
    
    # Orden alfabético por defecto
    ordering = ('estado', 'ciudad')

@admin.register(CatLada)
class CatLadaAdmin(admin.ModelAdmin):
    list_display = ('clave', 'ciudad_referencia', 'estado_referencia', 'get_enlace', 'is_active')
    search_fields = ('clave', 'ciudad_referencia', 'estado_referencia')
    list_filter = ('estado_referencia', 'is_active')
    ordering = ('clave',)
    
    def get_enlace(self, obj):
        return "Conectado" if obj.ubicacion_oficial else "-"
    get_enlace.short_description = 'Ubicación CRM'

