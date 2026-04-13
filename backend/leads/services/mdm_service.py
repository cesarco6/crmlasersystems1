import unicodedata
import difflib
from leads.models import CoreLead, Clinica

def normalizar_texto(texto):
    """
    Función helper que quita acentos, pasa a minúsculas 
    y elimina espacios en blanco extra de los extremos.
    """
    if not texto:
        return ""
    
    # 1. Asegurar que sea string
    texto = str(texto)
    
    # 2. Quitar acentos
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto) 
        if unicodedata.category(c) != 'Mn'
    )
    
    # 3. Minúsculas y remover espacios extra en extremos (y en medio)
    return " ".join(texto.strip().lower().split())

def resolver_identidad(datos_dict):
    """Central Master Data Management (MDM) algorithm to resolve duplications.
    
    Evaluates potential identity collisions based on normalization heuristics, 
    string similarity (SequenceMatcher), and strict telecom uniqueness.
    Routes the workflow through either 'CORPORATIVO' or 'INDIVIDUAL' collision paths.
    
    Args:
        datos_dict (dict): Payload containing identity vectors: 'tipo_entidad', 
            'nombre_pila', 'apellido_paterno', 'apellido_materno', 'telefono', 
            'especialidad_obj', 'ubicacion_obj'.
    
    Returns:
        tuple (Model, str|None): 
            - The matched or newly created entity (Clinica or CoreLead).
            - An alternative phone string if the match implies a secondary line, None otherwise.
            
    Raises:
        ValueError: If a strict phone collision exists preventing deterministic creation.
    """
    tipo_entidad = datos_dict.get('tipo_entidad')
    nombre_pila = datos_dict.get('nombre_pila', '')
    apellido_paterno = datos_dict.get('apellido_paterno', '')
    apellido_materno = datos_dict.get('apellido_materno', '')
    telefono = datos_dict.get('telefono')
    especialidad_obj = datos_dict.get('especialidad_obj')
    ubicacion_obj = datos_dict.get('ubicacion_obj')

    if tipo_entidad == 'CORPORATIVO':
        nombre_norm = normalizar_texto(nombre_pila)
        
        # 1. OPTIMIZACIÓN: Solo buscamos clínicas en esa misma ciudad
        clinicas_posibles = Clinica.objects.filter(ubicacion=ubicacion_obj)
        
        clinica_match = None
        for clinica in clinicas_posibles:
            if normalizar_texto(clinica.nombre) == nombre_norm:
                clinica_match = clinica
                break
                
        # 2. MATCH ENCONTRADO (Misma Clínica, misma ciudad)
        if clinica_match:
            telefono_alternativo = None
            if telefono and clinica_match.telefono_master != telefono:
                telefono_alternativo = telefono
            return clinica_match, telefono_alternativo
            
        # 3. COLISIÓN DE TELÉFONO: El nombre/ciudad no existe, pero el teléfono sí (Ladrón de identidad)
        if telefono:
            clinica_telefono = Clinica.objects.filter(telefono_master=telefono).first()
            if clinica_telefono:
                raise ValueError(f"Colisión MDM: El teléfono {telefono} ya pertenece a la Clínica '{clinica_telefono.nombre}'.")
                
        # 4. CREACIÓN (Nueva sucursal o clínica totalmente nueva)
        nueva_clinica = Clinica.objects.create(
            nombre=nombre_pila,
            telefono_master=telefono if telefono else "0000000000",
            ubicacion=ubicacion_obj  # <-- INYECTAMOS LA UBICACIÓN FÍSICA
        )
        return nueva_clinica, None

    elif tipo_entidad == 'INDIVIDUAL':
        nombre_completo = f"{nombre_pila or ''} {apellido_paterno or ''} {apellido_materno or ''}".strip()
        nombre_norm = normalizar_texto(nombre_completo)
        
        # Filtramos primero por especialidad y ubicacion para optimizar memoria
        leads_posibles = CoreLead.objects.filter(
            especialidad_cat=especialidad_obj, 
            ubicacion=ubicacion_obj
        )
        
        lead_match = None
        max_similitud = 0.0
        
        for lead in leads_posibles:
            lead_nombre_bd = f"{lead.nombre_pila or ''} {lead.apellido_paterno or ''} {lead.apellido_materno or ''}".strip()
            lead_nombre_norm = normalizar_texto(lead_nombre_bd)
            
            similitud = difflib.SequenceMatcher(None, nombre_norm, lead_nombre_norm).ratio()
            
            # Guardamos el lead si la similitud es > 0.85
            if similitud > 0.85 and similitud > max_similitud:
                max_similitud = similitud
                lead_match = lead
                
        if lead_match:
            telefono_alternativo = None
            # CoreLead define el teléfono principal como `phone_primary`
            if telefono and lead_match.phone_primary != telefono:
                telefono_alternativo = telefono
            return lead_match, telefono_alternativo
            
        # Si no hubo match por nombre, buscamos si el teléfono entrante ya existe en otro prospecto
        if telefono:
            lead_telefono = CoreLead.objects.filter(phone_primary=telefono).first()
            if lead_telefono:
                raise ValueError(f"Colisión MDM: El teléfono {telefono} ya pertenece al prospecto '{lead_telefono.nombre_pila} {lead_telefono.apellido_paterno}'.")
                
        # Si no hubo match por nombre ni colisión por teléfono, retorna None, None
        return None, None

    return None, None
