from django.views.generic import TemplateView
from django.views.generic import DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.core.paginator import Paginator
from users.permissions import role_required
from django.db.models import Q
from django.utils import timezone
from .mixins import LeadOwnershipMixin
from .models import CoreLead, Notificacion
from users.models import CatUbicacion, CatEspecialidad, CatProducto

@method_decorator(role_required(['VENDEDOR']), name='dispatch')
class DashboardAgenteView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'dashboard_agente.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. CAPTURAR LO QUE EL VENDEDOR QUIERE VER
        busqueda = self.request.GET.get('q', '').strip()
        filtro_rapido = self.request.GET.get('filtro', 'activos') # 'activos' por defecto
        
        hoy = timezone.now().date()

        # 2. BASE DE SEGURIDAD: Solo los leads de ESTE vendedor
        qs = CoreLead.objects.filter(owner=self.request.user)

        # ---------------------------------------------------------
        # ESCENARIO A: EL FRANCOTIRADOR (Buscando un registro específico)
        # ---------------------------------------------------------
        if busqueda:
            # Si hay búsqueda, rompemos las reglas y buscamos en TODA su cartera histórica
            qs = qs.filter(
                Q(nombre__icontains=busqueda) |
                Q(phone_primary__icontains=busqueda) |
                Q(celular__icontains=busqueda) |
                Q(email__icontains=busqueda)
            )
            
        # ---------------------------------------------------------
        # ESCENARIO B: LA RED DE ARRASTRE (Filtrando grupos diarios)
        # ---------------------------------------------------------
        else:
            # Regla INBOX ZERO: Ocultar los que ya terminaron su ciclo
            qs = qs.exclude(estatus__in=['CLIENTE', 'NO_CIERRE']).exclude(plan='DESCARTADO')
            
            # Regla HIBERNACIÓN: Si está "En Espera" para una fecha futura, lo ocultamos hoy
            # (Asumiendo que usas next_action_date, si usas otro campo, lo cambiamos)
            qs = qs.exclude(Q(plan='EN_ESPERA') & Q(next_action_date__gt=hoy))

            # Aplicar el botón que el vendedor haya presionado
            if filtro_rapido == 'hoy':
                qs = qs.filter(next_action_date=hoy)
            elif filtro_rapido == 'frescos':
                qs = qs.filter(estatus='PROSPECTO')
            elif filtro_rapido == 'urgentes':
                # Ejemplo: leads en SEGUIMIENTO que su fecha de acción ya se pasó
                qs = qs.filter(plan='SEGUIMIENTO', next_action_date__lt=hoy)
        
        # Ordenamos la consulta final
        qs = qs.order_by('-updated_at')

        # Dividimos en bloques de 10 registros por página
        paginador = Paginator(qs, 10) 
        numero_pagina = self.request.GET.get('page')
        pagina_obj = paginador.get_page(numero_pagina)

        # 3. ENVIAR RESULTADOS AL HTML
        # OJO: Ahora mandamos la página actual, no toda la base de datos
        context['leads'] = pagina_obj 
        context['page_obj'] = pagina_obj # Lo mandamos también con este nombre por convención de Django
        
        context['busqueda_actual'] = busqueda
        context['filtro_actual'] = filtro_rapido
        
        context['total_activos'] = CoreLead.objects.filter(owner=self.request.user).exclude(estatus__in=['CLIENTE', 'NO_CIERRE']).exclude(plan='DESCARTADO').count()
        # --- LÍNEAS NUEVAS PARA EL MODAL DE ALTA RÁPIDA ---
        context['especialidades_list'] = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
        context['productos_list'] = CatProducto.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
      
        # 3. ENVIAR RESULTADOS AL HTML
        context['leads'] = qs.order_by('-updated_at') # Los movidos recientemente van arriba
        context['busqueda_actual'] = busqueda
        context['filtro_actual'] = filtro_rapido
        
        # KPIs rápidos para la parte superior del Dashboard (Contadores)
        context['total_activos'] = CoreLead.objects.filter(owner=self.request.user).exclude(estatus__in=['CLIENTE', 'NO_CIERRE']).exclude(plan='DESCARTADO').count()
        
        return context

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaMasivaView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'ingesta_masiva.html'

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class AltaIndividualView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'alta_individual.html'

