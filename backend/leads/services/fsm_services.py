from django.utils.timezone import localtime, now
from datetime import datetime
from leads.models import CoreLead
from leads.services.common_services import obtener_catalogos_limpios

def procesar_transicion_fsm(lead_id: str, data: dict, user):
    try:
        lead = CoreLead.objects.get(id=lead_id)
        accion = data.get('action')
        
        # 1. ACTUALIZAR IDENTIDAD ATÓMICA
        if accion in ['VALIDAR', 'GUARDAR']:
            tipo_entidad = data.get('tipo_entidad', 'INDIVIDUAL')
            
            # Limpiamos primero por si venía de corporativo a individuo o viceversa
            lead.nombre_pila = ''
            lead.apellido_paterno = ''
            lead.apellido_materno = ''
            lead.titulo_cortesia_id = None
            
            if tipo_entidad == 'CORPORATIVO':
                nombre_corp = str(data.get('nombre_pila', '')).strip()
                if not nombre_corp:
                     return {"success": False, "error": "La Razón Social es obligatoria.", "status_code": 400}
                     
                lead.nombre_pila = nombre_corp[:100]
                lead.nombre = nombre_corp[:100]
                # Buscar o crear la clínica si no la tiene
                from leads.models import Clinica
                clinica_obj, _ = Clinica.objects.get_or_create(
                    telefono_master=lead.phone_primary,
                    defaults={'nombre': nombre_corp}
                )
                lead.clinica = clinica_obj

            else:
                titulo_id = data.get('titulo_cortesia')
                nombre = str(data.get('nombre_pila', '')).strip()
                paterno = str(data.get('apellido_paterno', '')).strip()
                materno = str(data.get('apellido_materno', '')).strip()

                if not nombre or not paterno:
                    return {"success": False, "error": "Nombre y Apellido Paterno son obligatorios en Individuos.", "status_code": 400}

                lead.titulo_cortesia_id = titulo_id if titulo_id else None
                lead.nombre_pila = nombre[:100]
                lead.apellido_paterno = paterno[:100]
                lead.apellido_materno = materno[:100]
                
                # Desvincular de clínica si cambió a individuo
                lead.clinica = None

                # Reconstruir Fallback MDM
                from leads.models import CatTitulo
                partes_nombre = []
                if nombre: partes_nombre.append(nombre)
                if paterno: partes_nombre.append(paterno)
                if materno: partes_nombre.append(materno)
                lead.nombre = " ".join(partes_nombre)[:100]

            lead.celular = str(data.get('celular', lead.celular)).strip()[:15]
            lead.email = str(data.get('email', lead.email)).strip()
            
            # --- ACTUALIZAR CATÁLOGOS (CANDADO ESTRICTO) ---
            nueva_esp_str = data.get('especialidad', '').strip()
            nuevo_prod_str = data.get('producto', '').strip()
            
            if nueva_esp_str or nuevo_prod_str:
                esp_obj, prod_obj = obtener_catalogos_limpios(nueva_esp_str, nuevo_prod_str)
                if nueva_esp_str: lead.especialidad_cat = esp_obj
                if nuevo_prod_str: lead.producto_cat = prod_obj
        
        # 2. LA MÁQUINA DE ESTADOS
        if accion == 'VALIDAR':
            if lead.estatus == 'PROSPECTO':
                lead.validar_identidad()
                lead.notas_variadas.setdefault("notas", []).append({
                    "tipo": "sistema",
                    "contenido": "Identidad Validada: Avanzó a LEAD.",
                    "fecha": localtime(now()).isoformat()
                })

        elif accion == 'DESCARTAR':
            motivo = data.get('motivo', 'Sin motivo especificado')
            lead.plan = 'DESCARTADO'
            lead.next_action_date = None
            lead.notas_variadas.setdefault("notas", []).append({
                "tipo": "contacto",
                "contenido": f"Descartado: {motivo}",
                "fecha": localtime(now()).isoformat()
            })
            
        elif accion == 'CALIFICAR':
            texto_calificacion = data.get('calificacion')
            
            # EL TRADUCTOR: Mapeamos los textos a números (int4)
            mapa = {'Alta': 3, 'Media': 2, 'Baja': 1}
            
            if texto_calificacion in mapa:
                lead.calificacion = mapa[texto_calificacion]
                
                # Ejecutar la transición de la Máquina de Estados si el lead está en Fase 2
                if lead.estatus == 'LEAD':
                    try:
                        lead.calificar_lead()
                    except Exception as e:
                        return {"success": False, "error": str(e), "status_code": 400}
                
                lead.notas_variadas.setdefault("notas", []).append({
                    "tipo": "sistema",
                    "contenido": f"Lead calificado como: {texto_calificacion}",
                    "fecha": localtime(now()).isoformat()
                })
            else:
                return {"success": False, "error": "Calificación inválida.", "status_code": 400}

        elif accion == 'AGENDAR':
            fecha_contacto_str = data.get('fecha_contacto')
            if not fecha_contacto_str:
                return {"success": False, "error": "La fecha es obligatoria.", "status_code": 400}
            
            fecha_contacto = datetime.strptime(fecha_contacto_str, '%Y-%m-%d').date()
            hoy = localtime(now()).date()
            dias_diferencia = (fecha_contacto - hoy).days
            
            lead.next_action_date = fecha_contacto
            
            if dias_diferencia <= 30:
                lead.plan = 'SEGUIMIENTO'
                mensaje_nota = f"🗓️ Acción a corto plazo: {fecha_contacto_str} (Continúa en Seguimiento)"
            else:
                lead.plan = 'EN_ESPERA'
                mensaje_nota = f"⏸️ Pausado a largo plazo: {fecha_contacto_str} (Pasa a En Espera)"
            
            lead.notas_variadas.setdefault("notas", []).append({
                "tipo": "sistema",
                "contenido": mensaje_nota,
                "fecha": localtime(now()).isoformat()
            })
            
        elif accion == 'AGREGAR_NOTA':
            nueva_nota = data.get('nota')
            if not nueva_nota:
                return {"success": False, "error": "La nota no puede estar vacía.", "status_code": 400}
            
            lead.notas_variadas.setdefault("notas", []).append({
                "tipo": "contacto",
                "contenido": nueva_nota.strip(),
                "fecha": localtime(now()).isoformat()
            })

        elif accion == 'CERRAR_VENTA':
            rfc_val = data.get('rfc', '').strip().upper()
            razon_val = data.get('razon_social', '').strip().upper()
            regimen_val = data.get('regimen_fiscal', '').strip()
            
            if not rfc_val or not razon_val or not regimen_val:
                return {"success": False, "error": "Faltan datos fiscales obligatorios para cerrar la venta.", "status_code": 400}
            
            from leads.models import FiscalProfile
            perfil, created = FiscalProfile.objects.get_or_create(lead=lead)
            perfil.rfc = rfc_val
            perfil.razon_social = razon_val
            perfil.regimen_fiscal = regimen_val
            perfil.save()

            lead.perfil_fiscal = perfil

            try:
                lead.formalizar_cliente()
            except Exception as e:
                return {"success": False, "error": str(e), "status_code": 400}
            
            timestamp = localtime(now()).strftime("%Y-%m-%d %H:%M")
            
            if not isinstance(lead.notas_variadas, dict):
                lead.notas_variadas = {"notas": []}
            if "notas" not in lead.notas_variadas:
                lead.notas_variadas["notas"] = []
                
            lead.notas_variadas["notas"].append({
                "fecha": timestamp,
                "tipo": "sistema",
                "contenido": f"🏆 ¡VENTA CERRADA! RFC capturado: {rfc_val}. El prospecto se ha convertido oficialmente en CLIENTE."
            })
            lead.save()
            return {"success": True, "status": "success", "mensaje": "¡Venta cerrada con éxito!", "nuevo_estatus": lead.estatus}

        elif accion == 'DESECHAR':
             try:
                 lead.delete()
                 return {"success": True, "status": "deleted", "mensaje": "Prospecto desechado físicamente de la base de datos.", "nuevo_estatus": "ELIMINADO"}
             except Exception as e:
                 return {"success": False, "error": str(e), "status_code": 400}

        # 3. GUARDADO FINAL
        lead.save()
        
        return {
            "success": True, 
            "status": "success",
            "mensaje": f"Operación {accion} realizada con éxito.",
            "nuevo_estatus": lead.estatus
        }

    except CoreLead.DoesNotExist:
        return {"success": False, "error": "Lead no encontrado.", "status_code": 404}
    except Exception as e:
        return {"success": False, "error": str(e), "status_code": 400}
