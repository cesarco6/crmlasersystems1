from django.views.generic import TemplateView
from django.views.generic import DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from users.permissions import role_required
from .mixins import LeadOwnershipMixin
from .models import CoreLead

@method_decorator(role_required(['VENDEDOR']), name='dispatch')
class DashboardAgenteView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'dashboard_agente.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['leads'] = CoreLead.objects.all().order_by('-id')[:10]
        return context

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaMasivaView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'ingesta_masiva.html'

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class AltaIndividualView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'alta_individual.html'


# 2. FICHA DE TRABAJO (Blindada contra el auto-formateador de VS Code)
@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class FichaTrabajoView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'ficha_trabajo.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead_id = self.kwargs.get('pk') or self.kwargs.get('id')
        lead = get_object_or_404(CoreLead, id=lead_id)
        '''
        print("\n" + "="*50)
        print("🔍 RASTREO: DATOS CRUDOS DESDE POSTGRES")
        print("="*50)
        print(f"ID:              {lead.id}")
        print(f"Nombre:          {repr(lead.nombre)}")
        print(f"Especialidad:    {repr(lead.especialidad)}")
        print(f"Ubicación:       {repr(lead.ubicacion.ciudad if lead.ubicacion else None)}")
        print(f"Producto Int.:   {repr(lead.producto_interes)}")
        print(f"Celular:         {repr(lead.celular)}")
        print("="*50 + "\n")
        '''
        
        # Mandamos el objeto completo
        context['lead'] = lead
        # Variables súper cortas para que el HTML no se rompa al guardar
        context['celular_seguro'] = lead.celular if lead.celular else "No registrado"
        context['especialidad_segura'] = lead.especialidad if lead.especialidad else "No especificada"
        context['producto_seguro'] = lead.producto_interes if lead.producto_interes else "No especificado"
        
        return context

import json
from datetime import datetime
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from users.models import CatUbicacion
from django.contrib.auth import get_user_model

User = get_user_model()

import unicodedata

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    # Eliminar acentos
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

