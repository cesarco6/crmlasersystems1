import re
import unicodedata
from leads.models import CatTitulo, Clinica

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def normalizar_telefono(telefono):
    if not telefono:
        return ""
    digitos = re.sub(r'\D', '', str(telefono))
    return digitos[:15]

def get_fila_val(fila_data, posibles_claves):
    """Helper para buscar valores independientemente de si pandas extrajo la columna con acentos o no"""
    for k, v in fila_data.items():
        if k in posibles_claves:
            return str(v).strip()
    return ""

def extraer_titulo_cortesia(nombre_raw, dry_run=False):
    """Extrae títulos como Dr., Dra., MVZ y devuelve el id de CatTitulo y el nombre sobrante."""
    if not nombre_raw:
        return None, ""
    
    # Expresión regular para detectar títulos al inicio
    # Partículas comunes: Dr, Dra, MVZ, Lic, Ing, Prof, Profa, LTF, Odont
    patron = r'^\s*(dr\.?|dra\.?|m\.?v\.?z\.?|lic\.?|ing\.?|prof\.?|profa\.?|ltf\.?|odont\.?)\s+'
    match = re.search(patron, nombre_raw, flags=re.IGNORECASE)
    
    titulo_id = None
    nombre_limpio = nombre_raw
    
    if match:
        particula_encontrada = match.group(1).replace('.', '').strip().title()
        # Eliminar el título del nombre
        nombre_limpio = re.sub(patron, '', nombre_raw, flags=re.IGNORECASE).strip()
        
        if not dry_run:
            t, _ = CatTitulo.objects.get_or_create(
                nombre__iexact=particula_encontrada,
                defaults={'nombre': particula_encontrada + '.', 'abreviatura': particula_encontrada.upper()}
            )
            titulo_id = t.id
        else:
            t = CatTitulo.objects.filter(nombre__iexact=particula_encontrada).first()
            titulo_id = t.id if t else None
                
    return titulo_id, nombre_limpio

def clasificar_entidad(nombre_raw):
    """
    Clasifica como:
    - 'CORPORATIVO': Clínica, Hospital, etc.
    - 'MULTIPLE': Incluye conectores (y, &, /)
    - 'INDIVIDUAL': Persona única
    """
    if not nombre_raw:
        return 'INDIVIDUAL'
        
    nombre_norm = normalizar_texto(nombre_raw)
    
    # 1. Corporativo
    palabras_corporativas = [
        r'\bclinica\b', r'\bhospital\b', r'\bgrupo\b', r'\basociacion\b', 
        r'\bcentro\b', r'\binstituto\b', r'\bvet\b', r'\bveterinaria\b', r'\bspa\b'
    ]
    if any(re.search(p, nombre_norm) for p in palabras_corporativas):
        return 'CORPORATIVO'
        
    # 2. Múltiple / Siameses
    conectores = [r'\by\b', r'\b&\b', r'\/', r'\be\b']
    if any(re.search(c, nombre_norm) for c in conectores):
        return 'MULTIPLE'
        
    return 'INDIVIDUAL'

def atomizar_identidad(nombre_limpio):
    """
    Toma un nombre sin títulos y lo separa en Pila, Paterno, Materno
    respetando partículas de apellidos (De, La, Del, San, Mac, etc.)
    """
    if not nombre_limpio:
        return "", "", ""
        
    particulas_compuestas = {
        'de', 'la', 'del', 'los', 'las', 'san', 'santa', 'von', 'van', 'mac', 'mc', 'dos', 'da', 'di'
    }
    
    tokens = nombre_limpio.split()
    tokens_agrupados = []
    
    i = 0
    while i < len(tokens):
        token_actual = tokens[i]
        token_norm = normalizar_texto(token_actual)
        
        if token_norm in particulas_compuestas and i + 1 < len(tokens):
            # Es una partícula, intentamos agruparla con la siguiente palabra
            grupo = [token_actual]
            while i + 1 < len(tokens) and normalizar_texto(tokens[i + 1]) in particulas_compuestas:
                i += 1
                grupo.append(tokens[i])
            if i + 1 < len(tokens):
                i += 1
                grupo.append(tokens[i])
            tokens_agrupados.append(" ".join(grupo))
        else:
            tokens_agrupados.append(token_actual)
        i += 1

    nombre_pila = ""
    apellido_paterno = ""
    apellido_materno = ""
    
    # Heurística simple de asignación
    if len(tokens_agrupados) == 1:
        nombre_pila = tokens_agrupados[0]
    elif len(tokens_agrupados) == 2:
        nombre_pila = tokens_agrupados[0]
        apellido_paterno = tokens_agrupados[1]
    elif len(tokens_agrupados) >= 3:
        # Asumimos que los dos últimos son paterno y materno
        apellido_materno = tokens_agrupados[-1]
        apellido_paterno = tokens_agrupados[-2]
        nombre_pila = " ".join(tokens_agrupados[:-2])
        
    return nombre_pila[:100], apellido_paterno[:100], apellido_materno[:100]

