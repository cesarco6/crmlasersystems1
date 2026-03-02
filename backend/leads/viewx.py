# leads/views.py
import json
import unicodedata
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

User = get_user_model()

from users.permissions import role_required
from users.models import CatUbicacion, CatEspecialidad, CatProducto
from .mixins import LeadOwnershipMixin
from .models import CoreLead, Notificacion, VentaTransaccional, Evento

# ==========================================
# FUNCIONES AUXILIARES Y DE LIMPIEZA
# ==========================================

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def obtener_catalogos_limpios(texto_especialidad, texto_producto):
    """Versión Estricta DDS 2.0: Solo lee, NUNCA crea."""
    producto_obj = CatProducto.objects.filter(nombre__iexact=str(texto_producto).strip()).first()
    if not producto_obj:
        producto_obj = CatProducto.objects.filter(nombre__icontains='Por Definir').first()

    especialidad_obj = CatEspecialidad.objects.filter(nombre__iexact=str(texto_especialidad).strip()).first()
    if not especialidad_obj:
        especialidad_obj = CatEspecialidad.objects.filter(nombre__icontains='General').first()

    return especialidad_obj, producto_obj

def es_director(user):
    return user.is_superuser

# ==========================================
# VISTAS DE VENDEDOR
# ==========================================

@method_decorator(role_required(['VENDEDOR']), name='dispatch')
class DashboardAgenteView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'dashboard_agente.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        busqueda = self.request.GET.get('q', '').strip()
        filtro_rapido = self.request.GET.get('filtro', 'activos')
        hoy = timezone.now().date()

        qs = CoreLead.objects.filter(owner=self.request.user)

        if busqueda:
            qs = qs.filter(
                Q(nombre__icontains=busqueda) |
                Q(phone_primary__icontains=busqueda) |
                Q(celular__icontains=busqueda) |
                Q(email__icontains=busqueda)
            )
        else:
            qs = qs.exclude(estatus__in=['CLIENTE', 'NO_CIERRE']).exclude(plan='DESCARTADO')
            qs = qs.exclude(Q(plan='EN_ESPERA') & Q(next_action_date__gt=hoy))

            if filtro_rapido == 'hoy':
                qs = qs.filter(next_action_date=hoy)
            elif filtro_rapido == 'frescos':
                qs = qs.filter(estatus='PROSPECTO')
            elif filtro_rapido == 'urgentes':
                qs = qs.filter(plan='SEGUIMIENTO', next_action_date__lt=hoy)
        
        qs = qs.order_by('-updated_at')

        paginador = Paginator(qs, 10) 
        numero_pagina = self.request.GET.get('page')
        pagina_obj = paginador.get_page(numero_pagina)

        context['leads'] = pagina_obj 
        context['page_obj'] = pagina_obj 
        context['busqueda_actual'] = busqueda
        context['filtro_actual'] = filtro_rapido
        
        context['total_activos'] = CoreLead.objects.filter(owner=self.request.user).exclude(estatus__in=['CLIENTE', 'NO_CIERRE']).exclude(plan='DESCARTADO').count()
        context['especialidades_list'] = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
        context['productos_list'] = CatProducto.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
      
        return context

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class AltaIndividualView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'alta_individual.html'

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class FichaTrabajoView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'ficha_trabajo.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead_id = self.kwargs.get('pk') or self.kwargs.get('id')
        lead = get_object_or_404(CoreLead, id=lead_id)
        
        context['lead'] = lead
        context['especialidades_list'] = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
        context['productos_list'] = CatProducto.objects.filter(is_active=True).order_by('nombre')
        context['celular_seguro'] = lead.celular if lead.celular else "No registrado"
        context['especialidad_segura'] = lead.especialidad_cat.nombre if lead.especialidad_cat else (lead.especialidad if lead.especialidad else "No especificada")
        context['producto_seguro'] = lead.producto_cat.nombre if lead.producto_cat else (lead.producto_interes if lead.producto_interes else "No especificado")
        
        return context

# ==========================================
# APIS DE VENDEDOR / OPERACIÓN
# ==========================================

