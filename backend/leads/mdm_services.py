import unicodedata
import re

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    # Eliminar acentos
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_telefono_estricto(telefono):
    """Extrae solo dígitos numéricos. Retorna máximo 15 apegándose a la BD."""
    if not telefono:
        return ""
    digitos = re.sub(r'\D', '', str(telefono))
    return digitos[:15]

def evaluar_duplicidad_estricta(nombre_entrante, telefono_entrante, especialidad_entrante, ubicacion_entrante, modelo_lead):
    """
    Evalúa la identidad cruzando la Cuarteta (Nombre, Teléfono, Especialidad, Ubicación).
    Retorna: (ESTATUS, RESULTADO)
    donde ESTATUS puede ser: 'ERROR', 'NUEVO', 'DUPLICADO', 'COMPARTIDO'
    """
    # Filtro 1 (Teléfono): Limpia el teléfono
    telefono_limpio = limpiar_telefono_estricto(telefono_entrante)
    if not telefono_limpio:
        return ('ERROR', 'Teléfono inválido')
        
    coincidencias_telefono = modelo_lead.objects.filter(phone_primary=telefono_limpio)
    
    # Si no existe en CoreLead, retorna NUEVO inmediatamente
    if not coincidencias_telefono.exists():
        return ('NUEVO', telefono_limpio)
        
    stopwords_medicas = {'dr', 'dra', 'doctor', 'doctora', 'de', 'la', 'el', 'los', 'las', 'y'}
    
    def extraer_set_palabras(texto):
        t_norm = normalizar_texto(texto)
        solo_letras = re.sub(r'[^a-z\s]', '', t_norm)
        palabras = set(solo_letras.split())
        return palabras - stopwords_medicas

    def normalizar_parametro(texto):
        """Normaliza especialidad/ubicación (minúsculas, sin espacios) para la heurística MDM"""
        if not texto: return ""
        return normalizar_texto(texto).replace(" ", "")

    set_entrante = extraer_set_palabras(nombre_entrante)
    especialidad_entrante_norm = normalizar_parametro(especialidad_entrante)
    ubicacion_entrante_norm = normalizar_parametro(ubicacion_entrante)
    
    for lead_existente in coincidencias_telefono:
        # Filtro 2 (Choque de Nombres)
        set_existente = extraer_set_palabras(lead_existente.nombre)
        
        # Si la intersección es vacía (0 coincidencias lexicográficas), no chocan sus nombres
        if not set_entrante.intersection(set_existente):
            continue
            
        # Filtro 3 (Desempate por Cuarteta - Excepción Call Center)
        # Extraemos la especialidad y ubicación del lead en BD previniendo Nulls
        esp_existente = lead_existente.especialidad_cat.nombre if lead_existente.especialidad_cat else ""
        ubi_existente = lead_existente.ubicacion.ciudad if lead_existente.ubicacion else ""
        if not ubi_existente and lead_existente.ubicacion:
            ubi_existente = lead_existente.ubicacion.estado or ""
            
        esp_existente_norm = normalizar_parametro(esp_existente)
        ubi_existente_norm = normalizar_parametro(ubi_existente)
        
        # Si la Especialidad es DIFERENTE Y la Ubicación es DIFERENTE, es falso positivo (directorio/clínica)
        if esp_existente_norm != especialidad_entrante_norm and ubi_existente_norm != ubicacion_entrante_norm:
            continue
            
        # Si la Especialidad ES IGUAL O la Ubicación ES IGUAL, el filtro falla, confirmando la duplicidad
        return ('DUPLICADO', lead_existente)
            
    # Si termina de evaluar el set completo sin saltar a 'DUPLICADO', es un teléfono compartido
    return ('COMPARTIDO', telefono_limpio)
