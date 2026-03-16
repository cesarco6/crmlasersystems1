from leads.models import CatEspecialidad, CatProducto
from django.db.models import Q
from leads.mdm_services import normalizar_texto

def obtener_catalogos_limpios(texto_especialidad, texto_producto):
    """
    Recibe los textos crudos del Excel o Formulario y los cruza inteligentemente
    contra las tablas catálogo.
    """
    
    # 1. Procesar Producto (Dinámico y Estético)
    texto_prod_limpio = str(texto_producto).strip()
    if not texto_prod_limpio or texto_prod_limpio.upper() == 'NAN':
        texto_prod_limpio = "Por Definir / Otro"
        
    # Buscamos primero coincidencia exacta
    producto_obj = CatProducto.objects.filter(nombre__iexact=texto_prod_limpio).first()
    
    # Si no coincidencia exacta, intentamos búsqueda por Alias Inteligente
    if not producto_obj:
        texto_prod_norm = normalizar_texto(texto_prod_limpio)
        producto_obj = CatProducto.objects.filter(
            Q(nombre__iexact=texto_producto) | 
            Q(alias__icontains=texto_prod_norm)
        ).first()
        
        # Si no lo encuentra, asignamos el "Por Definir"
        if not producto_obj:
            producto_obj, _ = CatProducto.objects.get_or_create(nombre='Por Definir / Otro')

    # 2. Procesar Especialidad (Dinámico y Estético)
    texto_esp_limpio = str(texto_especialidad).strip()
    if not texto_esp_limpio:
        texto_esp_limpio = "General"
        
    # Buscamos si ya existe ignorando mayúsculas/minúsculas
    especialidad_obj = CatEspecialidad.objects.filter(nombre__iexact=texto_esp_limpio).first()
    
    # Si no existe, lo creamos respetando su formato bonito original
    if not especialidad_obj:
        especialidad_obj = CatEspecialidad.objects.create(nombre=texto_esp_limpio)

    return especialidad_obj, producto_obj
