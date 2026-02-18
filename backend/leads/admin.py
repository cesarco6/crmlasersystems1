from django.contrib import admin
from .models import CoreLead, LeadDispute, FiscalProfile

@admin.register(CoreLead)
class CoreLeadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'phone_primary', 'estatus', 'owner')
    search_fields = ('nombre', 'phone_primary')
    readonly_fields = ('id', 'notas_variadas') # El JSONB se ve pero se protege de edición manual rápida

@admin.register(LeadDispute)
class LeadDisputeAdmin(admin.ModelAdmin):
    list_display = ('lead', 'claimant_user', 'status', 'created_at')
    list_filter = ('status', 'tipo_conflicto')