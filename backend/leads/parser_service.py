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

def extraer_titulo_cortesia(nombre_raw):
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
        particula_encontrada = match.group(1).replace('.', '').strip().lower()
        # Eliminar el título del nombre
        nombre_limpio = re.sub(patron, '', nombre_raw, flags=re.IGNORECASE).strip()
        
        # Mapeo simple o consulta a base de datos
        titulos_db = CatTitulo.objects.all()
        for t in titulos_db:
            t_norm = normalizar_texto(t.nombre).replace('.', '')
            t_abrev = normalizar_texto(t.abreviatura).replace('.', '') if t.abreviatura else ""
            if particula_encontrada == t_norm or (t_abrev and particula_encontrada == t_abrev):
                titulo_id = t.id
                break
                
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

def parsear_fila(fila_data):
    """Orquestador del pipeline ETL"""
    telefono_raw = fila_data.get('telefono', fila_data.get('phone_primary', ''))
    telefono_norm = normalizar_telefono(telefono_raw)
    
    nombre_raw = str(fila_data.get('nombre', '')).strip()
    
    # 1. Clasificar Entidad
    tipo_entidad = clasificar_entidad(nombre_raw)
    
    res = {
        "tipo_entidad": tipo_entidad,
        "telefono_norm": telefono_norm,
        "nombre_original": nombre_raw,
    }
    
    if tipo_entidad == 'CORPORATIVO':
        res['nombre_clinica'] = nombre_raw
    elif tipo_entidad == 'MULTIPLE':
        pass # Se enviará a revisión manual
    else:
        # Individuo
        titulo_id, nombre_sin_titulo = extraer_titulo_cortesia(nombre_raw)
        pila, paterno, materno = atomizar_identidad(nombre_sin_titulo)
        
        res['titulo_id'] = titulo_id
        res['nombre_pila'] = pila
        res['apellido_paterno'] = paterno
        res['apellido_materno'] = materno
        
    return res

from django.utils import timezone