@login_required
@require_POST
def procesar_alta_manual(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)
    
    try:
        data = json.loads(request.body)
        
        telefono = str(data.get('telefono', '')).strip()
        celular = str(data.get('celular', '')).strip()
        email = str(data.get('email', '')).strip()
        nombre = str(data.get('nombre', '')).strip()
        especialidad = str(data.get('especialidad', 'No especificada')).strip()
        valor_ubicacion = str(data.get('ubicacion', 'Desconocida')).strip()
        
        if not telefono or not nombre:
            return JsonResponse({"error": "El nombre y teléfono son obligatorios."}, status=400)
            
        if CoreLead.objects.filter(phone_primary=telefono[:15]).exists():
            return JsonResponse({"error": "Ya existe un registro con este Teléfono Primario en el sistema."}, status=400)

        ubicacion_obj, created = CatUbicacion.objects.get_or_create(
            ciudad=valor_ubicacion, 
            defaults={'estado': valor_ubicacion, 'is_active': True}
        )
        
        # Validación estricta usando nuestra función limpia
        esp_obj, prod_obj = obtener_catalogos_limpios(especialidad, 'Por Definir / Otro')

        nuevo_lead = CoreLead.objects.create(
            owner=request.user,
            ubicacion_id=ubicacion_obj.id,
            especialidad_cat=esp_obj,
            producto_cat=prod_obj,
            estatus='PROSPECTO',
            phone_primary=telefono[:15],
            celular=celular[:15],
            email=email,
            nombre=nombre[:100],
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
        
        if accion == 'DESECHAR':
            if lead.estatus == 'PROSPECTO':
                lead.delete() 
                return JsonResponse({"status": "deleted", "mensaje": "Prospecto desechado y eliminado de la base de datos."})
            else:
                return JsonResponse({"error": "Solo puedes desechar prospectos en Fase 1."}, status=400)

        lead.celular = data.get('celular', lead.celular)
        lead.email = data.get('email', lead.email)
        lead.direccion_completa = data.get('direccion', lead.direccion_completa)
        
        if lead.estatus == 'PROSPECTO':
            lead.nombre = data.get('nombre', lead.nombre)
            lead.phone_primary = data.get('telefono', lead.phone_primary)
            
            nueva_esp_str = data.get('especialidad', '').strip()
            if nueva_esp_str:
                esp_obj = CatEspecialidad.objects.filter(nombre__iexact=nueva_esp_str).first()
                if esp_obj: lead.especialidad_cat = esp_obj
                else: return JsonResponse({"error": f"La especialidad '{nueva_esp_str}' no existe."}, status=400)
            
            nuevo_prod_str = data.get('producto', '').strip()
            if nuevo_prod_str:
                prod_obj = CatProducto.objects.filter(nombre__iexact=nuevo_prod_str).first()
                if prod_obj: lead.producto_cat = prod_obj
                else: return JsonResponse({"error": f"El producto '{nuevo_prod_str}' no existe."}, status=400)
        
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
            mapa = {'Alta': 3, 'Media': 2, 'Baja': 1}
            
            if texto_calificacion in mapa:
                lead.calificacion = mapa[texto_calificacion]
                lead.notas_variadas.setdefault("notas", []).append({
                    "tipo": "sistema",
                    "contenido": f"Lead calificado como: {texto_calificacion}",
                    "fecha": timezone.now().isoformat()
                })
            else:
                return JsonResponse({"error": "Calificación inválida."}, status=400)

        elif accion == 'AGENDAR':
            fecha_contacto_str = data.get('fecha_contacto')
            if not fecha_contacto_str:
                return JsonResponse({"error": "La fecha es obligatoria."}, status=400)
            
            fecha_contacto = datetime.strptime(fecha_contacto_str, '%Y-%m-%d').date()
            hoy = timezone.now().date()
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
                "fecha": timezone.now().isoformat()
            })
            
        elif accion == 'AGREGAR_NOTA':
            nueva_nota = data.get('nota')
            if not nueva_nota:
                return JsonResponse({"error": "La nota no puede estar vacía."}, status=400)
            
            lead.notas_variadas.setdefault("notas", []).append({
                "tipo": "contacto",
                "contenido": nueva_nota.strip(),
                "fecha": timezone.now().isoformat()
            })
            
        elif accion == 'CERRAR_VENTA':
            lead.estatus = 'CLIENTE'
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            
            if not isinstance(lead.notas_variadas, dict):
                lead.notas_variadas = {"notas": []}
            if "notas" not in lead.notas_variadas:
                lead.notas_variadas["notas"] = []
                
            lead.notas_variadas["notas"].append({
                "fecha": timestamp,
                "tipo": "sistema",
                "contenido": "🏆 ¡VENTA CERRADA! El prospecto ha cruzado la meta y se ha convertido oficialmente en CLIENTE."
            })

        # GUARDADO FINAL ÚNICO
        lead.save()
        
        return JsonResponse({
            "status": "success", 
            "mensaje": f"Operación {accion} realizada con éxito.",
            "nuevo_estatus": lead.estatus
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_POST
def registrar_venta_extra(request):
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        producto_id = data.get('producto_id')
        monto = data.get('monto')
        notas = data.get('notas', '')
        estatus = data.get('estatus', 'PENDIENTE') 

        if not lead_id or not producto_id:
            return JsonResponse({"error": "Faltan datos obligatorios (lead_id, producto_id)."}, status=400)
        
        lead = get_object_or_404(CoreLead, id=lead_id)
        
        if lead.estatus != 'CLIENTE':
            return JsonResponse({"error": "Solo puedes registrar ventas transaccionales a prospectos con estatus de CLIENTE."}, status=400)

        producto = get_object_or_404(CatProducto, id=producto_id)

        if VentaTransaccional.objects.filter(lead=lead, producto=producto, estatus__in=['PENDIENTE', 'EN_GESTION']).exists():
            return JsonResponse({"error": "Ya existe una oportunidad activa (Pendiente o En Gestión) para este producto."}, status=400)

        nueva_venta = VentaTransaccional.objects.create(
            lead=lead,
            producto=producto,
            vendedor=request.user,
            estatus=estatus, 
            monto=monto if monto else None,
            notas=notas
        )

        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        nueva_nota = {
            "fecha": timestamp,
            "tipo": "sistema",
            "contenido": f"🎯 Oportunidad 360° creada: {producto.nombre} (Estatus: {estatus}).\n📝 Notas: {notas}"
        }

        if not isinstance(lead.notas_variadas, dict):
            lead.notas_variadas = {"notas": []}
        if "notas" not in lead.notas_variadas:
            lead.notas_variadas["notas"] = []
            
        lead.notas_variadas["notas"].append(nueva_nota)
        lead.save(update_fields=['notas_variadas'])

        return JsonResponse({
            "status": "success",
            "mensaje": "Venta transaccional registrada exitosamente.",
            "venta_id": str(nueva_venta.id)
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON Inválido enviado en la petición."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def marcar_alerta_leida(request, alerta_id):
    alerta = get_object_or_404(Notificacion, id=alerta_id, usuario=request.user)
    alerta.leida = True
    alerta.save()
    
    if alerta.lead:
        return redirect('detalle_lead', pk=alerta.lead.id) 
    
    return redirect('dashboard_agente')

# ==========================================
# VISTAS DE DIRECTOR (INGESTAS Y DASHBOARD)
# ==========================================

@method_decorator(role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaMasivaView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'ingesta_masiva.html'

@method_decorator(role_required(['DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaHistoricaView(LoginRequiredMixin, TemplateView):
    template_name = 'director_ingesta.html'

@login_required
@require_POST
def procesar_ingesta_masiva(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)
    
    try:
        data = json.loads(request.body)
        reporte = {'A': [], 'B': [], 'C': [], 'D': []}
        ubicaciones_db = CatUbicacion.objects.all()
        mapa_ciudades = {normalizar_texto(u.ciudad): u for u in ubicaciones_db}

        for lead_data in data:
            if not isinstance(lead_data, dict):
                continue
            
            telefono = str(lead_data.get('telefono', '')).strip()
            if not telefono: continue 
                
            nombre_raw = str(lead_data.get('nombre', 'Sin Nombre')).strip()
            nombre_norm = nombre_raw.lower().replace('dr.', '').replace('dr ', '').replace('dra.', '').replace('dra ', '').strip()
            especialidad = str(lead_data.get('especialidad', 'General')).strip()
            producto_interes = str(lead_data.get('producto', 'No especificado')).strip()
            
            ciudad_excel = lead_data.get('ubicacion', '')
            ciudad_norm = normalizar_texto(ciudad_excel)
            
            if not ciudad_norm:
                reporte["D"].append({"fila": lead_data, "motivo": "El campo de ubicación/ciudad viene vacío."})
                continue
                
            ubicacion_obj = mapa_ciudades.get(ciudad_norm)
            if not ubicacion_obj:
                reporte["D"].append({"fila": lead_data, "motivo": f"Ciudad no reconocida: '{ciudad_excel}'."})
                continue 

            val_direccion = str(lead_data.get('direccion_completa', '')).strip()
            val_celular = str(lead_data.get('celular', '')).strip()
            val_email = str(lead_data.get('email', '')).strip()
            notas_variadas_val = str(lead_data.get('notas', '')).strip()

            notas_json = {"notas": [], "columnas_excel_historicas": {}}

            if notas_variadas_val:
                notas_json["notas"].append({
                    "tipo": "contacto",
                    "contenido": notas_variadas_val,
                    "fecha": timezone.now().isoformat()
                })

            esp_obj, prod_obj = obtener_catalogos_limpios(especialidad, producto_interes)

            lead_existente = CoreLead.objects.filter(phone_primary=telefono[:15]).first()
            
            if not lead_existente:
                nuevo_lead = CoreLead.objects.create(
                    owner=request.user,
                    ubicacion_id=ubicacion_obj.id,
                    estatus='PROSPECTO', 
                    phone_primary=telefono[:15],
                    celular=val_celular[:15],
                    email=val_email,
                    direccion_completa=val_direccion[:255],
                    nombre=nombre_raw[:100],                   
                    especialidad_cat=esp_obj,   
                    producto_cat=prod_obj,      
                    notas_variadas=notas_json,
                )
                reporte['A'].append(telefono[:15])

            elif lead_existente.nombre.lower().replace('dr.', '').replace('dr ', '').replace('dra.', '').replace('dra ', '').strip() != nombre_norm:
                nuevo_lead = CoreLead.objects.create(
                    owner=request.user,
                    ubicacion_id=ubicacion_obj.id,
                    estatus='PROSPECTO', 
                    phone_primary=telefono[:15],
                    celular=val_celular[:15],
                    email=val_email,
                    direccion_completa=val_direccion[:255],
                    nombre=nombre_raw[:100],
                    especialidad_cat=esp_obj,   
                    producto_cat=prod_obj,      
                    notas_variadas=notas_json
                )
                reporte['A'].append(f"{telefono[:15]} (Nueva Persona)")

            else:
                if lead_existente.estatus == 'CLIENTE':
                    lead_existente.notas_variadas.setdefault("notas", []).append({
                        "tipo": "sistema",
                        "contenido": f"Intento de re-ingesta masiva bloqueado el {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                        "fecha": timezone.now().isoformat()
                    })
                    lead_existente.save(update_fields=['notas_variadas', 'updated_at'])
                    reporte['C'].append(nombre_raw)
                elif lead_existente.estatus == 'NO_CIERRE' and timezone.now() - lead_existente.updated_at > timedelta(days=365):
                    reporte['D'].append(nombre_raw)
                else:
                    reporte['B'].append(nombre_raw)

        return JsonResponse({'status': 'success', 'reporte': reporte})

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON Inválido enviado en la petición."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
@user_passes_test(es_director)
@require_POST
def api_ingesta_historica(request):
    try:
        data = json.loads(request.body)
        filas = data.get('datos', [])
        reporte = {"procesados": 0, "creados": 0, "actualizados": 0, "errores": []}
        mapa_ciudades = {normalizar_texto(u.ciudad): u for u in CatUbicacion.objects.all()}
        
        for index, fila in enumerate(filas):
            telefono = str(fila.get('telefono', '')).strip()
            if not telefono:
                reporte["errores"].append(f"Fila {index + 1}: Sin teléfono. Ignorada.")
                continue
            
            ciudad_excel = fila.get('ubicacion', '')
            ubicacion_obj = mapa_ciudades.get(normalizar_texto(ciudad_excel))
            vendedor_asignado = request.user 
            
            if ubicacion_obj:
                asignaciones = ubicacion_obj.asignacionterritorio_set.select_related('user_profile__user').all()
                if asignaciones.exists():
                    vendedor_asignado = asignaciones.first().user_profile.user

            vendedor_viejo = fila.get('vendedor_historico', 'Desconocido')
            fecha_vieja = fila.get('fecha_historica', 'Sin fecha')
            notas_originales = fila.get('notas', '')
            nota_historica_compilada = f"[CARGA HISTÓRICA] Vendedor Orig: {vendedor_viejo} | Fecha Orig: {fecha_vieja} | Notas: {notas_originales}"

            estatus_excel = fila.get('estatus', 'Histórico') 
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
                'especialidad_cat': especialidad_obj,
                'ubicacion_id': ubicacion_obj.id if ubicacion_obj else None,
                'direccion_completa': fila.get('direccion_completa', '')[:255],
                'producto_cat': producto_obj,
                'notas_variadas': notas_historicas,
                'estatus': estatus_excel, 
                'owner': vendedor_asignado, 
            }

            obj, created = CoreLead.objects.update_or_create(
                phone_primary=telefono[:15],
                defaults=defaults
            )
            
            if created: reporte["creados"] += 1
            else: reporte["actualizados"] += 1
            reporte["procesados"] += 1
            
        return JsonResponse({'status': 'success', 'reporte': reporte})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@user_passes_test(es_director, login_url='dashboard_agente')
def director_dashboard_view(request):
    filtro_estado = request.GET.get('estado', '')
    filtro_especialidad = request.GET.get('especialidad', '')
    filtro_producto = request.GET.get('producto', '')
    filtro_vendedor = request.GET.get('vendedor', '')

    qs = CoreLead.objects.all()
    
    if filtro_estado:
        qs = qs.filter(ubicacion__estado__iexact=filtro_estado)
    if filtro_especialidad:
        qs = qs.filter(especialidad_cat__nombre__iexact=filtro_especialidad)
    if filtro_producto:
        qs = qs.filter(producto_cat__nombre__iexact=filtro_producto)
    if filtro_vendedor:
        qs = qs.filter(owner__username__iexact=filtro_vendedor)

    lista_estados = CatUbicacion.objects.exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')
    lista_especialidades = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    lista_productos = CatProducto.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    lista_vendedores = User.objects.filter(is_superuser=False, is_active=True).values_list('username', flat=True).order_by('username')

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

    import datetime
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    if inicio_mes.month == 12:
        fin_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1) - datetime.timedelta(days=1)
    else:
        fin_mes = inicio_mes.replace(month=inicio_mes.month + 1, day=1) - datetime.timedelta(days=1)

    forecast_leads = qs.filter(
        calificacion__in=[2, 3],
        next_action_date__gte=inicio_mes,
        next_action_date__lte=fin_mes
    ).exclude(
        estatus__in=['CLIENTE', 'Histórico']
    ).exclude(
        plan='DESCARTADO'
    ).select_related('owner', 'especialidad_cat', 'producto_cat').order_by('next_action_date')

    dona_prospectos = qs.filter(estatus='PROSPECTO').count()
    dona_leads_frios = qs.filter(estatus='LEAD').exclude(calificacion__in=[2, 3]).count()
    dona_calificados = qs.filter(estatus='LEAD', calificacion__in=[2, 3]).count()
    dona_clientes = qs.filter(estatus='CLIENTE').count()
    dona_data = [dona_prospectos, dona_leads_frios, dona_calificados, dona_clientes]

    context = {
        'forecast_leads': forecast_leads,
        'estados': lista_estados,
        'especialidades': lista_especialidades,
        'productos': lista_productos,
        'vendedores': lista_vendedores, 
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
        'dona_data': dona_data,
        'chart_v_labels': json.dumps(v_labels), 'chart_v_rech': json.dumps(v_rech), 'chart_v_seg': json.dumps(v_seg), 'chart_v_cal': json.dumps(v_cal), 'chart_v_ven': json.dumps(v_ven),
        'chart_u_labels': json.dumps(u_labels), 'chart_u_rech': json.dumps(u_rech), 'chart_u_seg': json.dumps(u_seg), 'chart_u_cal': json.dumps(u_cal), 'chart_u_ven': json.dumps(u_ven),
        'chart_e_labels': json.dumps(e_labels), 'chart_e_rech': json.dumps(e_rech), 'chart_e_seg': json.dumps(e_seg), 'chart_e_cal': json.dumps(e_cal), 'chart_e_ven': json.dumps(e_ven),
    }
    
    return render(request, 'director_dashboard.html', context)

# ==========================================
# VISTAS DE DIRECTOR (RESCATE Y BÚSQUEDA)
# ==========================================

@login_required
def bandeja_rescate_view(request):
    if not request.user.is_superuser:
        return render(request, '403.html')
    
    leads = CoreLead.objects.filter(
        Q(estatus='EN_ESPERA') | Q(plan__iexact='descartado')
    ).select_related('owner', 'especialidad_cat', 'producto_cat')
    
    vendedores = User.objects.filter(is_active=True, is_superuser=False)
    
    context = {
        'leads': leads,
        'vendedores': vendedores
    }
    return render(request, 'director_rescate.html', context)

@login_required
@require_POST
def api_reasignar_lead(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
        
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        nuevo_vendedor_id = data.get('nuevo_vendedor_id')
        
        lead = CoreLead.objects.get(id=lead_id)
        nuevo_vendedor = User.objects.get(id=nuevo_vendedor_id)
        
        lead.owner = nuevo_vendedor
        lead.estatus = 'LEAD'
        lead.plan = 'SEGUIMIENTO'
        lead.save()
        
        return JsonResponse({'success': True, 'message': 'Reasignado con éxito'})
        
    except CoreLead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead no encontrado'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vendedor no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def api_desechar_lead(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
        
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        
        lead = CoreLead.objects.get(id=lead_id)
        lead.plan = 'ARCHIVO_MUERTO'
        lead.save()
        
        return JsonResponse({'success': True, 'message': 'Lead desechado al archivo muerto'})
        
    except CoreLead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def director_busqueda_view(request):
    if not request.user.is_superuser:
        return render(request, '403.html')
        
    q = request.GET.get('q', '').strip()
    leads = None
    
    if q:
        leads = CoreLead.objects.filter(
            Q(nombre__icontains=q) |
            Q(phone_primary__icontains=q) |
            Q(celular__icontains=q) |
            Q(email__icontains=q)
        ).select_related('owner', 'especialidad_cat', 'producto_cat')
    
    context = {
        'leads': leads,
        'q': q
    }
    
    return render(request, 'director_busqueda.html', context)

@login_required
def director_directorio_view(request):
    if not request.user.is_superuser:
        return render(request, '403.html')
        
    q = request.GET.get('q', '').strip()
    vendedor_id = request.GET.get('vendedor_id', '')
    estatus = request.GET.get('estatus', '')
    calificacion = request.GET.get('calificacion', '')
    
    leads = CoreLead.objects.all().select_related('owner', 'especialidad_cat', 'producto_cat')
    
    if q:
        leads = leads.filter(
            Q(nombre__icontains=q) |
            Q(phone_primary__icontains=q)
        )
    if vendedor_id:
        leads = leads.filter(owner_id=vendedor_id)
    if estatus:
        leads = leads.filter(estatus=estatus)
    if calificacion:
        leads = leads.filter(calificacion=int(calificacion))
        
    leads = leads.order_by('-created_at')
    
    paginator = Paginator(leads, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    vendedores = User.objects.filter(is_active=True, is_superuser=False)
    estatus_unicos = CoreLead.objects.values_list('estatus', flat=True).distinct().order_by('estatus')
    
    context = {
        'page_obj': page_obj,
        'q': q,
        'vendedor_id': vendedor_id,
        'estatus_filtro': estatus,
        'calificacion': calificacion,
        'vendedores': vendedores,
        'estatus_unicos': estatus_unicos,
    }
    
    return render(request, 'director_directorio.html', context)

# ==========================================
# VISTAS DE DIRECTOR (EVENTOS Y CAMPAÑAS)
# ==========================================

@login_required
def director_eventos_view(request):
    if not request.user.is_superuser:
        return render(request, '403.html')
        
    eventos = Evento.objects.prefetch_related('vendedores_asignados').order_by('-fecha_inicio')
    vendedores = User.objects.filter(is_active=True, is_superuser=False).order_by('username')
    
    context = {
        'eventos': eventos,
        'vendedores': vendedores,
    }
    return render(request, 'director_eventos.html', context)

@login_required
@require_POST
def api_crear_evento(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)
        
    try:
        data = json.loads(request.body)
        
        nombre = data.get('nombre')
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        lugar = data.get('lugar')
        tipo = data.get('tipo', 'EXPO') # Capturamos si es EXPO o TALLER
        
        if not all([nombre, fecha_inicio, fecha_fin, lugar]):
             return JsonResponse({'success': False, 'error': 'Revisa los campos obligatorios.'}, status=400)
             
        vendedores_ids = data.get('vendedores_ids', [])
        
        nuevo_evento = Evento.objects.create(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            lugar=lugar,
            tipo=tipo
        )
        
        if vendedores_ids:
            nuevo_evento.vendedores_asignados.set(vendedores_ids)
            
        return JsonResponse({'success': True, 'message': 'Evento creado correctamente.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)