@method_decorator(role_required(['DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaHistoricaView(LoginRequiredMixin, TemplateView):
    template_name = 'director_ingesta.html'


# 2. FICHA DE TRABAJO (Blindada contra el auto-formateador de VS Code)
@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class FichaTrabajoView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'ficha_trabajo.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead_id = self.kwargs.get('pk') or self.kwargs.get('id')
        lead = get_object_or_404(CoreLead, id=lead_id)
        
        # Mandamos el objeto completo
        context['lead'] = lead
        # --- NUEVAS LÍNEAS PARA LOS DROPDOWNS ---
        context['especialidades_list'] = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
        context['productos_list'] = CatProducto.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
        # Variables súper cortas para que el HTML no se rompa al guardar
        context['celular_seguro'] = lead.celular if lead.celular else "No registrado"
        context['especialidad_segura'] = lead.especialidad if lead.especialidad else "No especificada"
        context['producto_seguro'] = lead.producto_interes if lead.producto_interes else "No especificado"
        
        return context

import json
from datetime import datetime
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from users.models import CatUbicacion
from django.contrib.auth import get_user_model

User = get_user_model()

import unicodedata

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    # Eliminar acentos
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def obtener_catalogos_limpios(texto_especialidad, texto_producto):
    """
    Recibe textos libres y devuelve las instancias de los catálogos relacionales.
    """
    especialidad_obj = None
    producto_obj = None

    # 1. Procesar Producto (Estricto - Bóveda de 14 productos)
    texto_prod_norm = normalizar_texto(texto_producto)
    if texto_prod_norm:
        # Buscamos coincidencia exacta o en alias
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

@login_required
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

            esp_obj, prod_obj = obtener_catalogos_limpios(especialidad, producto_interes)

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
                    #especialidad=especialidad[:50],
                    #producto_interes=producto_interes[:50],                    
                    especialidad_cat=esp_obj,   # <-- NUEVO
                    producto_cat=prod_obj,      # <-- NUEVO
                    notas_variadas=notas_json,
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
                    #especialidad=especialidad[:50],
                    #producto_interes=producto_interes[:50],
                    especialidad_cat=esp_obj,   # <-- NUEVO
                    producto_cat=prod_obj,      # <-- NUEVO
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


@login_required
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
            especialidad_cat_id=especialidad_obj.id,
            producto_cat_id=producto_obj.id,
            estatus='PROSPECTO',
            phone_primary=telefono[:15],
            celular=celular[:15],
            email=email,
            nombre=nombre[:100],
            #especialidad=especialidad[:50],
            #producto_interes='No especificado', # Se llenará después
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

@login_required
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
            # --- USAMOS LA ADUANA PARA GUARDAR LOS SELECTS DEL VENDEDOR ---
            texto_esp = data.get('especialidad', lead.especialidad_cat.nombre if lead.especialidad_cat else 'General')
            texto_prod = data.get('producto', lead.producto_cat.nombre if lead.producto_cat else 'Por Definir / Otro')
            
            esp_obj, prod_obj = obtener_catalogos_limpios(texto_esp, texto_prod)
            
            lead.especialidad_cat = esp_obj
            lead.producto_cat = prod_obj
            
            # Borramos el guardado en los campos viejos de texto libre
            #lead.especialidad = data.get('especialidad', lead.especialidad)
            #lead.producto_interes = data.get('producto', lead.producto_interes)

            # --- NUEVO: ACTUALIZAR CATÁLOGOS ---
            # 1. Procesamos la Especialidad
            nueva_esp_str = data.get('especialidad', '').strip()
            if nueva_esp_str:
                # Buscamos o creamos el objeto de especialidad
                esp_obj, created = CatEspecialidad.objects.get_or_create(
                    nombre=nueva_esp_str,
                    defaults={'is_active': True}
                )
                lead.especialidad_cat = esp_obj
            
            # 2. Procesamos el Producto
            nuevo_prod_str = data.get('producto', '').strip()
            if nuevo_prod_str:
                # Buscamos o creamos el objeto de producto
                prod_obj, created = CatProducto.objects.get_or_create(
                    nombre=nuevo_prod_str,
                    defaults={'is_active': True}
                )
                lead.producto_cat = prod_obj
        
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


def es_director(user):
    return user.is_superuser

@login_required
@user_passes_test(es_director)
@require_POST
def api_ingesta_historica(request):
    try:
        data = json.loads(request.body)
        filas = data.get('datos', [])
        
        reporte = {"procesados": 0, "creados": 0, "actualizados": 0, "errores": []}
        
        # Cargar catálogo de ciudades para asignación ultrarrápida
        mapa_ciudades = {normalizar_texto(u.ciudad): u for u in CatUbicacion.objects.all()}
        
        for index, fila in enumerate(filas):
            telefono = str(fila.get('telefono', '')).strip()
            if not telefono:
                reporte["errores"].append(f"Fila {index + 1}: Sin teléfono. Ignorada.")
                continue
            
            # 1. Asignación Inteligente de Territorio
            ciudad_excel = fila.get('ubicacion', '')
            ubicacion_obj = mapa_ciudades.get(normalizar_texto(ciudad_excel))
            
            vendedor_asignado = request.user # Por defecto se lo queda el Director
            
            if ubicacion_obj:
                # Obtener dueños del territorio a través de AsignacionTerritorio -> UserProfile -> User
                # CatUbicacion tiene un related_name inverso por defecto asignacionterritorio_set
                asignaciones = ubicacion_obj.asignacionterritorio_set.select_related('user_profile__user').all()
                if asignaciones.exists():
                    vendedor_asignado = asignaciones.first().user_profile.user

            # 2. Empaquetar datos históricos (los inyectamos en notas por seguridad)
            vendedor_viejo = fila.get('vendedor_historico', 'Desconocido')
            fecha_vieja = fila.get('fecha_historica', 'Sin fecha')
            notas_originales = fila.get('notas', '')
            
            nota_historica_compilada = f"[CARGA HISTÓRICA] Vendedor Orig: {vendedor_viejo} | Fecha Orig: {fecha_vieja} | Notas: {notas_originales}"

            # 3. Preparar el diccionario de guardado
            # Usamos 'Histórico' como estatus por defecto para que no contamine la Fase 1
            estatus_excel = fila.get('estatus', 'Histórico') 

            # Asegurar formato de notas_variadas
            notas_historicas = {
                "notas": [],
                "columnas_excel_historicas": dict(fila)
            }
            if nota_historica_compilada:
                notas_historicas["notas"].append({
                    "tipo": "sistema",
                    "contenido": nota_historica_compilada,
                    "fecha": timezone.now().isoformat()
                })
            
            especialidad_obj, producto_obj = obtener_catalogos_limpios(fila.get('especialidad', ''), fila.get('producto', ''))

            defaults = {
                'nombre': fila.get('nombre', '')[:100],
                'email': fila.get('email', ''),
                'especialidad': especialidad_obj,
                'ubicacion_id': ubicacion_obj.id if ubicacion_obj else None,
                'direccion_completa': fila.get('direccion_completa', '')[:255],
                'producto_interes': producto_obj,
                'notas_variadas': notas_historicas,
                'estatus': estatus_excel, 
                'owner': vendedor_asignado, # El sistema hace 
            }

            # 4. Inyección a la Base de Datos (Update or Create)
            obj, created = CoreLead.objects.update_or_create(
                phone_primary=telefono[:15],
                defaults=defaults
            )
            
            if created:
                reporte["creados"] += 1
            else:
                reporte["actualizados"] += 1
                
            reporte["procesados"] += 1
            
        return JsonResponse({'status': 'success', 'reporte': reporte})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

from django.db.models import Count, Q

@login_required
@user_passes_test(es_director, login_url='dashboard_agente')
def director_dashboard_view(request):
    # --- 1. CAPTURAR FILTROS DE LA URL ---
    filtro_estado = request.GET.get('estado', '')
    filtro_especialidad = request.GET.get('especialidad', '')
    filtro_producto = request.GET.get('producto', '')
    filtro_vendedor = request.GET.get('vendedor', '')

    # --- 2. APLICAR FILTROS A LA CONSULTA BASE ---
    qs = CoreLead.objects.all()
    
    if filtro_estado:
        qs = qs.filter(ubicacion__estado__iexact=filtro_estado)
    if filtro_especialidad:
        qs = qs.filter(especialidad_cat__nombre__iexact=filtro_especialidad)
    if filtro_producto:
        qs = qs.filter(producto_cat__nombre__iexact=filtro_producto)
    if filtro_vendedor:
        qs = qs.filter(owner__username__iexact=filtro_vendedor)

    # --- 3. EXTRAER OPCIONES ÚNICAS PARA LOS DROPDOWNS ---
    lista_estados = CatUbicacion.objects.exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')
    lista_especialidades = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    lista_productos = CatProducto.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    
    lista_vendedores = User.objects.filter(is_superuser=False, is_active=True).values_list('username', flat=True).order_by('username')

    # --- 4. KPIs GLOBALES ---
    total_leads = qs.count()
    total_historicos = qs.filter(estatus='Histórico').count()
    total_vendedores_metric = lista_vendedores.count()

    hace_7_dias = timezone.now() - timedelta(days=7)
    base_semana = qs.filter(updated_at__gte=hace_7_dias).exclude(estatus='Histórico')

    total_trabajados_semana = base_semana.count()
    vendedores_activos = total_vendedores_metric
    volumen_promedio = round(total_trabajados_semana / vendedores_activos, 1) if vendedores_activos > 0 else 0

    tasa_calidad = base_semana.filter(plan__iexact='descartado').count()
    tasa_prospeccion = base_semana.filter(calificacion__in=[2, 3]).count()
    indice_venta = base_semana.filter(estatus__iexact='cliente').count()

    # --- 6. DATOS PARA GRÁFICAS MULTIDIMENSIONALES ---
    def procesar_agrupacion(query_result, campo_label):
        labels, rechazos, seguimientos, calificados, ventas = [], [], [], [], []
        for fila in query_result:
            etiqueta = fila[campo_label]
            if not etiqueta: etiqueta = 'Desconocido / Sin Asignar'
            
            labels.append(str(etiqueta))
            rechazos.append(fila['total_rechazos'])
            seguimientos.append(fila['total_seguimientos'])
            calificados.append(fila['total_calificados'])
            ventas.append(fila['total_ventas'])
        return labels, rechazos, seguimientos, calificados, ventas

    q_rechazo = Q(plan__iexact='descartado')
    q_seguimiento = Q(plan__iexact='seguimiento')
    q_calificado = Q(calificacion__in=[2, 3])
    q_venta = Q(estatus__iexact='cliente')

    stats_vendedor = qs.values('owner__username').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('owner__username')
    v_labels, v_rech, v_seg, v_cal, v_ven = procesar_agrupacion(stats_vendedor, 'owner__username')

    stats_ubicacion = qs.values('ubicacion__estado').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('ubicacion__estado')
    u_labels, u_rech, u_seg, u_cal, u_ven = procesar_agrupacion(stats_ubicacion, 'ubicacion__estado')

    stats_especialidad = qs.values('especialidad_cat__nombre').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('especialidad_cat__nombre')
    e_labels, e_rech, e_seg, e_cal, e_ven = procesar_agrupacion(stats_especialidad, 'especialidad_cat__nombre')

    # --- 7. CONTEXTO ---
    context = {
        'estados': lista_estados,
        'especialidades': lista_especialidades,
        'productos': lista_productos,
        'vendedores': lista_vendedores, # <--- ¡AQUÍ ESTÁ LA LÍNEA QUE FALTABA!
        'filtro_estado': filtro_estado,
        'filtro_especialidad': filtro_especialidad,
        'filtro_producto': filtro_producto,
        'filtro_vendedor': filtro_vendedor,
        'total_leads': total_leads,
        'total_historicos': total_historicos,
        'total_vendedores': total_vendedores_metric,
        'volumen_promedio': volumen_promedio,
        'tasa_calidad': tasa_calidad,
        'tasa_prospeccion': tasa_prospeccion,
        'indice_venta': indice_venta,
        'chart_v_labels': json.dumps(v_labels), 'chart_v_rech': json.dumps(v_rech), 'chart_v_seg': json.dumps(v_seg), 'chart_v_cal': json.dumps(v_cal), 'chart_v_ven': json.dumps(v_ven),
        'chart_u_labels': json.dumps(u_labels), 'chart_u_rech': json.dumps(u_rech), 'chart_u_seg': json.dumps(u_seg), 'chart_u_cal': json.dumps(u_cal), 'chart_u_ven': json.dumps(u_ven),
        'chart_e_labels': json.dumps(e_labels), 'chart_e_rech': json.dumps(e_rech), 'chart_e_seg': json.dumps(e_seg), 'chart_e_cal': json.dumps(e_cal), 'chart_e_ven': json.dumps(e_ven),
    }
    
    return render(request, 'director_dashboard.html', context)
    # --- 1. CAPTURAR FILTROS DE LA URL ---
    filtro_estado = request.GET.get('estado', '')
    filtro_especialidad = request.GET.get('especialidad', '')
    filtro_producto = request.GET.get('producto', '')
    filtro_vendedor = request.GET.get('vendedor', '')

    # --- 2. APLICAR FILTROS A LA CONSULTA BASE ---
    qs = CoreLead.objects.all()
    
    if filtro_estado:
        qs = qs.filter(ubicacion__estado__iexact=filtro_estado)
    if filtro_especialidad:
        # Ahora filtramos por el nombre del catálogo relacional
        qs = qs.filter(especialidad_cat__nombre__iexact=filtro_especialidad)
    if filtro_producto:
        # Ahora filtramos por el nombre del catálogo relacional
        qs = qs.filter(producto_cat__nombre__iexact=filtro_producto)
    if filtro_vendedor:
        qs = qs.filter(owner__username__iexact=filtro_vendedor)

    # --- 3. EXTRAER OPCIONES ÚNICAS PARA LOS DROPDOWNS ---
    # Ahora las listas se alimentan de los catálogos oficiales, garantizando cero duplicados
    lista_estados = CatUbicacion.objects.exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')
    lista_especialidades = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    lista_productos = CatProducto.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    
    lista_vendedores = User.objects.filter(is_superuser=False, is_active=True).values_list('username', flat=True).order_by('username')

    # --- 4. KPIs GLOBALES (Usando el qs filtrado) ---
    total_leads = qs.count()
    total_historicos = qs.filter(estatus='Histórico').count()
    total_vendedores_metric = lista_vendedores.count()

    # === KPIs SEMANALES ESTRICTOS (Últimos 7 días) ===
    hace_7_dias = timezone.now() - timedelta(days=7)
    base_semana = qs.filter(updated_at__gte=hace_7_dias).exclude(estatus='Histórico')

    total_trabajados_semana = base_semana.count()
    vendedores_activos = total_vendedores_metric
    volumen_promedio = round(total_trabajados_semana / vendedores_activos, 1) if vendedores_activos > 0 else 0

    tasa_calidad = base_semana.filter(plan__iexact='descartado').count()
    tasa_prospeccion = base_semana.filter(calificacion__in=[2, 3]).count()
    indice_venta = base_semana.filter(estatus__iexact='cliente').count()

    # --- 6. DATOS PARA GRÁFICAS MULTIDIMENSIONALES ---
    def procesar_agrupacion(query_result, campo_label):
        labels, rechazos, seguimientos, calificados, ventas = [], [], [], [], []
        for fila in query_result:
            etiqueta = fila[campo_label]
            if not etiqueta: etiqueta = 'Desconocido / Sin Asignar'
            
            labels.append(str(etiqueta))
            rechazos.append(fila['total_rechazos'])
            seguimientos.append(fila['total_seguimientos'])
            calificados.append(fila['total_calificados'])
            ventas.append(fila['total_ventas'])
        return labels, rechazos, seguimientos, calificados, ventas

    q_rechazo = Q(plan__iexact='descartado')
    q_seguimiento = Q(plan__iexact='seguimiento')
    q_calificado = Q(calificacion__in=[2, 3])
    q_venta = Q(estatus__iexact='cliente')

    # 1. Agrupación por Vendedor
    stats_vendedor = qs.values('owner__username').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('owner__username')
    v_labels, v_rech, v_seg, v_cal, v_ven = procesar_agrupacion(stats_vendedor, 'owner__username')

    # 2. Agrupación por Ubicación (Estado)
    stats_ubicacion = qs.values('ubicacion__estado').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('ubicacion__estado')
    u_labels, u_rech, u_seg, u_cal, u_ven = procesar_agrupacion(stats_ubicacion, 'ubicacion__estado')

    # 3. Agrupación por Especialidad Médica (AQUÍ ESTÁ LA MAGIA)
    stats_especialidad = qs.values('especialidad_cat__nombre').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('especialidad_cat__nombre')
    e_labels, e_rech, e_seg, e_cal, e_ven = procesar_agrupacion(stats_especialidad, 'especialidad_cat__nombre')

    # --- 7. CONTEXTO ---
    context = {
        'estados': lista_estados,
        'especialidades': lista_especialidades,
        'productos': lista_productos,
        'filtro_estado': filtro_estado,
        'filtro_especialidad': filtro_especialidad,
        'filtro_producto': filtro_producto,
        'filtro_vendedor': filtro_vendedor,
        'total_leads': total_leads,
        'total_historicos': total_historicos,
        'total_vendedores': total_vendedores_metric,
        'volumen_promedio': volumen_promedio,
        'tasa_calidad': tasa_calidad,
        'tasa_prospeccion': tasa_prospeccion,
        'indice_venta': indice_venta,
        'chart_v_labels': json.dumps(v_labels), 'chart_v_rech': json.dumps(v_rech), 'chart_v_seg': json.dumps(v_seg), 'chart_v_cal': json.dumps(v_cal), 'chart_v_ven': json.dumps(v_ven),
        'chart_u_labels': json.dumps(u_labels), 'chart_u_rech': json.dumps(u_rech), 'chart_u_seg': json.dumps(u_seg), 'chart_u_cal': json.dumps(u_cal), 'chart_u_ven': json.dumps(u_ven),
        'chart_e_labels': json.dumps(e_labels), 'chart_e_rech': json.dumps(e_rech), 'chart_e_seg': json.dumps(e_seg), 'chart_e_cal': json.dumps(e_cal), 'chart_e_ven': json.dumps(e_ven),
    }
    
    return render(request, 'director_dashboard.html', context)
    # --- 1. CAPTURAR FILTROS DE LA URL ---
    filtro_estado = request.GET.get('estado', '')
    filtro_especialidad = request.GET.get('especialidad', '')
    filtro_producto = request.GET.get('producto', '')
    filtro_vendedor = request.GET.get('vendedor', '')
    
    lista_vendedores = User.objects.filter(is_superuser=False, is_active=True).values_list('username', flat=True).order_by('username')
    # RAYOS X:
    print("\n--- VENDEDORES ENCONTRADOS ---")
    print(lista_vendedores)
    print("------------------------------\n")    

    # --- 2. APLICAR FILTROS A LA CONSULTA BASE ---
    qs = CoreLead.objects.all()
    
    if filtro_estado:
        qs = qs.filter(ubicacion__estado__iexact=filtro_estado)
    if filtro_especialidad:
        qs = qs.filter(especialidad__iexact=filtro_especialidad)
    if filtro_producto:
        qs = qs.filter(producto_interes__iexact=filtro_producto)
    if filtro_vendedor:
        # En CoreLead la fk es owner
        qs = qs.filter(owner__username__iexact=filtro_vendedor)

    # --- 3. EXTRAER OPCIONES ÚNICAS PARA LOS DROPDOWNS ---
    # Obtenemos los valores únicos de toda la BD (sin filtrar) para llenar los combos
    lista_estados = CatUbicacion.objects.exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')
    lista_especialidades = CoreLead.objects.exclude(especialidad='').values_list('especialidad', flat=True).distinct().order_by('especialidad')
    lista_productos = CoreLead.objects.exclude(producto_interes='').values_list('producto_interes', flat=True).distinct().order_by('producto_interes')
    
    # Lista de vendedores (usuarios que no son superusers y están activos)
    lista_vendedores = User.objects.filter(is_superuser=False, is_active=True).values_list('username', flat=True).order_by('username')

    # --- 4. KPIs GLOBALES (Usando el qs filtrado) ---
    total_leads = qs.count()
    total_historicos = qs.filter(estatus='Histórico').count()
    total_vendedores_metric = lista_vendedores.count()

    # === KPIs SEMANALES ESTRICTOS (Últimos 7 días) ===
    hace_7_dias = timezone.now() - timedelta(days=7)

    # 1. BASE: Todo lo que tuvo movimiento de trabajo esta semana
    base_semana = qs.filter(updated_at__gte=hace_7_dias).exclude(estatus='Histórico')

    # KPI 1: Volumen de trabajo (Promedio de leads tocados por ejecutivo en la semana)
    total_trabajados_semana = base_semana.count()
    vendedores_activos = total_vendedores_metric
    volumen_promedio = round(total_trabajados_semana / vendedores_activos, 1) if vendedores_activos > 0 else 0

    # KPI 2: Tasa de calidad (Número de Leads descartados)
    # Regla: plan = 'descartado'
    tasa_calidad = base_semana.filter(plan__iexact='descartado').count()

    # KPI 3: Tasa de prospección (Posibilidad de venta)
    # Regla: calificacion en ['media', 'alta'] -> mapeado a [2, 3] en DB
    tasa_prospeccion = base_semana.filter(calificacion__in=[2, 3]).count()

    # KPI 4: Índice de Venta (Ventas realizadas)
    # Regla: estatus = 'cliente'
    indice_venta = base_semana.filter(estatus__iexact='cliente').count()

    # --- 6. DATOS PARA GRÁFICAS MULTIDIMENSIONALES ---
    
    # Función auxiliar para extraer listas de Chart.js
    def procesar_agrupacion(query_result, campo_label):
        labels = []
        rechazos, seguimientos, calificados, ventas = [], [], [], []
        for fila in query_result:
            # Manejo de nulos o vacíos
            etiqueta = fila[campo_label]
            if not etiqueta: etiqueta = 'Desconocido / Sin Asignar'
            
            labels.append(str(etiqueta))
            rechazos.append(fila['total_rechazos'])
            seguimientos.append(fila['total_seguimientos'])
            calificados.append(fila['total_calificados'])
            ventas.append(fila['total_ventas'])
        return labels, rechazos, seguimientos, calificados, ventas

    # Condiciones de negocio exactas
    q_rechazo = Q(plan__iexact='descartado')
    q_seguimiento = Q(plan__iexact='seguimiento')
    q_calificado = Q(calificacion__in=[2, 3])
    q_venta = Q(estatus__iexact='cliente')

    # 1. Agrupación por Vendedor
    stats_vendedor = qs.values('owner__username').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('owner__username')
    v_labels, v_rech, v_seg, v_cal, v_ven = procesar_agrupacion(stats_vendedor, 'owner__username')

    # 2. Agrupación por Ubicación (Estado)
    stats_ubicacion = qs.values('ubicacion__estado').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('ubicacion__estado')
    u_labels, u_rech, u_seg, u_cal, u_ven = procesar_agrupacion(stats_ubicacion, 'ubicacion__estado')

    # 3. Agrupación por Especialidad Médica
    stats_especialidad = qs.values('especialidad').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta)
    ).order_by('especialidad')
    e_labels, e_rech, e_seg, e_cal, e_ven = procesar_agrupacion(stats_especialidad, 'especialidad')

    # --- 7. CONTEXTO ---
    context = {
        # Listas para pintar los selects
        'estados': lista_estados,
        'especialidades': lista_especialidades,
        'productos': lista_productos,
        'vendedores': lista_vendedores,
        
        # Valores seleccionados actualmente para dejarlos marcados
        'filtro_estado': filtro_estado,
        'filtro_especialidad': filtro_especialidad,
        'filtro_producto': filtro_producto,
        'filtro_vendedor': filtro_vendedor,

        # Métricas Globales
        'total_leads': total_leads,
        'total_historicos': total_historicos,
        'total_vendedores': total_vendedores_metric,
        
        # Métricas Semanales
        'volumen_promedio': volumen_promedio,
        'tasa_calidad': tasa_calidad,
        'tasa_prospeccion': tasa_prospeccion,
        'indice_venta': indice_venta,

        # Gráficas JSON
        'chart_v_labels': json.dumps(v_labels), 'chart_v_rech': json.dumps(v_rech), 'chart_v_seg': json.dumps(v_seg), 'chart_v_cal': json.dumps(v_cal), 'chart_v_ven': json.dumps(v_ven),
        'chart_u_labels': json.dumps(u_labels), 'chart_u_rech': json.dumps(u_rech), 'chart_u_seg': json.dumps(u_seg), 'chart_u_cal': json.dumps(u_cal), 'chart_u_ven': json.dumps(u_ven),
        'chart_e_labels': json.dumps(e_labels), 'chart_e_rech': json.dumps(e_rech), 'chart_e_seg': json.dumps(e_seg), 'chart_e_cal': json.dumps(e_cal), 'chart_e_ven': json.dumps(e_ven),
    }
    
    return render(request, 'director_dashboard.html', context)

def marcar_alerta_leida(request, alerta_id):
    # Buscamos la alerta asegurándonos de que pertenezca a este usuario
    alerta = get_object_or_404(Notificacion, id=alerta_id, usuario=request.user)
    
    # La apagamos
    alerta.leida = True
    alerta.save()
    
    # Si la alerta está ligada a un prospecto, llevamos al vendedor a ese perfil
    if alerta.lead:
        # OJO: Cambia 'detalle_lead' por el nombre real de tu URL para ver un lead
        return redirect('detalle_lead', pk=alerta.lead.id) 
    
    # Si es una alerta general, lo regresamos al dashboard
    return redirect('dashboard_agente')