from django.utils import timezone
from datetime import timedelta
from .models import Lead

def rutina_diaria_alertas():
    """
    Se ejecuta todos los días a las 01:00 AM.
    Solo lee y avisa, no fuerza cambios de estado.
    """
    hoy = timezone.now().date()
    limite_30_dias = hoy - timedelta(days=30)
    
    # Regla 1/10: Alerta si Lead > 30 días y sigue como 'Nuevo' o 'Contacto'
    leads_estancados = Lead.objects.filter(
        estado__in=['nuevo', 'contacto'],
        fecha_creacion__date__lte=limite_30_dias
    )
    
    for lead in leads_estancados:
        # Aquí crearemos la notificación (Badge) para el vendedor
        # Ejemplo: "El lead {lead.nombre} lleva 30 días sin avance. Por favor, actualiza sus notas o cambia su estado."
        print(f"ALERTA CREADA PARA: {lead.nombre} - 30 días sin cierre")

    # Regla de Reactivación: Leads 'En Espera' que llegan a su fecha
    leads_a_despertar = Lead.objects.filter(
        estado='espera',
        fecha_reactivacion__date=hoy
    )
    
    for lead in leads_a_despertar:
        # Alerta: "Es hora de contactar de nuevo a {lead.nombre}"
        print(f"DESPERTAR A: {lead.nombre}")
        
    return "Rutina de alertas ejecutada con éxito"