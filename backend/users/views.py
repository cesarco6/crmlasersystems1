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
    """Verifies if the user holds director privileges.

    Args:
        user (User): The user instance requesting access.

    Returns:
        bool: True if the user is a superuser, False otherwise.
    """
    return user.is_superuser


@login_required
@user_passes_test(es_director, login_url='dashboard_agente')
def panel_territorios(request):
    """Renders the territory assignment interface for directors.

    Fetches all sellers and available states (locations) to allow the director
    to bulk assign geographical territories to specific agents.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponse: Rendered 'director_territorios.html' template containing 
        the context with 'vendedores' and 'estados'.
    """
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
    """Handles user authentication and role-based redirect routing.

    Intercepts login attempts, evaluates user credentials, and implements the 
    traffic switch (traffic-director) to send Directors to the panoramic dashboard 
    and Sellers to their local operations dashboard.

    Args:
        request (HttpRequest): The incoming HTTP request containing POST payload.

    Returns:
        HttpResponseRedirect|HttpResponse: Redirects on successful login or renders 
        'login.html' on failure/GET.
    """
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
    """Terminates the user session and redirects to the login view.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponseRedirect: Redirect to the 'login' route.
    """
    logout(request)
    return redirect('login')

@login_required
@user_passes_test(es_director)
@require_http_methods(["GET", "POST"])
def api_territorios_vendedor(request, vendedor_id):
    """API endpoint to read or update territory assignments for a specific seller.

    - GET: Retrieves a list of states currently assigned to the seller.
    - POST: Receives a JSON payload mapping new states, removing old assignments 
      and bulk-creating the new territory boundaries.

    Args:
        request (HttpRequest): The incoming HTTP request.
        vendedor_id (int): The primary key of the User/Seller being queried/modified.

    Returns:
        JsonResponse: A JSON dictionary with the operation 'status' and payload/messages.
    """
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
