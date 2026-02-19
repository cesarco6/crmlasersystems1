from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from users.permissions import role_required
from .mixins import LeadOwnershipMixin

@method_decorator(role_required(['VENDEDOR']), name='dispatch')
class DashboardAgenteView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'dashboard_agente.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any necessary context data here
        # For now, the template is static, but we can add dynamic data later
        return context

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaMasivaView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'ingesta_masiva.html'