def parsear_fila(fila_data, dry_run=False):
    """Orquestador del pipeline ETL adaptado a Fase 2"""
    # 1. Teléfonos (Limpieza Regex y Prioridad Celular > Teléfono)
    val_celular = get_fila_val(fila_data, ['celular'])
    val_telefono = get_fila_val(fila_data, ['teléfono', 'telefono'])
    
    celular_limpio = re.sub(r'\D', '', val_celular)[:15]
    telefono_limpio = re.sub(r'\D', '', val_telefono)[:15]
    
    phone_primary = celular_limpio if celular_limpio else telefono_limpio
    
    # 2. Email (Limpiar espacios y minúsculas)
    email_raw = get_fila_val(fila_data, ['email', 'correo'])
    email_limpio = email_raw.replace(' ', '').lower()
    
    nombre_raw = get_fila_val(fila_data, ['nombre', 'nombre_completo'])
    
    # 3. Catálogos Raw
    especialidad_raw = get_fila_val(fila_data, ['especialidad'])
    ubicacion_raw = get_fila_val(fila_data, ['ubicación', 'ubicacion'])
    titulo_raw = get_fila_val(fila_data, ['titulo', 'título'])
    
    # 1. Clasificar Entidad
    tipo_entidad = clasificar_entidad(nombre_raw)
    
    res = {
        "tipo_entidad": tipo_entidad,
        "telefono_norm": phone_primary,
        "celular_norm": celular_limpio,
        "nombre_original": nombre_raw,
        "email_norm": email_limpio,
        "especialidad_raw": especialidad_raw,
        "ubicacion_raw": ubicacion_raw,
    }
    
    if tipo_entidad == 'CORPORATIVO':
        res['nombre_clinica'] = nombre_raw
    elif tipo_entidad == 'MULTIPLE':
        pass # Se enviará a revisión manual
    else:
        # Individuo
        titulo_id = None
        nombre_sin_titulo = nombre_raw
        
        if titulo_raw:
            particula_encontrada = titulo_raw.strip().title()
            if not particula_encontrada.endswith('.'):
                particula_encontrada += '.'
                
            if not dry_run:
                t, _ = CatTitulo.objects.get_or_create(
                    nombre__iexact=particula_encontrada,
                    defaults={'nombre': particula_encontrada, 'abreviatura': titulo_raw.strip().upper()}
                )
                titulo_id = t.id
            else:
                t = CatTitulo.objects.filter(nombre__iexact=particula_encontrada).first()
                titulo_id = t.id if t else None
            
            # Eliminar prefijos repetidos por si el usuario puso "Dr." en titulo y "Dr. Juan" en nombre
            patron = r'^\s*(dr\.?|dra\.?|m\.?v\.?z\.?|lic\.?|ing\.?|prof\.?|profa\.?|ltf\.?|odont\.?)\s+'
            nombre_sin_titulo = re.sub(patron, '', nombre_raw, flags=re.IGNORECASE).strip()
        else:
            titulo_id, nombre_sin_titulo = extraer_titulo_cortesia(nombre_raw, dry_run)
            
        pila, paterno, materno = atomizar_identidad(nombre_sin_titulo)
        
        res['titulo_id'] = titulo_id
        res['nombre_pila'] = pila
        res['apellido_paterno'] = paterno
        res['apellido_materno'] = materno
        
    return res

from django.utils import timezone

def orquestar_ingesta_historica(filas_data, admin_user=None, dry_run=True):
    """
    Orquesta la ingesta de un lote de filas enviándolas a la aduana (LeadStaging).
    Respetando la nueva regla estricta: Cero Inyección en CoreLead.
    """
    from leads.models import LeadStaging

    total_filas = len(filas_data)
    reporte = {
        "total_procesados": total_filas,
        "clinicas_identificadas": 0,
        "individuos_atomizados": 0,
        "siameses_revision_manual": total_filas,
        "errores_criticos": 0,
        "detalles": []
    }

    stagings_a_crear = []

    for fila in filas_data:
        # Forzamos el dry_run=True para que el parser JAMÁS toque la base de datos
        datos_parseados = parsear_fila(fila, dry_run=True)
        
        if not dry_run:
            stagings_a_crear.append(
                LeadStaging(
                    owner=admin_user,
                    datos_crudos=fila,
                    datos_parseados=datos_parseados,
                    motivo_conflicto="Ingesta Masiva: Pendiente de auditoría manual",
                    estatus='PENDIENTE'
                )
            )

        reporte["detalles"].append({
            "tipo": "REVISION_MANUAL_MULTIPLE",
            "data": fila,
            "motivo": "Enviado a Aduana (Staging)"
        })

    # Inyección masiva optimizada (solo se ejecuta si el usuario dio "Confirmar")
    if not dry_run and stagings_a_crear:
        LeadStaging.objects.bulk_create(stagings_a_crear, batch_size=500)

    return reporte