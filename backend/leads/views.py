# leads/views.py
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
from users.models import CatUbicacion, CatEspecialidad, CatProducto, CatTitulo
from django.utils.timezone import localtime, now

@method_decorator(role_required(['VENDEDOR']), name='dispatch')
class DashboardAgenteView(LoginRequiredMixin, LeadOwnershipMixin, TemplateView):
    template_name = 'dashboard_agente.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. CAPTURAR LO QUE EL VENDEDOR QUIERE VER
        busqueda = self.request.GET.get('q', '').strip()
        filtro_rapido = self.request.GET.get('filtro', 'activos') # 'activos' por defecto
        
        #hoy = timezone.now().date()
        hoy = localtime(now()).date()   

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
                Q(email__icontains=busqueda) |
                Q(clinica__nombre__icontains=busqueda)
            )
            
        # ---------------------------------------------------------
        # ESCENARIO B: LA RED DE ARRASTRE (Filtrando grupos diarios)
        # ---------------------------------------------------------
        else:
            # Regla INBOX ZERO: Ocultar los que ya terminaron su ciclo
            #qs = qs.exclude(estatus__in=['CLIENTE', 'NO_CIERRE']).exclude(plan='DESCARTADO')
            # Regla HIBERNACIÓN: Si está "En Espera" para una fecha futura, lo ocultamos hoy
            # (Asumiendo que usas next_action_date, si usas otro campo, lo cambiamos)
            #qs = qs.exclude(Q(plan='EN_ESPERA') & Q(next_action_date__gt=hoy))
            if filtro_rapido == 'clientes':
                # Si presionó el botón de Clientes, le traemos solo los clientes
                qs = qs.filter(estatus='CLIENTE')
            else:
                # Regla INBOX ZERO: (Se mantiene para todo lo demás)
                qs = qs.exclude(estatus__in=['CLIENTE', 'NO_CIERRE']).exclude(plan='DESCARTADO')
                
                # Regla HIBERNACIÓN: (Se mantiene para todo lo demás)
                qs = qs.exclude(Q(plan='EN_ESPERA') & Q(next_action_date__gt=hoy))

            # Aplicar el botón que el vendedor haya presionado
            if filtro_rapido == 'hoy':
                qs = qs.filter(next_action_date=hoy)
            elif filtro_rapido == 'frescos':
                qs = qs.filter(estatus='PROSPECTO')
            elif filtro_rapido == 'urgentes':
                # Ejemplo: leads en SEGUIMIENTO que su fecha de acción ya se pasó
                qs = qs.filter(plan='SEGUIMIENTO', next_action_date__lt=hoy)
            elif filtro_rapido == 'campanas':
                from .models import Evento
                eventos_activos = Evento.objects.filter(
                    estatus='ACTIVO',
                    vendedores_asignados=self.request.user
                )

                lineas_objetivo = []
                estados_obj = set()
                for ev in eventos_activos:
                    if ev.linea_producto and ev.linea_producto not in lineas_objetivo:
                        lineas_objetivo.append(ev.linea_producto)
                    if ev.estados_objetivo:
                        estados_obj.update(ev.estados_objetivo)
                
                estados_obj = list(estados_obj)

                if not eventos_activos.exists():
                    qs = qs.none()
                else:
                    q_campanas = Q()
                    if estados_obj:
                        q_campanas &= Q(ubicacion__estado__in=estados_obj)

                    if lineas_objetivo and 'TODAS' not in lineas_objetivo:
                        q_lineas = Q()
                        for linea in lineas_objetivo:
                            q_lineas |= Q(producto_cat__nombre__icontains=linea)
                        q_campanas &= q_lineas

                    qs = qs.filter(q_campanas)
        
        # Ordenamos la consulta final
        qs = qs.order_by('-updated_at')

        # Dividimos en bloques de 10 registros por página
        paginador = Paginator(qs, 7) 
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
        context['ubicaciones_list'] = CatUbicacion.objects.filter(is_active=True).values_list('ciudad', flat=True).order_by('ciudad')
        context['titulos_list'] = CatTitulo.objects.filter(is_active=True).order_by('nombre')
        
        # 3. ENVIAR RESULTADOS AL HTML
        #context['leads'] = qs.order_by('-updated_at') # Los movidos recientemente van arriba
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

import os
import uuid
import pandas as pd
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from leads.parser_service import orquestar_ingesta_historica

