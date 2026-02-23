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

# 1. Agregamos "procesar_alta_manual" a la lista de importaciones
from leads.views import DashboardAgenteView, IngestaMasivaView, procesar_ingesta_masiva, AltaIndividualView, FichaTrabajoView, procesar_alta_manual

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/agente/', DashboardAgenteView.as_view(), name='dashboard_agente'),
    path('ingesta-masiva/', IngestaMasivaView.as_view(), name='ingesta_masiva'),
    path('api/ingesta/', procesar_ingesta_masiva, name='api_ingesta_masiva'),
    
    # 2. La nueva ruta que escuchará a nuestro Modal
    path('api/alta-manual/', procesar_alta_manual, name='api_alta_manual'),
    
    path('alta/', AltaIndividualView.as_view(), name='alta_individual'),
    path('trabajo/<uuid:pk>/', FichaTrabajoView.as_view(), name='ficha_trabajo'),
    path('', RedirectView.as_view(pattern_name='dashboard_agente'), name='root'),
]