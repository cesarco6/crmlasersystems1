# leads/management/commands/generar_alertas.py
"""
Motor de Alertas Post-Venta — Django Management Command

Ejecutar diariamente (crontab / django-q):
    python manage.py generar_alertas

5 reglas de negocio evaluadas:
    1. reactivacion  — Lead activo con next_action_date <= hoy
    2. estancamiento — Lead activo sin movimiento en > 7 días
    3. capacitacion  — Cliente sin capacitación a los 8 días del tracking
    4. calidad       — Cliente sin llamada de calidad a los 180 días
    5. mantenimiento — Cliente sin servicio en los últimos 18 meses (540 días)
"""
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Evalúa reglas de negocio y genera alertas (Notificacion) para vendedores."

    def handle(self, *args, **options):
        from leads.models import CoreLead, Notificacion, TrackingPostVenta, VentaTransaccional

        hoy = now().date()
        creadas = 0
        omitidas = 0

        # ─────────────────────────────────────────────────────────────
        # Utilidad: crear alerta solo si no existe una viva del mismo tipo
        # ─────────────────────────────────────────────────────────────
        def crear_si_no_existe(lead, tipo, mensaje):
            nonlocal creadas, omitidas
            ya_existe = Notificacion.objects.filter(
                lead=lead,
                tipo=tipo,
                leida=False
            ).exists()
            if ya_existe:
                omitidas += 1
                return
            Notificacion.objects.create(
                usuario=lead.owner,
                lead=lead,
                tipo=tipo,
                mensaje=mensaje
            )
            creadas += 1

        # ─────────────────────────────────────────────────────────────
        # Leads activos (no terminales) — base para reglas 1 y 2
        # ─────────────────────────────────────────────────────────────
        ESTATUS_ACTIVOS = ['PROSPECTO', 'CONTACTADO', 'EN_DEMO', 'EN_PROPUESTA', 'EN_ESPERA']
        leads_activos = CoreLead.objects.filter(estatus__in=ESTATUS_ACTIVOS).select_related('owner')

        # ─────────────────────────────────────────────────────────────
        # REGLA 1: Agenda diaria — next_action_date vencida
        # ─────────────────────────────────────────────────────────────
        leads_vencidos = leads_activos.filter(next_action_date__lte=hoy)
        for lead in leads_vencidos:
            crear_si_no_existe(
                lead=lead,
                tipo='reactivacion',
                mensaje=f"📅 La agenda de {lead.nombre} venció el {lead.next_action_date}. ¡Contacta hoy!"
            )

        self.stdout.write(f"  Regla 1 (reactivacion): evaluadas {leads_vencidos.count()} leads")

        # ─────────────────────────────────────────────────────────────
        # REGLA 2: Telarañas — sin movimiento > 7 días
        # ─────────────────────────────────────────────────────────────
        umbral_7d = now() - timedelta(days=7)
        leads_estancados = leads_activos.filter(updated_at__lt=umbral_7d)
        for lead in leads_estancados:
            dias = (now() - lead.updated_at).days
            crear_si_no_existe(
                lead=lead,
                tipo='estancamiento',
                mensaje=f"🕸️ {lead.nombre} lleva {dias} días sin movimiento. ¡Reactívalo!"
            )

        self.stdout.write(f"  Regla 2 (estancamiento): evaluadas {leads_estancados.count()} leads")

        # ─────────────────────────────────────────────────────────────
        # REGLA 3: Capacitación — 8 días sin marcar
        # ─────────────────────────────────────────────────────────────
        umbral_8d = now() - timedelta(days=8)
        trackings_sin_cap = TrackingPostVenta.objects.filter(
            capacitacion_dada=False,
            created_at__lte=umbral_8d
        ).select_related('lead', 'lead__owner')

        for tracking in trackings_sin_cap:
            lead = tracking.lead
            dias = (now() - tracking.created_at).days
            crear_si_no_existe(
                lead=lead,
                tipo='capacitacion',
                mensaje=f"🎓 {lead.nombre} lleva {dias} días como cliente sin recibir capacitación. ¡Agéndala!"
            )

        self.stdout.write(f"  Regla 3 (capacitacion): evaluados {trackings_sin_cap.count()} trackings")

        # ─────────────────────────────────────────────────────────────
        # REGLA 4: Llamada de Calidad — 180 días sin marcar
        # ─────────────────────────────────────────────────────────────
        umbral_180d = now() - timedelta(days=180)
        trackings_sin_calidad = TrackingPostVenta.objects.filter(
            calidad_hecha=False,
            created_at__lte=umbral_180d
        ).select_related('lead', 'lead__owner')

        for tracking in trackings_sin_calidad:
            lead = tracking.lead
            dias = (now() - tracking.created_at).days
            crear_si_no_existe(
                lead=lead,
                tipo='calidad',
                mensaje=f"📞 {lead.nombre}: han pasado {dias} días. ¡Es momento de la llamada de calidad!"
            )

        self.stdout.write(f"  Regla 4 (calidad): evaluados {trackings_sin_calidad.count()} trackings")

        # ─────────────────────────────────────────────────────────────
        # REGLA 5: Reloj Flotante — Mantenimiento 18 meses (540 días)
        # ─────────────────────────────────────────────────────────────
        umbral_540d = now() - timedelta(days=540)

        clientes = CoreLead.objects.filter(estatus='CLIENTE').select_related('owner')

        for lead in clientes:
            # a) Buscar la última VentaTransaccional de familia SERVICIO
            ultima_venta_servicio = VentaTransaccional.objects.filter(
                lead=lead,
                producto__familia='SERVICIO'
            ).order_by('-fecha_venta').first()

            # b) Determinar punto de inicio del reloj
            if ultima_venta_servicio:
                punto_inicio = ultima_venta_servicio.fecha_venta
            else:
                # Si nunca hubo un servicio, usamos el tracking o el lead como fallback
                try:
                    punto_inicio = lead.tracking_postventa.created_at
                except TrackingPostVenta.DoesNotExist:
                    punto_inicio = lead.created_at

            # c) Evaluar si pasaron >= 540 días
            if punto_inicio <= umbral_540d:
                dias = (now() - punto_inicio).days
                crear_si_no_existe(
                    lead=lead,
                    tipo='mantenimiento',
                    mensaje=f"🔧 {lead.nombre}: Han pasado {dias} días desde el último servicio. ¡Es momento del mantenimiento!"
                )

        self.stdout.write(f"  Regla 5 (mantenimiento): evaluados {clientes.count()} clientes")

        # ─────────────────────────────────────────────────────────────
        # Resumen final
        # ─────────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Motor de Alertas completado: {creadas} alertas creadas, {omitidas} omitidas (ya existían)."
        ))