def orquestar_ingesta_historica(filas_data, admin_user=None, dry_run=True):
    """
    Orquesta la ingesta de un lote de filas.
    - Soporta Dry Run (sin db impact).
    - Aplica Zona Neutral (estatus='CLIENTE').
    - Detecta Clínica vs Individuo vs Siameses.
    - Usa Evaluación MDM estricta y evita guardar si dry_run=True.
    """
    reporte = {
        "total_procesados": len(filas_data),
        "clinicas_identificadas": 0,
        "individuos_atomizados": 0,
        "siameses_revision_manual": 0,
        "errores_criticos": 0,
        "detalles": []
    }

    # Carga perezosa de Modelos para evitar importaciones circulares en el topo del archivo
    from django.db.models import Q
    from leads.models import CoreLead, Clinica, LeadStaging, CatEspecialidad
    from users.models import CatUbicacion
    from django.contrib.auth import get_user_model
    from leads.mdm_services import evaluar_duplicidad_estricta
    import itertools

    User = get_user_model()

    # --- REGLA 5: ROUND-ROBIN DE VENDEDORES (FUERA DEL CICLO) ---
    vendedores_activos = list(User.objects.filter(is_active=True, is_superuser=False))
    if not vendedores_activos:
        vendedores_activos = [admin_user] if admin_user else []
    
    ruleta_vendedores = itertools.cycle(vendedores_activos) if vendedores_activos else None

    for fila in filas_data:
        resultado_parseo = parsear_fila(fila)
        telefono_norm = resultado_parseo.get('telefono_norm', '')
        nombre_original = resultado_parseo.get('nombre_original', '')
        email_extraido = str(fila.get('email', '')).strip() # REGLA 3a: Extraer Email

        if len(telefono_norm) < 10:
            reporte["errores_criticos"] += 1
            reporte["detalles"].append({"tipo": "ERROR", "data": fila, "motivo": "Teléfono mínimo no alcanzado"})
            if not dry_run and admin_user:
                LeadStaging.objects.create(
                    owner=admin_user,
                    datos_crudos=fila,
                    datos_parseados=resultado_parseo,
                    motivo_conflicto="Teléfono mínimo no alcanzado"
                )
            continue

        # --- REGLA 2: CADENERO ANTI-DUPLICADOS ---
        if CoreLead.objects.filter(phone_primary=telefono_norm).exists():
            continue # Salto silencioso si ya existe en CoreLead

        tipo_entidad = resultado_parseo.get('tipo_entidad')
        
        if tipo_entidad == 'MULTIPLE':
            reporte["siameses_revision_manual"] += 1
            reporte["detalles"].append({"tipo": "REVISION_MANUAL_MULTIPLE", "data": fila, "motivo": "Nombres fusionados o con conectores"})
            if not dry_run and admin_user:
                LeadStaging.objects.create(
                    owner=admin_user,
                    datos_crudos=fila,
                    datos_parseados=resultado_parseo,
                    motivo_conflicto="Clasificado como MULTIPLE (Siameses)"
                )
            continue
            
        # Validación MDM Secundaria
        especialidad_texto = str(fila.get('especialidad', '')).strip()
        ubicacion_texto = str(fila.get('ubicacion', '')).strip()
        
        estatus_mdm, res_mdm = evaluar_duplicidad_estricta(
            nombre_entrante=nombre_original,
            telefono_entrante=telefono_norm,
            especialidad_entrante=especialidad_texto,
            ubicacion_entrante=ubicacion_texto,
            modelo_lead=CoreLead
        )
        
        if estatus_mdm == 'DUPLICADO':
            reporte["siameses_revision_manual"] += 1
            reporte["detalles"].append({"tipo": "REVISION_MANUAL_DUPLICADO", "data": fila, "motivo": f"Choque MDM o tel repetido - (Lead ID: {res_mdm.id})"})
            if not dry_run and admin_user:
                LeadStaging.objects.create(
                    owner=admin_user,
                    datos_crudos=fila,
                    datos_parseados=resultado_parseo,
                    motivo_conflicto=f"Posible duplicado en MDM contra Lead {res_mdm.id}"
                )
            continue

        # --- REGLA 4: TRAMPA DE UBICACIÓN (STAGING) ---
        ubicacion_obj = None
        if ubicacion_texto:
            ubicacion_obj = CatUbicacion.objects.filter(
                Q(ciudad__iexact=ubicacion_texto) | Q(estado__iexact=ubicacion_texto)
            ).filter(is_active=True).first()

        if not ubicacion_obj:
            if not dry_run and admin_user:
                LeadStaging.objects.create(
                    owner=admin_user,
                    datos_crudos=fila,
                    datos_parseados=resultado_parseo,
                    motivo_conflicto=f"Ubicación no válida en catálogo: '{ubicacion_texto}'"
                )
            reporte["errores_criticos"] += 1
            reporte["detalles"].append({"tipo": "ERROR", "data": fila, "motivo": f"Ubicación no válida: {ubicacion_texto}"})
            continue # Manda al quirófano

        # --- REGLA 3b: INYECCIÓN DE ESPECIALIDAD (CATÁLOGO) ---
        especialidad_obj = None
        if especialidad_texto:
            if not dry_run: # Solo creamos el catalogo real si no es dry run
                especialidad_obj, _ = CatEspecialidad.objects.get_or_create(
                    nombre__iexact=especialidad_texto,
                    defaults={'nombre': especialidad_texto.upper(), 'is_active': True}
                )
            else:
                especialidad_obj = CatEspecialidad.objects.filter(nombre__iexact=especialidad_texto).first()

        # Data Neutral para ambos casos
        notas_historicas = {
            "notas": [{
                "tipo": "sistema",
                "contenido": "Migración Histórica: Cronología original no disponible",
                "usuario": admin_user.id if admin_user else None,
                "fecha": timezone.now().isoformat()
            }],
            "columnas_excel_historicas": fila
        }
        
        # Asignar owner de la ruleta
        vendedor_asignado = next(ruleta_vendedores) if ruleta_vendedores else admin_user

        if tipo_entidad == 'CORPORATIVO':
            nombre_clinica = resultado_parseo.get('nombre_clinica', nombre_original)
            if not dry_run and vendedor_asignado:
                clinica_obj, _ = Clinica.objects.get_or_create(
                    telefono_master=telefono_norm,
                    defaults={'nombre': nombre_clinica}
                )
                CoreLead.objects.create(
                    owner=vendedor_asignado,  # REGLA 5: Aplicación Round-Robin
                    estatus='CLIENTE',
                    phone_primary=telefono_norm,
                    email=email_extraido,     # REGLA 3a: Email
                    nombre_pila=nombre_clinica, 
                    nombre=nombre_original,
                    clinica=clinica_obj,
                    especialidad_cat=especialidad_obj, # REGLA 3b: Especialidad Cat
                    ubicacion=ubicacion_obj,  # REGLA 4: Ubicacion asegurada
                    notas_variadas=notas_historicas
                )
            reporte["clinicas_identificadas"] += 1
            reporte["detalles"].append({"tipo": "CORPORATIVO", "data": fila, "nombre_inyectado": nombre_clinica})
            
        elif tipo_entidad == 'INDIVIDUAL':
            if not dry_run and vendedor_asignado:
                CoreLead.objects.create(
                    owner=vendedor_asignado,  # REGLA 5: Aplicación Round-Robin
                    estatus='CLIENTE',
                    phone_primary=telefono_norm,
                    email=email_extraido,     # REGLA 3a: Email
                    titulo_cortesia_id=resultado_parseo.get('titulo_id'),
                    nombre_pila=resultado_parseo.get('nombre_pila'),
                    apellido_paterno=resultado_parseo.get('apellido_paterno'),
                    apellido_materno=resultado_parseo.get('apellido_materno'),
                    nombre=nombre_original,
                    especialidad_cat=especialidad_obj, # REGLA 3b: Especialidad Cat
                    ubicacion=ubicacion_obj,  # REGLA 4: Ubicacion asegurada
                    notas_variadas=notas_historicas
                )
            reporte["individuos_atomizados"] += 1
            reporte["detalles"].append({
                "tipo": "INDIVIDUAL", 
                "data": fila, 
                "pila": resultado_parseo.get('nombre_pila'),
                "paterno": resultado_parseo.get('apellido_paterno'),
                "materno": resultado_parseo.get('apellido_materno')
            })

    return reporte