@method_decorator(role_required(['DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaHistoricaView(LoginRequiredMixin, TemplateView):
    template_name = 'leads/ingesta_historica.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        context = self.get_context_data()

        # Configurar almacenamiento temporal seguro
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_ingesta')
        os.makedirs(temp_dir, exist_ok=True)
        fs = FileSystemStorage(location=temp_dir)

        if action == 'simulate':
            archivo = request.FILES.get('archivo_historico')
            if not archivo:
                messages.error(request, "Debes adjuntar un archivo (CSV/Excel).")
                return render(request, self.template_name, context)

            try:
                # 1. Guardar archivo temporal con UUID
                ext = os.path.splitext(archivo.name)[1]
                file_uuid = f"{uuid.uuid4().hex}{ext}"
                filename = fs.save(file_uuid, archivo)
                file_path = fs.path(filename)
                
                # 2. Leer archivo en memoria usando Pandas
                if ext.lower() in ['.xls', '.xlsx']:
                    df = pd.read_excel(file_path)
                elif ext.lower() == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    fs.delete(filename)
                    messages.error(request, "Formato no soportado. Usa CSV o Excel.")
                    return render(request, self.template_name, context)

                # Limpiar NaN y convertir a lista de diccionarios
                df = df.fillna('')
                # Convertimos nombres de columnas a minúsculas y sin espacios para mayor flexibilidad
                df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
                filas_data = df.to_dict('records')

                if not filas_data:
                    fs.delete(filename)
                    messages.warning(request, "El archivo está vacío.")
                    return render(request, self.template_name, context)

                # 3. Ejecutar SIMULACRO (Dry Run)
                reporte = orquestar_ingesta_historica(
                    filas_data=filas_data,
                    admin_user=request.user,
                    dry_run=True  # NO TOCA LA BASE DE DATOS
                )

                # Pasar resultados al template
                context['reporte'] = reporte
                context['file_uuid'] = file_uuid
                context['simulacion_activa'] = True
                
                if reporte.get("errores_criticos", 0) > 0:
                    messages.warning(request, f"Se encontraron {reporte['errores_criticos']} registros con errores críticos que no podrán ser inyectados.")

            except Exception as e:
                if 'filename' in locals() and fs.exists(filename):
                    fs.delete(filename)
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
            
            return render(request, self.template_name, context)

        elif action == 'commit':
            file_uuid = request.POST.get('file_uuid')
            
            if not file_uuid:
                messages.error(request, "Sesión de simulacro expirada o archivo no encontrado. Vuelve a subirlo.")
                return redirect('director_ingesta')

            file_path = fs.path(file_uuid)
            
            if not fs.exists(file_uuid):
                messages.error(request, "El archivo temporal ya no existe. Por favor repite el proceso.")
                return redirect('director_ingesta')

            try:
                # 1. Volver a leer exactamente el mismo archivo temporal
                ext = os.path.splitext(file_uuid)[1]
                if ext.lower() in ['.xls', '.xlsx']:
                    df = pd.read_excel(file_path)
                else:
                    df = pd.read_csv(file_path)

                df = df.fillna('')
                df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
                filas_data = df.to_dict('records')

                # 2. Ejecutar INYECCIÓN REAL
                reporte = orquestar_ingesta_historica(
                    filas_data=filas_data,
                    admin_user=request.user,
                    dry_run=False  # AHORA SÍ IMPACTA LA DB
                )

                messages.success(request, f"¡Migración Histórica completada! Se crearon {reporte['clinicas_identificadas']} clínicas y {reporte['individuos_atomizados']} individuos.")
                
                # 3. Eliminar archivo temporal por seguridad
                fs.delete(file_uuid)
                
                return redirect('director_dashboard')

            except Exception as e:
                messages.error(request, f"Error durante la inyección: {str(e)}")
                # Si falla fuerte, intentamos limpiar la basura
                if fs.exists(file_uuid):
                     fs.delete(file_uuid)
                return redirect('director_ingesta')
        
        elif action == 'cancel':
             file_uuid = request.POST.get('file_uuid')
             if file_uuid and fs.exists(file_uuid):
                 fs.delete(file_uuid)
             messages.info(request, "Proceso de ingesta cancelado.")
             return redirect('director_ingesta')

        return render(request, self.template_name, context)

from leads.models import LeadStaging
from django.views.generic import ListView

@method_decorator(role_required(['DIRECTOR', 'ADMIN']), name='dispatch')
class ListaStagingView(LoginRequiredMixin, ListView):
    model = LeadStaging
    template_name = 'leads/staging_list.html'
    context_object_name = 'leads_staging'
    paginate_by = 50

    def get_queryset(self):
        # Solo mostrar los pendientes, ordenados por los más antiguos primero
        return LeadStaging.objects.filter(estatus='PENDIENTE').order_by('created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_pendientes'] = LeadStaging.objects.filter(estatus='PENDIENTE').count()
        return context

@method_decorator(role_required(['DIRECTOR', 'ADMIN']), name='dispatch')
class ProcesarStagingView(LoginRequiredMixin, DetailView):
    model = LeadStaging
    template_name = 'leads/staging_procesar.html'
    context_object_name = 'staging_lead'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        context['vendedores_list'] = User.objects.filter(is_active=True, is_superuser=False).order_by('username')
        context['especialidades_list'] = CatEspecialidad.objects.filter(is_active=True).order_by('nombre')
        context['ubicaciones_list'] = CatUbicacion.objects.filter(is_active=True).order_by('ciudad')
        context['titulos_list'] = CatTitulo.objects.filter(is_active=True).order_by('nombre')
        # Buscamos cuántos quedan para el badge superior
        context['restantes'] = LeadStaging.objects.filter(estatus='PENDIENTE').count()
        return context

    def post(self, request, *args, **kwargs):
        staging_lead = self.get_object()
        action = request.POST.get('action')

        if action == 'descartar':
            staging_lead.estatus = 'DESCARTADO'
            staging_lead.save()
            messages.info(request, "Registro descartado exitosamente.")
            return self._redirect_to_next()

        elif action == 'guardar':
            # Extraer IDs y tipos
            vendedor_id = request.POST.get('vendedor_id')
            tipo_entidad = request.POST.get('tipo_entidad', 'INDIVIDUAL')
            especialidad_id = request.POST.get('especialidad_id')
            ubicacion_id = request.POST.get('ubicacion_id')

            telefono = str(request.POST.get('telefono', '')).strip()
            celular = str(request.POST.get('celular', '')).strip()
            email = str(request.POST.get('email', '')).strip()
            
            titulo_id = request.POST.get('titulo_cortesia')
            nombre_pila = str(request.POST.get('nombre_pila', '')).strip()
            apellido_paterno = str(request.POST.get('apellido_paterno', '')).strip()
            apellido_materno = str(request.POST.get('apellido_materno', '')).strip()

            vendedor_historico = staging_lead.datos_crudos.get('vendedor_historico', 'Desconocido')
            notas_originales = staging_lead.datos_crudos.get('notas', '')

            # --- OBTENER OBJETOS DE CATÁLOGOS ---
            titulo_obj = CatTitulo.objects.filter(id=titulo_id).first() if titulo_id else None
            especialidad_obj = CatEspecialidad.objects.filter(id=especialidad_id).first()
            ubicacion_obj = CatUbicacion.objects.filter(id=ubicacion_id).first()

            if not all([especialidad_obj, ubicacion_obj]):
                messages.error(request, "Especialidad y Ubicación son campos obligatorios.")
                return redirect('staging_procesar', pk=staging_lead.pk)

            # --- CONCATENACIÓN MDM ---
            nombre_concatenado = ""
            if tipo_entidad == 'CORPORATIVO':
                nombre_concatenado = nombre_pila # En clínicas, el nombre principal viene acá
            else:
                partes_nombre = []
                if nombre_pila: partes_nombre.append(nombre_pila)
                if apellido_paterno: partes_nombre.append(apellido_paterno)
                if apellido_materno: partes_nombre.append(apellido_materno)
                nombre_concatenado = " ".join(partes_nombre)

            if not nombre_concatenado:
                messages.error(request, "El nombre no puede estar vacío.")
                return redirect('staging_procesar', pk=staging_lead.pk)

            # --- REGLA DE ORO DE NO DUPLICACIÓN (MDM ESTRICTO) ---
            from .mdm_services import evaluar_duplicidad_estricta
            estatus_identidad, resultado_identidad = evaluar_duplicidad_estricta(
                nombre_concatenado, telefono, especialidad_obj.nombre, ubicacion_obj.ciudad, CoreLead
            )
            
            if estatus_identidad == 'ERROR':
                messages.error(request, f"Error MDM: {resultado_identidad}")
                return redirect('staging_procesar', pk=staging_lead.pk)
                
            elif estatus_identidad == 'DUPLICADO':
                dueño = resultado_identidad.owner.username if resultado_identidad.owner else 'Sin asignar'
                messages.error(
                    request, 
                    f"⚠️ Inyección Bloqueada: El sistema detectó un duplicado activo en CoreLead ({resultado_identidad.nombre} - Tel: {resultado_identidad.phone_primary}). "
                    f"Pertenece a la cartera de {dueño}. Debes DESCARTAR este registro o cambiar el número."
                )
                return redirect('staging_procesar', pk=staging_lead.pk)

            telefono_limpio = resultado_identidad

            # --- LÓGICA DE ASIGNACIÓN HÍBRIDA (REGLA DE ORO) ---
            from django.contrib.auth import get_user_model
            from django.db.models import Count
            User = get_user_model()

            if not vendedor_id:
                vendedor_asignado = User.objects.filter(
                    is_active=True, is_superuser=False
                ).annotate(Count('corelead')).order_by('corelead__count').first()
            else:
                vendedor_asignado = get_object_or_404(User, id=vendedor_id)

            if not vendedor_asignado:
                 messages.error(request, "No hay vendedores activos en el sistema para asignar el prospecto.")
                 return redirect('staging_procesar', pk=staging_lead.pk)

            # Preparar notas históricas empaquetadas (Zona Neutral / Inyección)
            nota_historica_compilada = f"[QUIRÓFANO] Inyectado manualmente. Vendedor Orig: {vendedor_historico} | Notas Orig: {notas_originales}"
            notas_historicas = {
                "notas": [{
                    "tipo": "sistema",
                    "contenido": nota_historica_compilada,
                    "fecha": localtime(now()).isoformat(),
                    "usuario": request.user.id
                }],
                "columnas_excel_historicas": staging_lead.datos_crudos
            }

            # Crear el CoreLead Final Bifurcado
            try:
                from .models import Clinica
                if tipo_entidad == 'CORPORATIVO':
                    clinica_obj, _ = Clinica.objects.get_or_create(
                        telefono_master=telefono_limpio,
                        defaults={'nombre': nombre_concatenado}
                    )
                    CoreLead.objects.create(
                        owner=vendedor_asignado,
                        ubicacion=ubicacion_obj,
                        estatus='CLIENTE',  
                        phone_primary=telefono_limpio,
                        celular=celular[:15],
                        email=email,
                        nombre=nombre_concatenado[:100],
                        nombre_pila=nombre_concatenado[:100],
                        clinica=clinica_obj,
                        especialidad_cat=especialidad_obj,
                        notas_variadas=notas_historicas,
                    )
                else:
                    CoreLead.objects.create(
                        owner=vendedor_asignado,
                        ubicacion=ubicacion_obj,
                        estatus='CLIENTE',  
                        phone_primary=telefono_limpio,
                        celular=celular[:15],
                        email=email,
                        nombre=nombre_concatenado[:100],
                        titulo_cortesia=titulo_obj,
                        nombre_pila=nombre_pila[:100],
                        apellido_paterno=apellido_paterno[:100],
                        apellido_materno=apellido_materno[:100],
                        especialidad_cat=especialidad_obj,
                        notas_variadas=notas_historicas,
                    )
                
                # Marcar LeadStaging como resuelto
                staging_lead.estatus = 'RESUELTO'
                staging_lead.save()
                
                messages.success(request, f"¡Inyectado exitosamente! Asignado a {vendedor_asignado.username}.")
                return self._redirect_to_next()
                
            except Exception as e:
                messages.error(request, f"Error interno al guardar en BD: {str(e)}")
                return redirect('staging_procesar', pk=staging_lead.pk)

        return redirect('staging_procesar', pk=staging_lead.pk)

    def _redirect_to_next(self):
        # Busca el siguiente pendiente cronológicamente
        siguiente = LeadStaging.objects.filter(estatus='PENDIENTE').order_by('created_at').first()
        if siguiente:
            return redirect('staging_procesar', pk=siguiente.pk)
        messages.success(self.request, "¡Felicidades! Se ha vaciado la cola del Quirófano.")
        return redirect('staging_list')


from django.views.generic import View

@method_decorator(role_required(['DIRECTOR', 'ADMIN']), name='dispatch')
class IngestaHistoricaExpressView(LoginRequiredMixin, View):
    template_name = 'leads/ingesta_express.html'

    def get(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        context = {
            'vendedores_list': User.objects.filter(is_active=True, is_superuser=False).order_by('username'),
            'especialidades_list': CatEspecialidad.objects.filter(is_active=True).order_by('nombre'),
            'ubicaciones_list': CatUbicacion.objects.filter(is_active=True).order_by('ciudad'),
            'titulos_list': CatTitulo.objects.filter(is_active=True).order_by('nombre'),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        vendedor_id = request.POST.get('vendedor_id')
        tipo_entidad = request.POST.get('tipo_entidad', 'INDIVIDUAL')
        especialidad_id = request.POST.get('especialidad_id')
        ubicacion_id = request.POST.get('ubicacion_id')

        telefono = str(request.POST.get('telefono', '')).strip()
        celular = str(request.POST.get('celular', '')).strip()
        email = str(request.POST.get('email', '')).strip()
        
        titulo_id = request.POST.get('titulo_cortesia')
        nombre_pila = str(request.POST.get('nombre_pila', '')).strip()
        apellido_paterno = str(request.POST.get('apellido_paterno', '')).strip()
        apellido_materno = str(request.POST.get('apellido_materno', '')).strip()

        # Validación de campos y catálogos obligatorios
        titulo_obj = CatTitulo.objects.filter(id=titulo_id).first() if titulo_id else None
        especialidad_obj = CatEspecialidad.objects.filter(id=especialidad_id).first()
        ubicacion_obj = CatUbicacion.objects.filter(id=ubicacion_id).first()

        if not all([especialidad_obj, ubicacion_obj]):
            messages.error(request, "Especialidad y Ubicación son campos obligatorios.")
            return redirect('ingesta_express')

        # Concatenación de nombre
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
            messages.error(request, "El nombre / razón social no puede estar vacío.")
            return redirect('ingesta_express')

        # Regla MDM Estricta
        from .mdm_services import evaluar_duplicidad_estricta
        estatus_identidad, resultado_identidad = evaluar_duplicidad_estricta(
            nombre_concatenado, telefono, especialidad_obj.nombre, ubicacion_obj.ciudad, CoreLead
        )
        
        if estatus_identidad == 'ERROR':
            messages.error(request, f"Error MDM: {resultado_identidad}")
            return redirect('ingesta_express')
            
        elif estatus_identidad == 'DUPLICADO':
            dueño = resultado_identidad.owner.username if resultado_identidad.owner else 'Sin asignar'
            messages.error(
                request, 
                f"⚠️ Inyección Bloqueada: El sistema detectó un duplicado activo en CoreLead ({resultado_identidad.nombre} - Tel: {resultado_identidad.phone_primary}). "
                f"Pertenece a la cartera de {dueño}."
            )
            return redirect('ingesta_express')

        telefono_limpio = resultado_identidad

        # Asignación Híbrida
        from django.contrib.auth import get_user_model
        from django.db.models import Count
        User = get_user_model()

        if not vendedor_id:
            vendedor_asignado = User.objects.filter(
                is_active=True, is_superuser=False
            ).annotate(Count('corelead')).order_by('corelead__count').first()
        else:
            vendedor_asignado = get_object_or_404(User, id=vendedor_id)

        if not vendedor_asignado:
            messages.error(request, "No hay vendedores activos en el sistema para asignar.")
            return redirect('ingesta_express')

        # Preparar notas históricas
        notas_historicas = {
            "notas": [{
                "tipo": "sistema",
                "contenido": "[INGRESO EXPRESS MANUAL] Migración Histórica: Cronología original no disponible",
                "fecha": localtime(now()).isoformat(),
                "usuario": request.user.id
            }],
            "columnas_excel_historicas": {}
        }

        # Crear el CoreLead Final bifurcado
        try:
            from .models import Clinica
            if tipo_entidad == 'CORPORATIVO':
                clinica_obj, _ = Clinica.objects.get_or_create(
                    telefono_master=telefono_limpio,
                    defaults={'nombre': nombre_concatenado}
                )
                nuevo_lead = CoreLead.objects.create(
                    owner=vendedor_asignado,
                    ubicacion=ubicacion_obj,
                    estatus='CLIENTE',  
                    phone_primary=telefono_limpio,
                    celular=celular[:15],
                    email=email,
                    nombre=nombre_concatenado[:100],
                    nombre_pila=nombre_concatenado[:100],
                    clinica=clinica_obj,
                    especialidad_cat=especialidad_obj,
                    notas_variadas=notas_historicas,
                )
            else:
                nuevo_lead = CoreLead.objects.create(
                    owner=vendedor_asignado,
                    ubicacion=ubicacion_obj,
                    estatus='CLIENTE',  
                    phone_primary=telefono_limpio,
                    celular=celular[:15],
                    email=email,
                    nombre=nombre_concatenado[:100],
                    titulo_cortesia=titulo_obj,
                    nombre_pila=nombre_pila[:100],
                    apellido_paterno=apellido_paterno[:100],
                    apellido_materno=apellido_materno[:100],
                    especialidad_cat=especialidad_obj,
                    notas_variadas=notas_historicas,
                )
            
            messages.success(request, f"🚀 ¡Ingreso Express exitoso! {nombre_concatenado} asignado a {vendedor_asignado.username}.")
            # Redirigir a la misma vista para otra captura
            return redirect('ingesta_express')
            
        except Exception as e:
            messages.error(request, f"Error al guardar en BD: {str(e)}")
            return redirect('ingesta_express')

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
        context['productos_list'] = CatProducto.objects.filter(is_active=True).order_by('nombre')
        context['titulos_list'] = CatTitulo.objects.filter(is_active=True).order_by('nombre')
        # Variables súper cortas para que el HTML no se rompa al guardar
        context['celular_seguro'] = lead.celular if lead.celular else "No registrado"
        # Priorizamos el catálogo relacional (DDS Fase 2)
        context['especialidad_segura'] = lead.especialidad_cat.nombre if lead.especialidad_cat else (lead.especialidad if lead.especialidad else "No especificada")
        context['producto_seguro'] = lead.producto_cat.nombre if lead.producto_cat else (lead.producto_interes if lead.producto_interes else "No especificado")
        
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
import re

from .mdm_services import normalizar_texto, limpiar_telefono_estricto, evaluar_duplicidad_estricta

def obtener_catalogos_limpios(texto_especialidad, texto_producto):
    """Versión Estricta DDS 2.0: Solo lee, NUNCA crea."""
    producto_obj = CatProducto.objects.filter(nombre__iexact=str(texto_producto).strip()).first()
    if not producto_obj:
        producto_obj = CatProducto.objects.filter(nombre__icontains='Por Definir').first()

    especialidad_obj = CatEspecialidad.objects.filter(nombre__iexact=str(texto_especialidad).strip()).first()
    if not especialidad_obj:
        especialidad_obj = CatEspecialidad.objects.filter(nombre__icontains='General').first()

    return especialidad_obj, producto_obj
    

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
            
            from .parser_service import parsear_fila
            from .models import Clinica
            parsed_data = parsear_fila(lead_data)
            
            if parsed_data["tipo_entidad"] == "MULTIPLE":
                reporte["D"].append({"fila": lead_data, "motivo": "Múltiples médicos detectados (Siameses)."})
                continue
                
            telefono = parsed_data["telefono_norm"]
            if not telefono:
                continue # Saltamos filas sin teléfono
                
            if parsed_data["tipo_entidad"] == "CORPORATIVO":
                clinica, created = Clinica.objects.get_or_create(
                    telefono_master=telefono,
                    defaults={"nombre": parsed_data["nombre_clinica"]}
                )
                reporte["A"].append(f"{telefono} (Corporativo: {parsed_data['nombre_clinica']})")
                continue
                
            nombre_raw = parsed_data["nombre_original"]
            nombre_norm = normalizar_texto(nombre_raw)

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
                    #   "fecha": timezone.now().isoformat()
                    "fecha": localtime(now()).strftime("%Y-%m-%d %H:%M")
                })

            from leads.services.common_services import obtener_catalogos_limpios
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
                    titulo_cortesia_id=parsed_data.get("titulo_id"),
                    nombre_pila=parsed_data.get("nombre_pila"),
                    apellido_paterno=parsed_data.get("apellido_paterno"),
                    apellido_materno=parsed_data.get("apellido_materno"),
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
                    titulo_cortesia_id=parsed_data.get("titulo_id"),
                    nombre_pila=parsed_data.get("nombre_pila"),
                    apellido_paterno=parsed_data.get("apellido_paterno"),
                    apellido_materno=parsed_data.get("apellido_materno"),
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
                        "contenido": f"Intento de re-ingesta masiva bloqueado el {localtime(now()).strftime('%Y-%m-%d %H:%M')}",
                        "fecha": localtime(now()).strftime('%Y-%m-%d %H:%M')
                    })
                    lead_existente.save(update_fields=['notas_variadas', 'updated_at'])
                    reporte['C'].append(nombre_raw)
                elif lead_existente.estatus == 'NO_CIERRE' and localtime(now()) - lead_existente.updated_at > timedelta(days=365):
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
        from leads.services.lead_creation_service import crear_prospecto_core
        
        # Delegamos TODA la lógica al Service Layer
        resultado = crear_prospecto_core(data, request.user)
        
        if resultado.get("success"):
            return JsonResponse({
                'status': 'success', 
                'mensaje': resultado.get("mensaje", "Creado con éxito"),
                'lead_id': resultado.get("lead_id")
            })
        else:
            return JsonResponse({"error": resultado.get("error")}, status=resultado.get("status_code", 400))

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
        from leads.services.fsm_services import procesar_transicion_fsm
        
        resultado = procesar_transicion_fsm(pk, data, request.user)
        
        if resultado.get("success"):
            return JsonResponse({
                "status": resultado.get("status", "success"), # Soporte para status="deleted"
                "mensaje": resultado.get("mensaje"),
                "nuevo_estatus": resultado.get("nuevo_estatus")
            })
        else:
            return JsonResponse({"error": resultado.get("error")}, status=resultado.get("status_code", 400))

    except json.JSONDecodeError:
        return JsonResponse({"error": "Datos inválidos enviados desde el formulario."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
@require_POST
def api_marcar_no_cierre(request, pk):
    try:
        data = json.loads(request.body)
        motivo = data.get('motivo', 'Desconocido').strip()
        
        lead = get_object_or_404(CoreLead, id=pk)
        
        # Invocamos estrictamente a la máquina de estados FSM
        try:
            texto_nota_historica = f"Rechazo Definitivo: {motivo}"
            lead.archivar_sin_exito(nota_motivo=texto_nota_historica, usuario_id=request.user.id)
            lead.save()
            
            return JsonResponse({"status": "success", "mensaje": "El ciclo del prospecto se ha cerrado sin éxito (NO CIERRE)."})
            
        except Exception as e:
            # Capturamos excepciones propias del FSM (ej. TransitionNotAllowed)
            return JsonResponse({"error": str(e)}, status=400)
            
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def es_director(user):
    return user.is_superuser


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

    hace_7_dias = localtime(now()) - timedelta(days=7)
    base_semana = qs.filter(updated_at__gte=hace_7_dias).exclude(estatus='Histórico')

    total_trabajados_semana = base_semana.count()
    vendedores_activos = total_vendedores_metric
    volumen_promedio = round(total_trabajados_semana / vendedores_activos, 1) if vendedores_activos > 0 else 0

    tasa_calidad = base_semana.filter(plan__iexact='descartado').count()
    tasa_prospeccion = base_semana.filter(calificacion__in=[2, 3]).count()
    indice_venta = base_semana.filter(estatus__iexact='cliente').count()
    tasa_no_cierre = base_semana.filter(estatus__iexact='NO_CIERRE').count()

    # --- 6. DATOS PARA GRÁFICAS MULTIDIMENSIONALES ---
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

    stats_vendedor = qs.values('owner__username').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta),
        total_no_cierres=Count('id', filter=q_no_cierre)
    ).order_by('owner__username')
    v_labels, v_rech, v_seg, v_cal, v_ven, v_noc = procesar_agrupacion(stats_vendedor, 'owner__username')

    stats_ubicacion = qs.values('ubicacion__estado').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta),
        total_no_cierres=Count('id', filter=q_no_cierre)
    ).order_by('ubicacion__estado')
    u_labels, u_rech, u_seg, u_cal, u_ven, u_noc = procesar_agrupacion(stats_ubicacion, 'ubicacion__estado')

    stats_especialidad = qs.values('especialidad_cat__nombre').annotate(
        total_rechazos=Count('id', filter=q_rechazo),
        total_seguimientos=Count('id', filter=q_seguimiento),
        total_calificados=Count('id', filter=q_calificado),
        total_ventas=Count('id', filter=q_venta),
        total_no_cierres=Count('id', filter=q_no_cierre)
    ).order_by('especialidad_cat__nombre')
    e_labels, e_rech, e_seg, e_cal, e_ven, e_noc = procesar_agrupacion(stats_especialidad, 'especialidad_cat__nombre')

    # --- 7. FORECAST MENSUAL ---
    import datetime
    
    hoy = localtime(now()).date()
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

    # --- EMBUDO DE CONVERSIÓN (DONA) ---
    dona_prospectos = qs.filter(estatus='PROSPECTO').count()
    dona_leads_frios = qs.filter(estatus='LEAD').exclude(calificacion__in=[2, 3]).count()
    dona_calificados = qs.filter(estatus='LEAD', calificacion__in=[2, 3]).count()
    dona_clientes = qs.filter(estatus='CLIENTE').count()
    
    dona_data = [dona_prospectos, dona_leads_frios, dona_calificados, dona_clientes]

    # --- 8. CONTEXTO ---
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
        'tasa_no_cierre': tasa_no_cierre,
        'dona_data': dona_data,
        'chart_v_labels': json.dumps(v_labels), 'chart_v_rech': json.dumps(v_rech), 'chart_v_seg': json.dumps(v_seg), 'chart_v_cal': json.dumps(v_cal), 'chart_v_ven': json.dumps(v_ven), 'chart_v_noc': json.dumps(v_noc),
        'chart_u_labels': json.dumps(u_labels), 'chart_u_rech': json.dumps(u_rech), 'chart_u_seg': json.dumps(u_seg), 'chart_u_cal': json.dumps(u_cal), 'chart_u_ven': json.dumps(u_ven), 'chart_u_noc': json.dumps(u_noc),
        'chart_e_labels': json.dumps(e_labels), 'chart_e_rech': json.dumps(e_rech), 'chart_e_seg': json.dumps(e_seg), 'chart_e_cal': json.dumps(e_cal), 'chart_e_ven': json.dumps(e_ven), 'chart_e_noc': json.dumps(e_noc),
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
    hace_7_dias = localtime(now()) - timedelta(days=7)
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

    # 3. Agrupación por Especialidad Médica 
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
@login_required
@user_passes_test(es_director, login_url='dashboard_agente')
def director_dashboard_view(request):
    from leads.services.dashboard_services import obtener_metricas_director
    
    # 1. Recolectar parámetros HTTP
    filtros = {
        'estado': request.GET.get('estado', ''),
        'especialidad': request.GET.get('especialidad', ''),
        'producto': request.GET.get('producto', ''),
        'vendedor': request.GET.get('vendedor', '')
    }
    
    # 2. Delegar el cálculo pesado al Service Layer
    context = obtener_metricas_director(filtros)
    
    # 3. Renderizar la vista
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

