from leads.models import CoreLead, Clinica, CatTitulo, CatUbicacion
from leads.services.common_services import obtener_catalogos_limpios
from leads.mdm_services import evaluar_duplicidad_estricta

def crear_prospecto_core(data: dict, user):
    try:
        telefono = str(data.get('telefono', '')).strip()
        celular = str(data.get('celular', '')).strip()
        email = str(data.get('email', '')).strip()
        
        tipo_entidad = data.get('tipo_entidad', 'INDIVIDUAL')
        titulo_id = data.get('titulo_cortesia')
        nombre_pila = str(data.get('nombre_pila', '')).strip()
        apellido_paterno = str(data.get('apellido_paterno', '')).strip()
        apellido_materno = str(data.get('apellido_materno', '')).strip()

        valor_especialidad = str(data.get('especialidad', 'No especificada')).strip()
        valor_producto = str(data.get('producto', 'No especificado')).strip()
        valor_ubicacion = str(data.get('ubicacion', 'Desconocida')).strip()
        
        titulo_obj = CatTitulo.objects.filter(id=titulo_id).first() if titulo_id else None
        
        nombre_concatenado = ""
        if tipo_entidad == 'CORPORATIVO':
            nombre_concatenado = nombre_pila
        else:
            partes_nombre = []
            if nombre_pila: partes_nombre.append(nombre_pila)
            if apellido_paterno: partes_nombre.append(apellido_paterno)
            if apellido_materno: partes_nombre.append(apellido_materno)
            nombre_concatenado = " ".join(partes_nombre)
        
        if not nombre_concatenado:
            return {"success": False, "error": "El nombre es obligatorio.", "status_code": 400}
            
        estatus_identidad, resultado_identidad = evaluar_duplicidad_estricta(
            nombre_concatenado, telefono, valor_especialidad, valor_ubicacion, CoreLead
        )
        
        if estatus_identidad == 'ERROR':
            return {"success": False, "error": resultado_identidad, "status_code": 400}
            
        elif estatus_identidad == 'DUPLICADO':
            dueño_actual = resultado_identidad.owner.username if resultado_identidad.owner else 'Sin asignar'
            return {"success": False, "error": f"⚠️ Posible Duplicado: Un registro similar ({resultado_identidad.nombre}) ya usa este teléfono. Pertenece a la cartera de {dueño_actual}.", "status_code": 400}
            
        telefono_limpio = resultado_identidad
        
        especialidad_obj, producto_obj = obtener_catalogos_limpios(valor_especialidad, valor_producto)

        ubicacion_obj, created = CatUbicacion.objects.get_or_create(
            ciudad=valor_ubicacion, 
            defaults={'estado': valor_ubicacion, 'is_active': True}
        )

        if tipo_entidad == 'CORPORATIVO':
            clinica_obj, _ = Clinica.objects.get_or_create(
                telefono_master=telefono_limpio,
                defaults={'nombre': nombre_concatenado}
            )
            nuevo_lead = CoreLead.objects.create(
                owner=user,
                ubicacion=ubicacion_obj,
                especialidad_cat=especialidad_obj,
                producto_cat=producto_obj,
                estatus='PROSPECTO',
                phone_primary=telefono_limpio,
                celular=celular[:15],
                email=email,
                #nombre=nombre_concatenado[:100],                 
                nombre_pila=nombre_concatenado[:100],
                clinica=clinica_obj,
                notas_variadas={"notas": [], "columnas_excel_historicas": {}}
            )
        else:
            nuevo_lead = CoreLead.objects.create(
                owner=user,
                ubicacion=ubicacion_obj,
                especialidad_cat=especialidad_obj,
                producto_cat=producto_obj,
                estatus='PROSPECTO',
                phone_primary=telefono_limpio,
                celular=celular[:15],
                email=email,
                #nombre=nombre_concatenado[:100],
                titulo_cortesia=titulo_obj,
                nombre_pila=nombre_pila[:100],
                apellido_paterno=apellido_paterno[:100],
                apellido_materno=apellido_materno[:100],
                notas_variadas={"notas": [], "columnas_excel_historicas": {}}
            )

        return {"success": True, "lead_id": str(nuevo_lead.id), "mensaje": "Prospecto creado exitosamente"}

    except Exception as e:
        return {"success": False, "error": str(e), "status_code": 500}
