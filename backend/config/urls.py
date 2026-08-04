"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView
from leads import views as leads_views

# 1. Agregamos "procesar_alta_manual" a la lista de importaciones
from leads.views import DashboardAgenteView, Ventas360View, IngestaMasivaView, procesar_ingesta_masiva, AltaIndividualView, FichaTrabajoView, FichaTrabajo360View, procesar_alta_manual, actualizar_lead_fsm, IngestaHistoricaView, director_dashboard_view, registrar_venta_extra, ListaStagingView, ProcesarStagingView, IngestaHistoricaExpressView, actualizar_estatus_venta_extra, AgenteStagingListView, AgenteStagingProcesarView
from users.views import panel_territorios, custom_login_view, custom_logout_view, api_territorios_vendedor, api_set_global_font
from django.shortcuts import render

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)

def custom_403(request, exception=None):
    return render(request, '403.html', status=403)

handler404 = custom_404
handler500 = custom_500
handler403 = custom_403

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', custom_login_view, name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/agente/', DashboardAgenteView.as_view(), name='dashboard_agente'),
    path('agente/ventas-360/', Ventas360View.as_view(), name='ventas_360'),
    path('ingesta-masiva/', IngestaMasivaView.as_view(), name='ingesta_masiva'),
    path('api/ingesta/', procesar_ingesta_masiva, name='api_ingesta_masiva'),
    path('director/ingesta-historica/', IngestaHistoricaView.as_view(), name='director_ingesta'),
    path('director/dashboard/', director_dashboard_view, name='director_dashboard'),
    path('director/territorios/', panel_territorios, name='director_territorios'),
    path('api/director/territorios/<int:vendedor_id>/', api_territorios_vendedor, name='api_territorios_vendedor'),
    path('api/set-global-font/', api_set_global_font, name='api_set_global_font'),

    # Quirófano (Staging) - DIrector
    path('director/staging/', ListaStagingView.as_view(), name='staging_list'),
    path('director/staging/<uuid:pk>/procesar/', ProcesarStagingView.as_view(), name='staging_procesar'),
    path('director/ingesta-express/', IngestaHistoricaExpressView.as_view(), name='ingesta_express'),

    # Quirófano (Staging) - Agente
    path('agente/staging/', AgenteStagingListView.as_view(), name='agente_staging_list'),
    path('agente/staging/<uuid:pk>/procesar/', AgenteStagingProcesarView.as_view(), name='agente_staging_procesar'),

    # Buscador Global Omnipotente - Director
    path('director/buscar/', leads_views.director_busqueda_view, name='director_busqueda'),
    path('director/directorio/', leads_views.director_directorio_view, name='director_directorio'),
    path('director/directorio/exportar/', leads_views.director_directorio_exportar_view, name='director_directorio_exportar'),
    path('agente/exportar-leads/', leads_views.agente_exportar_leads_view, name='agente_exportar_leads'),
    path('agente/ventas-360/exportar-talleres/', leads_views.agente_exportar_talleres_view, name='agente_exportar_talleres'),
    
    # Eventos y Campañas - Director
    path('director/eventos/', leads_views.director_eventos_view, name='director_eventos'),
    path('api/eventos/crear/', leads_views.api_crear_evento, name='api_crear_evento'),
    path('api/eventos/eliminar/<int:evento_id>/', leads_views.api_eliminar_evento, name='api_eliminar_evento'),
    path('api/eventos/editar/', leads_views.api_editar_evento, name='api_editar_evento'),
    path('api/eventos/archivar/<int:evento_id>/', leads_views.api_archivar_evento, name='api_archivar_evento'),
    path('api/eventos/detalle/<int:evento_id>/', leads_views.api_detalle_evento, name='api_detalle_evento'),
    
    # Vistas de Dirección - Bandeja de Rescate
    path('director/rescate/', leads_views.bandeja_rescate_view, name='director_rescate'),
    path('director/fidelizacion/', leads_views.dashboard_fidelizacion_view, name='director_fidelizacion'),
    path('api/hito-postventa/<uuid:lead_id>/', leads_views.api_marcar_hito_postventa, name='api_marcar_hito_postventa'),
    path('api/reasignar-lead/', leads_views.api_reasignar_lead, name='api_reasignar_lead'),
    path('api/desechar-lead/', leads_views.api_desechar_lead, name='api_desechar_lead'),
    
    # 2. La nueva ruta que escuchará a nuestro Modal
    path('api/alta-manual/', procesar_alta_manual, name='api_alta_manual'),
    path('api/venta-extra/', registrar_venta_extra, name='registrar_venta_extra'),
    path('api/venta-extra/<int:venta_id>/actualizar/', actualizar_estatus_venta_extra, name='api_actualizar_venta_extra'),
    
    path('alta/', AltaIndividualView.as_view(), name='alta_individual'),
    path('trabajo/<uuid:pk>/', FichaTrabajoView.as_view(), name='ficha_trabajo'),
    path('trabajo-360/<uuid:pk>/', FichaTrabajo360View.as_view(), name='ficha_trabajo_360'),
    path('agente/expo/<int:evento_id>/', leads_views.AgenteExpoCapturaView.as_view(), name='agente_expo_captura'),
    path('api/lead/<uuid:pk>/actualizar/', actualizar_lead_fsm, name='api_actualizar_lead'),
    path('', RedirectView.as_view(pattern_name='dashboard_agente'), name='root'),

    path('api/lead/<uuid:pk>/no-cierre/', leads_views.api_marcar_no_cierre, name='api_no_cierre'),
    path('api/alerta/<int:alerta_id>/atender/', leads_views.api_atender_alerta, name='api_atender_alerta'),
    path('api/citas-dia/', leads_views.api_citas_dia, name='api_citas_dia'),
    path('agente/ventas-360/vincular-evento/', leads_views.vincular_cliente_evento_view, name='vincular_cliente_evento'),
    path('agente/ventas-360/eventos-cliente/', leads_views.obtener_eventos_cliente_view, name='eventos_cliente'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Rutas para probar las páginas de error en entorno local (DEBUG=True)
    urlpatterns += [
        path('test/404/', custom_404, name='test_404'),
        path('test/500/', custom_500, name='test_500'),
        path('test/403/', custom_403, name='test_403'),
    ]