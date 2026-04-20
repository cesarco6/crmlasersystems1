import os
from django.shortcuts import render
from django.conf import settings

class MaintenanceModeMiddleware:
    """
    Middleware que detiene el flujo de la aplicación web y devuelve una pantalla
    de mantenimiento 503 si encuentra un archivo 'mantenimiento.flag' en 
    el directorio raíz del proyecto (BASE_DIR).
    Excluye la ruta /admin/ para permitir la gestión interna.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Lista Blanca: Siempre permitimos acceso al admin y archivos estáticos
        if request.path.startswith('/admin/') or request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL):
            return self.get_response(request)

        # 2. Definición del Archivo Bandera
        flag_path = os.path.join(settings.BASE_DIR, 'mantenimiento.flag')
        
        # 3. Intercepción si el archivo existe
        if os.path.exists(flag_path):
            # Valor por defecto
            msg = "Ingeniería trabajando en la plataforma. Pronto estaremos en línea."
            
            # Intenta leer el texto dentro del archivo bandera
            try:
                with open(flag_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        # Limitar a unos cuantos caracteres por si el usuario metió mucho texto
                        msg = content[:200]
            except Exception:
                pass # Si no se puede leer, usamos el msg por defecto
            
            # Retornamos el render con status HTTP 503 (Servicio no disponible)
            response = render(request, 'maintenance.html', {'maintenance_message': msg})
            response.status_code = 503
            return response

        return self.get_response(request)
