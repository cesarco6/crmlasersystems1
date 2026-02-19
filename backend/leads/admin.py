from django.contrib import admin
from .models import CoreLead, FiscalProfile

@admin.register(CoreLead)
class CoreLeadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'phone_primary', 'estatus', 'owner')
    search_fields = ('nombre', 'phone_primary')
    readonly_fields = ('id', 'notas_variadas') # El JSONB se ve pero se protege de edición manual rápida