@require_POST
def procesar_ingesta_masiva(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)
    
    try:
        data = json.loads(request.body)
        
        default_user = User.objects.filter(is_superuser=True).first()

        reporte = {'A': [], 'B': [], 'C': [], 'D': []}

        # Cargar catálogo de ciudades normalizado en memoria para búsquedas ultrarrápidas
        ubicaciones_db = CatUbicacion.objects.all()
        mapa_ciudades = {normalizar_texto(u.ciudad): u for u in ubicaciones_db}

        for lead_data in data:
            if not isinstance(lead_data, dict):
                continue
            
            # Se requiere phone_primary de manera obligatoria
            telefono = str(lead_data.get('telefono', '')).strip()
            if not telefono:
                continue # Saltamos filas sin teléfono
                
            nombre_raw = str(lead_data.get('nombre', 'Sin Nombre')).strip()
            # Normalización del nombre
            nombre_norm = nombre_raw.lower().replace('dr.', '').replace('dr ', '').replace('dra.', '').replace('dra ', '').strip()

            especialidad = str(lead_data.get('especialidad', 'General')).strip()
            producto_interes = str(lead_data.get('producto', 'No especificado')).strip()
            
            # --- VALIDACIÓN ESTRICTA DE CIUDAD ---
            ciudad_excel = lead_data.get('ubicacion', '')
            ciudad_norm = normalizar_texto(ciudad_excel)
            
            if not ciudad_norm:
                reporte["D"].append({"fila": lead_data, "motivo": "El campo de ubicación/ciudad viene vacío."})
                continue
                
            ubicacion_obj = mapa_ciudades.get(ciudad_norm)
            
            if not ubicacion_obj:
                reporte["D"].append({
                    "fila": lead_data, 
                    "motivo": f"Ciudad no reconocida: '{ciudad_excel}'. Escríbela correctamente o solicita al Admin que la agregue al catálogo."
                })
                continue # Saltamos este registro (no se inyecta, va a Caso D)

            val_direccion = str(lead_data.get('direccion_completa', '')).strip()
            val_celular = str(lead_data.get('celular', '')).strip()
            val_email = str(lead_data.get('email', '')).strip()
            notas_variadas_val = str(lead_data.get('notas', '')).strip()

            notas_json = {
                "notas": [],
                "columnas_excel_historicas": {}
            }

            if notas_variadas_val:
                notas_json["notas"].append({
                    "tipo": "contacto",
                    "contenido": notas_variadas_val,
                    "fecha": timezone.now().isoformat()
                })

            # Lógica de Arbitraje de 4 Casos
            lead_existente = CoreLead.objects.filter(phone_primary=telefono[:15]).first()
            
            if not lead_existente:
                # CASO A: Registro Nuevo
                nuevo_lead = CoreLead.objects.create(
                    owner=request.user,
                    ubicacion_id=ubicacion_obj.id,
                    estatus='PROSPECTO', # <-- NACIMIENTO EN FASE 1 (DDS 2.0)
                    phone_primary=telefono[:15],
                    celular=val_celular[:15],
                    email=val_email,
                    direccion_completa=val_direccion[:255],
                    nombre=nombre_raw[:100],
                    especialidad=especialidad[:50],
                    producto_interes=producto_interes[:50],
                    notas_variadas=notas_json
                )
                reporte['A'].append(telefono[:15])

            elif lead_existente.nombre.lower().replace('dr.', '').replace('dr ', '').replace('dra.', '').replace('dra ', '').strip() != nombre_norm:
                # CASO A: Clínica Compartida (Mismo tel, distinto nombre)
                nuevo_lead = CoreLead.objects.create(
                    owner=request.user,
                    ubicacion_id=ubicacion_obj.id,
                    estatus='PROSPECTO', # <-- NACIMIENTO EN FASE 1 (DDS 2.0)
                    phone_primary=telefono[:15],
                    celular=val_celular[:15],
                    email=val_email,
                    direccion_completa=val_direccion[:255],
                    nombre=nombre_raw[:100],
                    especialidad=especialidad[:50],
                    producto_interes=producto_interes[:50],
                    notas_variadas=notas_json
                )
                reporte['A'].append(f"{telefono[:15]} (Nueva Persona)")

            else:
                # CASOS B, C y D (Existe y es la misma persona)
                if lead_existente.estatus == 'CLIENTE':
                    # CASO C: Intento de re-ingesta de un cliente
                    lead_existente.notas_variadas.setdefault("notas", []).append({
                        "tipo": "sistema",
                        "contenido": f"Intento de re-ingesta masiva bloqueado el {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                        "fecha": timezone.now().isoformat()
                    })
                    lead_existente.save(update_fields=['notas_variadas', 'updated_at'])
                    reporte['C'].append(nombre_raw)
                elif lead_existente.estatus == 'NO_CIERRE' and timezone.now() - lead_existente.updated_at > timedelta(days=365):
                    # CASO D: Revisión manual (Inactivo por > 1 año)
                    reporte['D'].append(nombre_raw)
                else:
                    # CASO B: Duplicado de dueño activo
                    reporte['B'].append(nombre_raw)

        return JsonResponse({'status': 'success', 'reporte': reporte})

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON Inválido enviado en la petición."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_POST
def procesar_alta_manual(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # 1. Extraemos los datos del Modal
        telefono = str(data.get('telefono', '')).strip()
        celular = str(data.get('celular', '')).strip()
        email = str(data.get('email', '')).strip()
        nombre = str(data.get('nombre', '')).strip()
        especialidad = str(data.get('especialidad', 'No especificada')).strip()
        valor_ubicacion = str(data.get('ubicacion', 'Desconocida')).strip()
        
        # Validaciones básicas
        if not telefono or not nombre:
            return JsonResponse({"error": "El nombre y teléfono son obligatorios."}, status=400)
            
        if CoreLead.objects.filter(phone_primary=telefono[:15]).exists():
            return JsonResponse({"error": "Ya existe un registro con este Teléfono Primario en el sistema."}, status=400)

        # 2. Gestionamos la Ubicación
        ubicacion_obj, created = CatUbicacion.objects.get_or_create(
            ciudad=valor_ubicacion, 
            defaults={'estado': valor_ubicacion, 'is_active': True}
        )

        # 3. Creamos el Lead (Nace en Fase 1)
        nuevo_lead = CoreLead.objects.create(
            owner=request.user,
            ubicacion_id=ubicacion_obj.id,
            estatus='PROSPECTO',
            phone_primary=telefono[:15],
            celular=celular[:15],
            email=email,
            nombre=nombre[:100],
            especialidad=especialidad[:50],
            producto_interes='No especificado', # Se llenará después
            notas_variadas={"notas": [], "columnas_excel_historicas": {}}
        )

        return JsonResponse({
            'status': 'success', 
            'mensaje': 'Prospecto creado exitosamente',
            'lead_id': str(nuevo_lead.id)
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Datos inválidos enviados desde el formulario."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_POST
def actualizar_lead_fsm(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)
    
    try:
        data = json.loads(request.body)
        accion = data.get('accion') 
        lead = get_object_or_404(CoreLead, id=pk)
        
        # --- REGLA: DESECHAR (ELIMINAR) ---
        if accion == 'DESECHAR':
            if lead.estatus == 'PROSPECTO':
                lead.delete() 
                return JsonResponse({"status": "deleted", "mensaje": "Prospecto desechado y eliminado de la base de datos."})
            else:
                return JsonResponse({"error": "Solo puedes desechar prospectos en Fase 1."}, status=400)

        # 1. ACTUALIZAR DATOS BASE (Candado de Integridad DDS)
        # Datos de Enriquecimiento (Siempre editables)
        lead.celular = data.get('celular', lead.celular)
        lead.email = data.get('email', lead.email)
        lead.direccion_completa = data.get('direccion', lead.direccion_completa)
        
        # Datos de Identidad (Solo editables en Fase 1)
        if lead.estatus == 'PROSPECTO':
            lead.nombre = data.get('nombre', lead.nombre)
            lead.phone_primary = data.get('telefono', lead.phone_primary)
            lead.especialidad = data.get('especialidad', lead.especialidad)
            lead.producto_interes = data.get('producto', lead.producto_interes)
        
        # 2. LA MÁQUINA DE ESTADOS
        if accion == 'VALIDAR':
            if lead.estatus == 'PROSPECTO':
                lead.validar_identidad()
                lead.notas_variadas.setdefault("notas", []).append({
                    "tipo": "sistema",
                    "contenido": "Identidad Validada: Avanzó a LEAD.",
                    "fecha": timezone.now().isoformat()
                })

        elif accion == 'DESCARTAR':
            motivo = data.get('motivo', 'Sin motivo especificado')
            lead.archivar_sin_exito(motivo, request.user.id)
            
        elif accion == 'CALIFICAR':
            texto_calificacion = data.get('calificacion')
            
            # EL TRADUCTOR: Mapeamos los textos a números (int4)
            mapa = {'Alta': 3, 'Media': 2, 'Baja': 1}
            
            if texto_calificacion in mapa:
                lead.calificacion = mapa[texto_calificacion] # Guarda el número en la DB
                lead.notas_variadas.setdefault("notas", []).append({
                    "tipo": "sistema",
                    "contenido": f"Lead calificado como: {texto_calificacion}", # Muestra el texto al vendedor
                    "fecha": timezone.now().isoformat()
                })
            else:
                return JsonResponse({"error": "Calificación inválida."}, status=400)

        elif accion == 'AGENDAR':
            fecha_contacto_str = data.get('fecha_contacto')
            if not fecha_contacto_str:
                return JsonResponse({"error": "La fecha es obligatoria."}, status=400)
            
            # Convertir a objeto date y calcular diferencia
            fecha_contacto = datetime.strptime(fecha_contacto_str, '%Y-%m-%d').date()
            hoy = timezone.now().date()
            dias_diferencia = (fecha_contacto - hoy).days
            
            lead.next_action_date = fecha_contacto
            
            # REGLA DDS: Gatillo Inteligente de 30 días
            if dias_diferencia <= 30:
                lead.plan = 'SEGUIMIENTO'
                mensaje_nota = f"🗓️ Acción a corto plazo: {fecha_contacto_str} (Continúa en Seguimiento)"
            else:
                lead.plan = 'EN_ESPERA'
                mensaje_nota = f"⏸️ Pausado a largo plazo: {fecha_contacto_str} (Pasa a En Espera)"
            
            lead.notas_variadas.setdefault("notas", []).append({
                "tipo": "sistema",
                "contenido": mensaje_nota,
                "fecha": timezone.now().isoformat()
            })
            
        elif accion == 'AGREGAR_NOTA':
            nueva_nota = data.get('nota')
            if not nueva_nota:
                return JsonResponse({"error": "La nota no puede estar vacía."}, status=400)
            
            lead.notas_variadas.setdefault("notas", []).append({
                "tipo": "contacto", # 'contacto' es manual del vendedor, 'sistema' es de la FSM
                "contenido": nueva_nota.strip(),
                "fecha": timezone.now().isoformat()
            })
            
        # 3. GUARDADO FINAL
        lead.save()
        
        return JsonResponse({
            "status": "success", 
            "mensaje": f"Operación {accion} realizada con éxito.",
            "nuevo_estatus": lead.estatus
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)