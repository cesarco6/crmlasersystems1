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
from leads.views import DashboardAgenteView, IngestaMasivaView, procesar_ingesta_masiva, AltaIndividualView, FichaTrabajoView, procesar_alta_manual, actualizar_lead_fsm, IngestaHistoricaView, director_dashboard_view, registrar_venta_extra, ListaStagingView, ProcesarStagingView, IngestaHistoricaExpressView, actualizar_estatus_venta_extra
from users.views import panel_territorios, custom_login_view, custom_logout_view, api_territorios_vendedor

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', custom_login_view, name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/agente/', DashboardAgenteView.as_view(), name='dashboard_agente'),
    path('ingesta-masiva/', IngestaMasivaView.as_view(), name='ingesta_masiva'),
    path('api/ingesta/', procesar_ingesta_masiva, name='api_ingesta_masiva'),
    path('director/ingesta-historica/', IngestaHistoricaView.as_view(), name='director_ingesta'),
    path('director/dashboard/', director_dashboard_view, name='director_dashboard'),
    path('director/territorios/', panel_territorios, name='director_territorios'),
    path('api/director/territorios/<int:vendedor_id>/', api_territorios_vendedor, name='api_territorios_vendedor'),

    # Quirófano (Staging)
    path('director/staging/', ListaStagingView.as_view(), name='staging_list'),
    path('director/staging/<uuid:pk>/procesar/', ProcesarStagingView.as_view(), name='staging_procesar'),
    path('director/ingesta-express/', IngestaHistoricaExpressView.as_view(), name='ingesta_express'),

    # Buscador Global Omnipotente - Director
    path('director/buscar/', leads_views.director_busqueda_view, name='director_busqueda'),
    path('director/directorio/', leads_views.director_directorio_view, name='director_directorio'),
    
    # Eventos y Campañas - Director
    path('director/eventos/', leads_views.director_eventos_view, name='director_eventos'),
    path('api/eventos/crear/', leads_views.api_crear_evento, name='api_crear_evento'),
    
    # Vistas de Dirección - Bandeja de Rescate
    path('director/rescate/', leads_views.bandeja_rescate_view, name='director_rescate'),
    path('director/fidelizacion/', leads_views.dashboard_fidelizacion_view, name='director_fidelizacion'),
    path('api/reasignar-lead/', leads_views.api_reasignar_lead, name='api_reasignar_lead'),
    path('api/desechar-lead/', leads_views.api_desechar_lead, name='api_desechar_lead'),
    
    # 2. La nueva ruta que escuchará a nuestro Modal
    path('api/alta-manual/', procesar_alta_manual, name='api_alta_manual'),
    path('api/venta-extra/', registrar_venta_extra, name='registrar_venta_extra'),
    path('api/venta-extra/<int:venta_id>/actualizar/', actualizar_estatus_venta_extra, name='api_actualizar_venta_extra'),
    
    path('alta/', AltaIndividualView.as_view(), name='alta_individual'),
    path('trabajo/<uuid:pk>/', FichaTrabajoView.as_view(), name='ficha_trabajo'),
    path('api/lead/<uuid:pk>/actualizar/', actualizar_lead_fsm, name='api_actualizar_lead'),
    path('', RedirectView.as_view(pattern_name='dashboard_agente'), name='root'),

    path('api/lead/<uuid:pk>/no-cierre/', leads_views.api_marcar_no_cierre, name='api_no_cierre'),


]