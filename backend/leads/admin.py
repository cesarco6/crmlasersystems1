# leads/admin.py
from django.contrib import admin
from .models import CoreLead, FiscalProfile, ExcepcionEspecialidadLinea

@admin.register(CoreLead)
class CoreLeadAdmin(admin.ModelAdmin):
    # 1. En la tabla mostramos la propiedad calculada para que se vea bonito
    list_display = ('nombre_completo_mdm', 'phone_primary', 'estatus', 'owner')
    
    # 2. En el buscador tenemos que poner los campos atómicos reales
    search_fields = ('nombre_pila', 'apellido_paterno', 'apellido_materno', 'phone_primary')
    
    readonly_fields = ('id', 'notas_variadas')


@admin.register(ExcepcionEspecialidadLinea)
class ExcepcionEspecialidadLineaAdmin(admin.ModelAdmin):
    list_display = ('especialidad', 'linea_producto', 'permitido')
    list_filter = ('linea_producto', 'permitido')
    search_fields = ('especialidad__nombre',)