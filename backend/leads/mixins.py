# backend/leads/mixins.py
from .models import CoreLead

class LeadOwnershipMixin:
    """
    Garantiza que el usuario solo acceda a sus propios leads.
    Si es DIRECTOR o ADMIN, puede ver todos.
    """
    def get_queryset(self):
        user = self.request.user
        if user.profile.rol in ['DIRECTOR', 'ADMIN']:
            return CoreLead.objects.all()
        return CoreLead.objects.filter(owner=user)