@login_required
@require_POST
def registrar_venta_extra(request):
    """
    Registra una compra transaccional solo si el lead ya es CLIENTE.
    Pensado para ventas de tipo Accesorio, Servicio o Evento.
    """
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        producto_id = data.get('producto_id')
        monto = data.get('monto')
        notas = data.get('notas', '')
        estatus = data.get('estatus', 'PENDIENTE') # Nuevo estatus

        if not lead_id or not producto_id:
            return JsonResponse({"error": "Faltan datos obligatorios (lead_id, producto_id)."}, status=400)
        
        lead = get_object_or_404(CoreLead, id=lead_id)
        
        # 1. Candado de Fidelización (Visión 360°): 
        # Cero impacto al FSM, venta reservada a CLIENTES ya consolidados en el embudo.
        if lead.estatus != 'CLIENTE':
            return JsonResponse({"error": "Solo puedes registrar ventas transaccionales a prospectos con estatus de CLIENTE."}, status=400)

        producto = get_object_or_404(CatProducto, id=producto_id)

        # --- CANDADO ANTI-SPAM (Código de antiG) ---
        from .models import VentaTransaccional
        
        if VentaTransaccional.objects.filter(lead=lead, producto=producto, estatus__in=['PENDIENTE', 'EN_GESTION']).exists():
            return JsonResponse({"error": "Ya existe una oportunidad activa (Pendiente o En Gestión) para este producto."}, status=400)
        # ------------------------------------------

        # 2. Guardado de Independencia Transaccional
        nueva_venta = VentaTransaccional.objects.create(
            lead=lead,
            producto=producto,
            vendedor=request.user,
            estatus=estatus, 
            monto=monto if monto else None,
            notas=notas
        )

        # --- NUEVO: Inyectar la miga de pan en el historial del Lead ---
        # ... (aquí sigue el resto de tu código normal que guarda las notas) ...
        # --- NUEVO: Inyectar la miga de pan en el historial del Lead ---
        # from django.utils import timezone
        
        #timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        timestamp = localtime(now()).strftime("%Y-%m-%d %H:%M")
        
        nueva_nota = {
            "fecha": timestamp,
            "tipo": "sistema",  # Lo marcamos como sistema para que resalte
            "contenido": f"🎯 Oportunidad 360° creada: {producto.nombre} (Estatus: {estatus}).\n📝 Notas: {notas}"
        }

        # Asegurarnos de que el diccionario de notas exista
        if not isinstance(lead.notas_variadas, dict):
            lead.notas_variadas = {"notas": []}
        if "notas" not in lead.notas_variadas:
            lead.notas_variadas["notas"] = []
            
        # Guardar la nota y actualizar el lead
        lead.notas_variadas["notas"].append(nueva_nota)
        lead.save(update_fields=['notas_variadas'])
        # ----------------------------------------------------------------

        return JsonResponse({
            "status": "success",
            "mensaje": "Venta transaccional registrada exitosamente.",
            "venta_id": str(nueva_venta.id)
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON Inválido enviado en la petición."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def bandeja_rescate_view(request):
    if not request.user.is_superuser:
        return render(request, '403.html')
    
    leads = CoreLead.objects.filter(
        Q(estatus='EN_ESPERA') | Q(plan__iexact='descartado') | Q(estatus__iexact='NO_CIERRE')
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

from django.core.paginator import Paginator

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

from .models import Evento

@login_required
def director_eventos_view(request):
    if not request.user.is_superuser:
        return render(request, '403.html')
        
    eventos = Evento.objects.prefetch_related('vendedores_asignados').order_by('-fecha_inicio')
    vendedores = User.objects.filter(is_active=True, is_superuser=False).order_by('username')
    estados_list = CatUbicacion.objects.exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')
    
    context = {
        'eventos': eventos,
        'vendedores': vendedores,
        'estados_list': estados_list,
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
        tipo = data.get('tipo', 'EXPO')
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        lugar = data.get('lugar')
        linea_producto = data.get('linea_producto', 'TODAS')
        estados_objetivo = data.get('estados_objetivo', [])
        
        if not all([nombre, fecha_inicio, fecha_fin, lugar]):
             return JsonResponse({'success': False, 'error': 'Revisa los campos obligatorios.'}, status=400)
             
        vendedores_ids = data.get('vendedores_ids', [])
        
        nuevo_evento = Evento.objects.create(
            nombre=nombre,
            tipo=tipo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            lugar=lugar,
            linea_producto=linea_producto,
            estados_objetivo=estados_objetivo
        )
        
        if vendedores_ids:
            nuevo_evento.vendedores_asignados.set(vendedores_ids)
            
        return JsonResponse({'success': True, 'message': 'Evento creado correctamente.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def actualizar_estatus_venta_extra(request, venta_id):
    """
    Endpoint para actualizar el estatus de una VentaTransaccional (Oportunidad 360°).
    Inyecta una miga de pan en notas_variadas del CoreLead asociado.
    """
    try:
        data = json.loads(request.body)
        nuevo_estatus = data.get('estatus')

        # Validación de estatus permitido
        from .models import VentaTransaccional
        estatus_validos = [choice[0] for choice in VentaTransaccional.ESTATUS_CHOICES]
        if nuevo_estatus not in estatus_validos:
            return JsonResponse({"error": f"Estatus '{nuevo_estatus}' no es válido."}, status=400)

        venta = get_object_or_404(VentaTransaccional, id=venta_id)

        # --- Guardia de Flujo Unidireccional ---
        TRANSICIONES_PERMITIDAS = {
            'PENDIENTE':   ['EN_GESTION'],
            'EN_GESTION':  ['CONCRETADO', 'DESCARTADO'],
            'CONCRETADO':  [],   # Estado terminal
            'DESCARTADO':  [],   # Estado terminal
        }

        transiciones_validas = TRANSICIONES_PERMITIDAS.get(venta.estatus, [])
        if nuevo_estatus not in transiciones_validas:
            return JsonResponse({
                "error": f"Transición no permitida: {venta.get_estatus_display()} → {nuevo_estatus}. "
                         f"Solo puedes avanzar a: {', '.join(transiciones_validas) or 'Ninguno (estado final)'}."
            }, status=400)

        estatus_anterior = venta.get_estatus_display()

        # Actualizar el estatus
        venta.estatus = nuevo_estatus
        venta.save(update_fields=['estatus'])

        # --- Inyectar miga de pan en el historial del Lead ---
        lead = venta.lead
        timestamp = localtime(now()).strftime("%Y-%m-%d %H:%M")

        nueva_nota = {
            "fecha": timestamp,
            "tipo": "sistema",
            "contenido": f"🔄 Oportunidad 360° actualizada: {venta.producto.nombre} — {estatus_anterior} → {venta.get_estatus_display()}."
        }

        if not isinstance(lead.notas_variadas, dict):
            lead.notas_variadas = {"notas": []}
        if "notas" not in lead.notas_variadas:
            lead.notas_variadas["notas"] = []

        lead.notas_variadas["notas"].append(nueva_nota)

        # --- Nota opcional del vendedor ---
        nota_vendedor = data.get('nota', '').strip()
        if nota_vendedor:
            nota_humana = {
                "fecha": timestamp,
                "tipo": "vendedor",
                "contenido": f"📝 [{venta.producto.nombre}] {nota_vendedor}"
            }
            lead.notas_variadas["notas"].append(nota_humana)

        lead.save(update_fields=['notas_variadas'])

        return JsonResponse({
            "status": "success",
            "mensaje": f"Estatus actualizado a {venta.get_estatus_display()}."
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(es_director, login_url='dashboard_agente')
def dashboard_fidelizacion_view(request):
    """
    Dashboard de Fidelización 360° — Métricas de volumen
    para oportunidades de venta cruzada (VentaTransaccional).
    Solo accesible para la Dirección.
    """
    from .models import VentaTransaccional
    from django.core.paginator import Paginator
    from datetime import datetime

    # 1. Filtros
    filtro_vendedor = request.GET.get('vendedor', '')
    filtro_estatus = request.GET.get('estatus', '')
    filtro_familia = request.GET.get('familia', '')
    filtro_fecha_desde = request.GET.get('fecha_desde', '')
    filtro_fecha_hasta = request.GET.get('fecha_hasta', '')

    qs = VentaTransaccional.objects.select_related('lead', 'producto', 'vendedor').all()

    if filtro_vendedor:
        qs = qs.filter(vendedor__username__iexact=filtro_vendedor)
    if filtro_estatus:
        qs = qs.filter(estatus=filtro_estatus)
    if filtro_familia:
        qs = qs.filter(producto__familia__iexact=filtro_familia)

    # Filtros de rango de fechas (sobre fecha_venta)
    if filtro_fecha_desde:
        try:
            fecha_desde = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')
            qs = qs.filter(fecha_venta__date__gte=fecha_desde.date())
        except ValueError:
            pass
    if filtro_fecha_hasta:
        try:
            fecha_hasta = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            qs = qs.filter(fecha_venta__date__lte=fecha_hasta.date())
        except ValueError:
            pass

    qs = qs.order_by('-fecha_venta')

    # 2. KPIs (Volumen)
    total_ops = qs.count()
    pendientes = qs.filter(estatus='PENDIENTE').count()
    concretadas = qs.filter(estatus='CONCRETADO').count()
    en_gestion = qs.filter(estatus='EN_GESTION').count()
    descartadas = qs.filter(estatus='DESCARTADO').count()

    tasa_cierre = 0
    ops_cerradas = concretadas + descartadas
    if ops_cerradas > 0:
        tasa_cierre = round((concretadas / ops_cerradas) * 100, 1)

    # 3. Datos para Chart.js (JSON seguro para el template)
    chart_data = json.dumps({
        'labels': ['Pendiente', 'En Gestión', 'Concretado', 'Descartado'],
        'data': [pendientes, en_gestion, concretadas, descartadas],
        'colors': ['#ffc107', '#0d6efd', '#198754', '#dc3545'],
    })

    # 4. Listas para Dropdowns
    vendedores_list = User.objects.filter(is_active=True, is_superuser=False).order_by('username')
    familias_list = ['ACCESORIO', 'SERVICIO', 'EVENTO']
    estatus_list = VentaTransaccional.ESTATUS_CHOICES

    # 5. Paginación (5 registros para convivir con la gráfica)
    paginator = Paginator(qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_ops': total_ops,
        'pendientes': pendientes,
        'concretadas': concretadas,
        'en_gestion': en_gestion,
        'descartadas': descartadas,
        'tasa_cierre': tasa_cierre,
        'chart_data': chart_data,
        'vendedores': vendedores_list,
        'familias': familias_list,
        'estatus_list': estatus_list,
        'filtro_vendedor': filtro_vendedor,
        'filtro_estatus': filtro_estatus,
        'filtro_familia': filtro_familia,
        'filtro_fecha_desde': filtro_fecha_desde,
        'filtro_fecha_hasta': filtro_fecha_hasta,
    }
    return render(request, 'director_fidelizacion.html', context)
