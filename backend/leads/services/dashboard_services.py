# leads/services/dashboard_services.py
import json
import datetime
from django.db.models import Count, Q
from django.utils.timezone import localtime, now
from datetime import timedelta
from django.contrib.auth import get_user_model

from leads.models import CoreLead
from users.models import CatUbicacion, CatEspecialidad, CatProducto

User = get_user_model()

def obtener_metricas_director(filtros: dict) -> dict:
    # --- 1. CAPTURAR FILTROS ---
    filtro_estado = filtros.get('estado', '')
    filtro_especialidad = filtros.get('especialidad', '')
    filtro_producto = filtros.get('producto', '')
    filtro_vendedor = filtros.get('vendedor', '')

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

    qs_organico = qs.exclude(es_historico=True)

    # --- 3. EXTRAER OPCIONES ÚNICAS (DDS 2.0) ---
    lista_estados = CatUbicacion.objects.exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')
    lista_especialidades = CatEspecialidad.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    lista_productos = CatProducto.objects.filter(is_active=True).values_list('nombre', flat=True).order_by('nombre')
    lista_vendedores = User.objects.filter(is_superuser=False, is_active=True).values_list('username', flat=True).order_by('username')

    # --- 4. KPIs GLOBALES ---
    total_leads = qs.count()
    total_historicos = qs.filter(es_historico=True).count()
    total_vendedores_metric = lista_vendedores.count()

    hace_7_dias = localtime(now()) - timedelta(days=7)
    base_semana = qs_organico.filter(updated_at__gte=hace_7_dias).exclude(estatus='Histórico')

    total_trabajados_semana = base_semana.count()
    vendedores_activos = total_vendedores_metric
    volumen_promedio = round(total_trabajados_semana / vendedores_activos, 1) if vendedores_activos > 0 else 0

    tasa_calidad = base_semana.filter(plan__iexact='descartado').count()
    tasa_prospeccion = base_semana.filter(calificacion__in=[2, 3]).count()
    indice_venta = base_semana.filter(estatus__iexact='cliente').count()
    tasa_no_cierre = base_semana.filter(estatus__iexact='NO_CIERRE').count()

    # --- 5. DATOS PARA GRÁFICAS MULTIDIMENSIONALES ---
    def procesar_agrupacion(query_result, campo_label):
        labels, rechazos, seguimientos, calificados, ventas, no_cierres = [], [], [], [], [], []
        for fila in query_result:
            etiqueta = fila[campo_label]
            if not etiqueta: etiqueta = 'Desconocido / Sin Asignar'
            
            labels.append(str(etiqueta))
            rechazos.append(fila['total_rechazos'])
            seguimientos.append(fila['total_seguimientos'])
            calificados.append(fila['total_calificados'])
            ventas.append(fila['total_ventas'])
            no_cierres.append(fila['total_no_cierres'])
        return labels, rechazos, seguimientos, calificados, ventas, no_cierres

    q_rechazo = Q(plan__iexact='descartado')
    q_seguimiento = Q(plan__iexact='seguimiento')
    q_calificado = Q(calificacion__in=[2, 3])
    q_venta = Q(estatus__iexact='cliente')
    q_no_cierre = Q(estatus__iexact='NO_CIERRE')

    stats_vendedor = qs_organico.values('owner__username').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta),
        total_no_cierres=Count('id', filter=q_no_cierre)
    ).order_by('owner__username')
    v_labels, v_rech, v_seg, v_cal, v_ven, v_noc = procesar_agrupacion(stats_vendedor, 'owner__username')

    stats_ubicacion = qs_organico.values('ubicacion__estado').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta),
        total_no_cierres=Count('id', filter=q_no_cierre)
    ).order_by('ubicacion__estado')
    u_labels, u_rech, u_seg, u_cal, u_ven, u_noc = procesar_agrupacion(stats_ubicacion, 'ubicacion__estado')

    stats_especialidad = qs_organico.values('especialidad_cat__nombre').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta),
        total_no_cierres=Count('id', filter=q_no_cierre)
    ).order_by('especialidad_cat__nombre')
    e_labels, e_rech, e_seg, e_cal, e_ven, e_noc = procesar_agrupacion(stats_especialidad, 'especialidad_cat__nombre')

    # --- 6. FORECAST MENSUAL ---
    hoy = localtime(now()).date()
    inicio_mes = hoy.replace(day=1)
    
    if inicio_mes.month == 12:
        fin_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1) - datetime.timedelta(days=1)
    else:
        fin_mes = inicio_mes.replace(month=inicio_mes.month + 1, day=1) - datetime.timedelta(days=1)

    forecast_leads = qs_organico.filter(
        calificacion__in=[2, 3],
        next_action_date__gte=inicio_mes,
        next_action_date__lte=fin_mes
    ).exclude(
        estatus__in=['CLIENTE', 'Histórico']
    ).exclude(
        plan='DESCARTADO'
    ).select_related('owner', 'especialidad_cat', 'producto_cat').order_by('next_action_date')

    # --- 7. EMBUDO DE CONVERSIÓN (DONA) ---
    dona_prospectos = qs_organico.filter(estatus='PROSPECTO').count()
    dona_leads_frios = qs_organico.filter(estatus='LEAD').exclude(calificacion__in=[2, 3]).count()
    dona_calificados = qs_organico.filter(estatus='LEAD', calificacion__in=[2, 3]).count()
    dona_clientes = qs_organico.filter(estatus='CLIENTE').count()
    
    dona_data = [dona_prospectos, dona_leads_frios, dona_calificados, dona_clientes]

    # --- 8. RETORNAR CONTEXTO AL CONTROLADOR ---
    return {
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
        'tasa_no_cierre': tasa_no_cierre,
        'dona_data': dona_data,
        'chart_v_labels': json.dumps(v_labels), 'chart_v_rech': json.dumps(v_rech), 'chart_v_seg': json.dumps(v_seg), 'chart_v_cal': json.dumps(v_cal), 'chart_v_ven': json.dumps(v_ven), 'chart_v_noc': json.dumps(v_noc),
        'chart_u_labels': json.dumps(u_labels), 'chart_u_rech': json.dumps(u_rech), 'chart_u_seg': json.dumps(u_seg), 'chart_u_cal': json.dumps(u_cal), 'chart_u_ven': json.dumps(u_ven), 'chart_u_noc': json.dumps(u_noc),
        'chart_e_labels': json.dumps(e_labels), 'chart_e_rech': json.dumps(e_rech), 'chart_e_seg': json.dumps(e_seg), 'chart_e_cal': json.dumps(e_cal), 'chart_e_ven': json.dumps(e_ven), 'chart_e_noc': json.dumps(e_noc),
    }