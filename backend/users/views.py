from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from users.models import CatUbicacion, UserProfile, AsignacionTerritorio
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

User = get_user_model()

def es_director(user):
    return user.is_superuser


@login_required
@user_passes_test(es_director, login_url='dashboard_agente')
def panel_territorios(request):
    # Obtener a los vendedores (excluimos al superusuario/director para la lista de asignación)
    vendedores = User.objects.filter(is_superuser=False).order_by('username')
    
    # Obtener los 32 estados únicos ordenados alfabéticamente
    estados_unicos = CatUbicacion.objects.values_list('estado', flat=True).distinct().order_by('estado')
    
    context = {
        'vendedores': vendedores,
        'estados': estados_unicos,
    }
    return render(request, 'director_territorios.html', context)

def custom_login_view(request):
    # Si el usuario ya está logueado, lo pateamos a su dashboard correspondiente
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('director_dashboard') # Redirección dinámica por rol
        else:
            return redirect('dashboard_agente') # Ajusta al nombre de tu ruta del vendedor

    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave = request.POST.get('password')
        
        user = authenticate(request, username=usuario, password=clave)
        
        if user is not None:
            login(request, user)
            # El Switch de Tráfico
            if user.is_superuser:
                return redirect('director_dashboard')
            else:
                return redirect('dashboard_agente') # Ajusta al nombre de tu URL de vendedor
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'login.html')

def custom_logout_view(request):
    logout(request)
    return redirect('login')

@login_required
@user_passes_test(es_director)
@require_http_methods(["GET", "POST"])
def api_territorios_vendedor(request, vendedor_id):
    try:
        vendedor = User.objects.get(id=vendedor_id)
        # Obtenemos el perfil o lo creamos si no existe por alguna razón
        perfil, created = UserProfile.objects.get_or_create(user=vendedor)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Vendedor no encontrado o error al obtener perfil'}, status=404)

    if request.method == 'GET':
        estados_asignados = list(AsignacionTerritorio.objects.filter(user_profile=perfil).values_list('ubicacion__estado', flat=True).distinct())
        return JsonResponse({'status': 'success', 'estados': estados_asignados})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            estados_seleccionados = data.get('estados', [])
            
            # Obtener todas las ubicaciones correspondientes a los estados
            ubicaciones_nuevas = CatUbicacion.objects.filter(estado__in=estados_seleccionados)
            
            # Borrar las asignaciones viejas de este perfil
            AsignacionTerritorio.objects.filter(user_profile=perfil).delete()
            
            # Crear las nuevas
            nuevas_asignaciones = [AsignacionTerritorio(user_profile=perfil, ubicacion=ubi) for ubi in ubicaciones_nuevas]
            AsignacionTerritorio.objects.bulk_create(nuevas_asignaciones)
            
            return JsonResponse({'status': 'success', 'message': 'Territorios actualizados correctamente.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_set_global_font(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Solo el administrador puede cambiar la fuente'}, status=403)
    
    try:
        from django.conf import settings
        import os
        
        data = json.loads(request.body)
        font = data.get('font')
        if font in ['ubuntu', 'inter', 'roboto', 'outfit']:
            settings_file = os.path.join(settings.BASE_DIR, 'global_settings.json')
            settings_data = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        settings_data = json.load(f)
                except Exception:
                    pass
            settings_data['crm_font'] = font
            with open(settings_file, 'w') as f:
                json.dump(settings_data, f)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'error': 'Fuente no válida'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
