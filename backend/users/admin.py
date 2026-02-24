# users/admin.py
from django.contrib import admin
from .models import UserProfile, CatUbicacion

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
