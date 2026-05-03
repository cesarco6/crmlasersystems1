# 🏛️ Arquitectura Técnica — CRM Laser Systems
> **DDS versión:** 2.1 · **Commit base:** `8488718` · **Actualizado:** 03/Mayo/2026

---

## 1. Stack Tecnológico

| Capa | Tecnología | Versión | Rol |
|---|---|---|---|
| **Runtime** | Python | 3.12 | Lenguaje base |
| **Framework** | Django | ≥5.0, <5.1 | MVT + ORM + Admin |
| **Base de datos** | PostgreSQL | 16-alpine | Persistencia principal + JSONB |
| **Broker / Caché** | Redis | 7-alpine | Cola de tareas + caché de sesiones |
| **Servidor WSGI prod** | Gunicorn | ≥21.2 | 3 workers, 2 threads, 60s timeout |
| **Proxy reverso** | Nginx | (externo) | TLS, headers, archivos estáticos |
| **Servidor estáticos** | Whitenoise | ≥6.6 | Sirve `/static/` dentro de Django |
| **FSM** | django-fsm | 3.0.1 | Máquina de estados protegida en modelos |
| **Cola de tareas** | django-q2 | ≥1.6 | Scheduler de alertas proactivo |
| **Excel (lectura)** | pandas + openpyxl | ≥2.0 / ≥3.1 | Ingesta masiva + exportaciones XLSX |
| **Excel (escritura)** | openpyxl | ≥3.1 | Generación de reportes XLSX (nuevo) |
| **Documentos Word** | docxtpl | ≥0.20 | Formato de pedido con plantilla .docx |
| **Frontend** | Django Templates + Bootstrap 5.3 | - | MVT server-side rendering |
| **JS libs** | Vanilla JS, SweetAlert2, Chart.js | CDN | Modales, alertas, gráficas |
| **Contenedorización** | Docker + Docker Compose | - | Entornos dev y prod |

---

## 2. Estructura del Proyecto

```
crm_laser_systems/
├── Dockerfile
├── docker-compose.yml          # Entorno desarrollo
├── docker-compose.prod.yml     # Entorno producción (Gunicorn)
├── .env                        # Variables sensibles (NO versionado)
├── .gitignore
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                 # Configuración Django (settings, urls, wsgi)
│   │   ├── settings.py
│   │   ├── urls.py             # Router principal (84 líneas, 30+ rutas)
│   │   ├── middleware.py       # MaintenanceModeMiddleware
│   │   ├── wsgi.py / asgi.py
│   ├── leads/                  # App core del negocio
│   │   ├── models.py           # 8 modelos de negocio
│   │   ├── views.py            # ~1838 líneas, todas las vistas
│   │   ├── admin.py
│   │   ├── mixins.py           # LeadOwnershipMixin
│   │   ├── context_processors.py  # Contador de alertas global
│   │   ├── mdm_services.py     # MDM legacy (evaluar_duplicidad_estricta)
│   │   ├── parser_service.py   # Orquestador de ingesta masiva
│   │   ├── services.py         # Servicios auxiliares
│   │   ├── tasks.py            # Tareas legacy django-q
│   │   ├── services/           # Service Layer modular
│   │   │   ├── fsm_services.py      # Motor FSM (procesar_transicion_fsm)
│   │   │   ├── mdm_service.py       # MDM v2 (resolver_identidad)
│   │   │   ├── lead_creation_service.py
│   │   │   ├── dashboard_services.py
│   │   │   ├── document_services.py # docxtpl (formato pedido)
│   │   │   └── common_services.py
│   │   └── management/commands/
│   │       ├── generar_alertas.py   # Motor proactivo (5 reglas)
│   │       ├── migrar_catalogos.py  # Seed de catálogos
│   │       └── seed_ladas_mexico.py # Catálogo IFT nacional
│   ├── users/                  # App de usuarios y catálogos
│   │   ├── models.py           # UserProfile + 6 catálogos
│   │   ├── views.py            # Login dual, territorios
│   │   ├── permissions.py      # Decorador role_required
│   │   ├── backends.py         # EmailAuthBackend
│   │   └── admin.py
│   ├── templates/              # Django Templates (18 archivos)
│   ├── static/                 # CSS/JS propios
│   ├── staticfiles/            # Colección Whitenoise (collectstatic)
│   ├── media/                  # Uploads (formatos Word)
│   └── docs/
│       ├── avisos_architecture.md
│       ├── manual_usuario.md
│       └── arquitectura_tecnica.md  ← este archivo
```

---

## 3. Infraestructura Docker

### Desarrollo (`docker-compose.yml`)

```
┌─────────────────────────────────────────────┐
│  web (Django runserver :8000)               │
│  qcluster (python manage.py qcluster)       │
│  db  (postgres:16-alpine :5432)             │
│  redis (redis:7-alpine)                     │
└─────────────────────────────────────────────┘
```

### Producción (`docker-compose.prod.yml`)

```
Internet → Nginx (TLS) → crm_ls_prod (Gunicorn :8000 local)
                       → crm_ls_qcluster (Django Q workers)
                       → crm_ls_db (postgres:16)
                       → crm_ls_redis (redis:7)
```

- **Gunicorn:** `--workers 3 --threads 2 --timeout 60`
- **Bind:** `127.0.0.1:8000` (solo localhost, Nginx hace el proxy)
- **CSRF_TRUSTED_ORIGINS:** `https://crm-ls.lat`
- **SECURE_PROXY_SSL_HEADER:** `HTTP_X_FORWARDED_PROTO: https`

---

## 4. Modelos de Datos

### 4.1 Diagrama de Relaciones

```
User (Django auth)
 │── OneToOne ──► UserProfile (rol, meta_clientes_mensual)
 │── FK (owner) ─► CoreLead ◄── FK ── LeadStaging
                      │
                      ├── OneToOne ──► FiscalProfile
                      ├── OneToOne ──► TrackingPostVenta
                      ├── FK ─────────► Clinica
                      ├── FK ─────────► CatUbicacion
                      ├── FK ─────────► CatEspecialidad
                      ├── FK ─────────► CatProducto
                      ├── FK ─────────► CatTitulo
                      ├── M2M ─────────► Evento (via LeadEvento)
                      └── 1-N ─────────► VentaTransaccional

Notificacion ──► FK ──► User
             ──► FK ──► CoreLead

CatUbicacion ──► FK ──► CatLada (1-N)
             ──► M2M ──► Evento
             ──► M2M ──► UserProfile (AsignacionTerritorio)
```

### 4.2 Modelo Principal: `CoreLead`

```python
# PK: UUID v4 (no secuencial — ofuscación de URLs)
id             = UUIDField(primary_key=True)
owner          = FK(User)           # Scope RBAC: cada agente ve solo sus leads
ubicacion      = FK(CatUbicacion)
estatus        = FSMField(default='PROSPECTO', protected=True)
plan           = CharField(default='SEGUIMIENTO')  # SEGUIMIENTO | EN_ESPERA | DESCARTADO
calificacion   = IntegerField(default=0)  # 0=sin cal, 1=Baja, 2=Media, 3=Alta
next_action_date = DateField(null=True)
notas_variadas = JSONField(default=default_notas_variadas)  # JSONB híbrido
es_historico   = BooleanField(default=False)

# Identidad atómica (inmutable en Fase 2+)
titulo_cortesia = FK(CatTitulo)
nombre_pila     = CharField(100)
apellido_paterno = CharField(100)
apellido_materno = CharField(100)
phone_primary   = CharField(15)
celular         = CharField(15)

# Catálogos relacionales
especialidad_cat = FK(CatEspecialidad)
producto_cat     = FK(CatProducto)
clinica          = FK(Clinica, null=True)  # Solo entidades corporativas
```

**Candado de Identidad (override de `save()`):**
```python
# Si el estatus ya no es PROSPECTO, estos campos son INMUTABLES a nivel DB:
campos_bloqueados = ['phone_primary', 'nombre_pila', 'apellido_paterno',
                     'especialidad_cat', 'producto_cat']
# Lanza ValidationError si alguno cambia.
```

### 4.3 Estructura JSONB de `notas_variadas`

```json
{
  "notas": [
    {
      "tipo": "sistema | contacto | descarte",
      "contenido": "Texto de la nota",
      "fecha": "2026-05-03T09:00:00-06:00",
      "usuario": 1
    }
  ],
  "columnas_excel_historicas": {}
}
```

### 4.4 Catálogos del Sistema (`users/models.py`)

| Modelo | Descripción | Campos clave |
|---|---|---|
| `UserProfile` | Extiende User con rol RBAC | `rol`, `meta_clientes_mensual` |
| `CatUbicacion` | Ciudad + Estado | `ciudad`, `estado`, `is_active` |
| `CatLada` | Diccionario IFT nacional | `clave`, FK→CatUbicacion |
| `CatEspecialidad` | Especialidades médicas | `nombre`, `alias` (para ingestas) |
| `CatProducto` | Catálogo de productos | `nombre`, `familia`, `alias` |
| `CatTitulo` | Títulos de cortesía | `nombre`, `abreviatura` |
| `AsignacionTerritorio` | Mapa vendedor↔ciudad | FK→UserProfile, FK→CatUbicacion |
| `SalesGoal` | Metas mensuales | `periodo_inicio`, `cantidad_objetivo` |

---

## 5. Máquina de Estados FSM

Implementada con `django-fsm 3.0.1`. El campo `estatus` está protegido (`protected=True`), lo que impide modificarlo directamente; solo las transiciones decoradas con `@transition` pueden cambiarlo.

```
PROSPECTO ──validar_identidad()──► LEAD
              (+ justificación obligatoria)
LEAD      ──calificar_lead()────► LEAD_CALIFICADO
LEAD_CALIFICADO ──formalizar_cliente()──► CLIENTE
              (bloqueante: requiere FiscalProfile.rfc)

PROSPECTO │
LEAD      │──archivar_sin_exito()──► NO_CIERRE
LEAD_CAL. │    (nota motivo obligatoria)

NO_CIERRE ──reactivar_historico()──► PROSPECTO
```

**Service Layer (`fsm_services.py`)** — `procesar_transicion_fsm()`:

| Acción `data['accion']` | Comportamiento |
|---|---|
| `VALIDAR` | Aplica identidad atómica + `validar_identidad()` + nota sistema |
| `GUARDAR` | Actualiza campos operativos sin cambiar estatus |
| `CALIFICAR` | Mapea texto→int + `calificar_lead()` si está en LEAD |
| `AGENDAR` | Calcula `plan` (≤30d=SEGUIMIENTO, >30d=EN_ESPERA) |
| `AGREGAR_NOTA` | Appends al JSONB de notas |
| `CERRAR_VENTA` | Crea `FiscalProfile` + `formalizar_cliente()` + genera .docx |
| `DESCARTAR` | Marca plan=DESCARTADO, sin cambiar estatus |
| `DESECHAR` | Hard delete (solo Prospectos) |

---

## 6. Capa de Servicio MDM (Master Data Management)

### 6.1 MDM v2 — `services/mdm_service.py` → `resolver_identidad()`

Punto central de aduana para **evitar duplicados** en alta manual, ingesta masiva e ingesta express.

**Entidad INDIVIDUAL (similitud de nombre ≥ 0.85 via `difflib.SequenceMatcher`):**

```
1. Filtrar leads por especialidad + ubicación
2. Para cada lead candidato, calcular similitud de nombre
3. Si similitud > 0.85 → MATCH (retorna lead existente + teléfono alternativo)
4. Si no hay match por nombre, verificar colisión de teléfono puro
5. Si teléfono ya existe en otro lead → raise ValueError (bloqueo)
6. Si ningún match → retorna (None, None) = registro nuevo
```

**Entidad CORPORATIVA (igualdad exacta de nombre normalizado por ciudad):**

```
1. Filtrar clínicas por ubicacion_obj
2. Comparar nombres normalizados (sin acentos, minúsculas)
3. Si match → retorna clínica existente
4. Si teléfono colisiona con otra clínica → raise ValueError
5. Si no → crea nueva Clinica en BD
```

### 6.2 MDM legacy — `mdm_services.py` → `evaluar_duplicidad_estricta()`

Algoritmo alternativo basado en **Cuarteta** (Nombre+Teléfono+Especialidad+Ubicación) para validaciones en ingesta masiva de archivos.

---

## 7. Exportación XLSX

> Funcionalidad añadida en commit `8488718`

### Helper compartido: `generar_respuesta_xlsx(queryset, nombre_archivo)`

```python
# Ubicación: leads/views.py (aprox. línea 1223)
# Dependencias: openpyxl.Workbook, Font, PatternFill, Alignment

# Columnas exportadas (12):
HEADERS = [
    "Nombre Completo", "Telefono", "Celular", "Email",
    "Estatus", "Calificacion", "Producto", "Especialidad",
    "Ciudad", "Vendedor", "Fecha Registro", "Notas"
]

# Anchos (chars): [32,14,14,28,18,14,24,24,18,16,16,60]
# Encabezado:  Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1E3A5F")
# Notas:       Concatena todas las notas del JSONB separadas por " | "
# Calificación: mapeada {3:'Alta', 2:'Media', 1:'Baja'}
```

### Endpoints de exportación

| Rol | URL | Nombre URL | Vista |
|---|---|---|---|
| Vendedor | `/agente/exportar-leads/` | `agente_exportar_leads` | `agente_exportar_leads_view()` |
| Director | `/director/directorio/exportar/` | `director_directorio_exportar` | `director_directorio_exportar_view()` |

**Agente:** respeta `filtro` (`activos/frescos/hoy/urgentes`) y `q` (búsqueda). Nombre archivo: `mis_leads_<username>.xlsx`

**Director:** respeta `q`, `vendedor_id`, `estatus`, `calificacion`. Nombre archivo: `directorio_leads.xlsx`

---

## 8. Motor de Alertas Proactivo

**Comando:** `python manage.py generar_alertas`
**Scheduler:** Django Q2 (Redis broker), ejecutado diariamente

### 5 Reglas evaluadas

| # | Tipo | Condición | Destinatario |
|---|---|---|---|
| 1 | `reactivacion` | `next_action_date <= hoy` en leads activos | Vendedor owner |
| 2 | `estancamiento` | `updated_at < hoy - 7 días` en leads activos | Vendedor owner |
| 3 | `capacitacion` | `TrackingPostVenta.capacitacion_dada=False` y `created_at ≤ hoy-8d` | Vendedor owner |
| 4 | `calidad` | `TrackingPostVenta.calidad_hecha=False` y `created_at ≤ hoy-180d` | Vendedor owner |
| 5 | `mantenimiento` | Última `VentaTransaccional(SERVICIO).fecha_venta ≤ hoy-540d` | Vendedor owner |

**Lógica de deduplicación:** `crear_si_no_existe()` verifica `Notificacion.objects.filter(lead, tipo, leida=False)` antes de crear — nunca genera alertas duplicadas.

### Context Processor Global

`leads.context_processors.contador_alertas` inyecta en **cada request**:
- `notificaciones_no_leidas` → count para el badge de la campana
- `lista_alertas` → las 5 más recientes (para el dropdown)

### Auto-resolución (apagado silencioso)

| Acción del vendedor | Alerta que se apaga |
|---|---|
| Avanzar FSM (`VALIDAR`, `CALIFICAR`) | `reactivacion`, `estancamiento` |
| Marcar `capacitacion_dada=True` | `capacitacion` |
| Marcar `calidad_hecha=True` | `calidad` |
| Registrar `VentaTransaccional(SERVICIO)` | `mantenimiento` |

---

## 9. Autenticación y Seguridad RBAC

### Login Dual

`AUTHENTICATION_BACKENDS` configurado en orden:
1. `users.backends.EmailAuthBackend` — verifica `User.email` primero
2. `django.contrib.auth.backends.ModelBackend` — fallback por `username`

### RBAC — Decorador `@role_required`

```python
# users/permissions.py
@role_required(['VENDEDOR'])           # Solo agentes
@role_required(['DIRECTOR', 'ADMIN'])  # Dirección
@role_required(['VENDEDOR', 'DIRECTOR', 'ADMIN'])  # Todos los autenticados
```

Verifica `request.user.profile.rol` (campo en `UserProfile`). Lanza `PermissionDenied` (HTTP 403) si no coincide.

### `LeadOwnershipMixin`

```python
# leads/mixins.py
# Aplicado en DashboardAgenteView y FichaTrabajoView
# Garantiza que get_queryset() filtre por owner=request.user
# Protege contra acceso cruzado entre vendedores
```

### Mantenimiento — `MaintenanceModeMiddleware`

```python
# config/middleware.py
# Detecta: BASE_DIR/mantenimiento.flag
# Responde: HTTP 503 con maintenance.html
# Excluye: /admin/,  /static/, /media/
# Lee hasta 200 chars del archivo como mensaje personalizado
```

---

## 10. URL Routing

**Archivo:** `config/urls.py` (84 líneas)

| Prefijo | Tipo | Descripción |
|---|---|---|
| `/login/`, `/logout/` | Function View | Auth dual |
| `/dashboard/agente/` | Class View | `DashboardAgenteView` (VENDEDOR) |
| `/agente/ventas-360/` | Class View | `Ventas360View` (VENDEDOR) |
| `/agente/exportar-leads/` | Function View | XLSX Export Vendedor ← **NEW** |
| `/agente/staging/` | Class View | `AgenteStagingListView` |
| `/trabajo/<uuid>/` | Class View | `FichaTrabajoView` |
| `/director/dashboard/` | Function View | `director_dashboard_view` |
| `/director/directorio/` | Function View | `director_directorio_view` |
| `/director/directorio/exportar/` | Function View | XLSX Export Director ← **NEW** |
| `/director/buscar/` | Function View | `director_busqueda_view` |
| `/director/rescate/` | Function View | `bandeja_rescate_view` |
| `/director/fidelizacion/` | Function View | `dashboard_fidelizacion_view` |
| `/director/eventos/` | Function View | `director_eventos_view` |
| `/director/staging/` | Class View | `ListaStagingView` |
| `/director/ingesta-historica/` | Class View | `IngestaHistoricaView` |
| `/director/ingesta-express/` | Class View | `IngestaHistoricaExpressView` |
| `/director/territorios/` | Function View | `panel_territorios` |
| `/api/alta-manual/` | Function View POST | Alta rápida |
| `/api/lead/<uuid>/actualizar/` | Function View POST | FSM transitions |
| `/api/alerta/<id>/atender/` | Function View POST | Marcar alerta |
| `/api/hito-postventa/<uuid>/` | Function View POST | Hitos fidelización |
| `/api/reasignar-lead/` | Function View POST | Director reasigna |
| `/api/venta-extra/` | Function View POST | VentaTransaccional |
| `/api/eventos/crear/` | Function View POST | Nuevo evento |
| `/admin/` | Django Admin | Panel sys admin |

---

## 11. Ingesta Masiva — Pipeline de Datos

```
Archivo Excel/CSV
      │
      ▼
IngestaHistoricaView.POST (pandas read_excel/read_csv)
      │
      ▼
parser_service.orquestar_ingesta_historica(dry_run=True)
      │
      ├── Para cada fila:
      │     ├── Normalizar columnas
      │     ├── MDM: evaluar_duplicidad_estricta()
      │     │     ├── NUEVO       → se puede crear CoreLead
      │     │     ├── DUPLICADO   → fusión silenciosa o nota
      │     │     ├── COMPARTIDO  → teléfono compartido, cuidado
      │     │     └── ERROR       → teléfono inválido → LeadStaging
      │     └── Conflictos → LeadStaging(estatus='PENDIENTE', origen='HISTORICO')
      │
      ▼
Reporte (dry_run=True):
  { clinicas_identificadas, individuos_atomizados, errores_criticos, ... }
      │
      ▼ (usuario confirma)
orquestar_ingesta_historica(dry_run=False) → commit real en DB
      │
      ▼
Archivo temporal eliminado del filesystem
```

---

## 12. Django Q2 — Configuración del Cluster

```python
Q_CLUSTER = {
    'name': 'crm_laser_cluster',
    'workers': 4,          # Procesos paralelos
    'recycle': 500,        # Tareas antes de reciclar worker
    'timeout': 60,         # Segundos máximos por tarea
    'compress': True,
    'save_limit': 250,     # Historial de resultados
    'queue_limit': 500,
    'cpu_affinity': 1,
    'redis': os.environ.get('REDIS_URL', 'redis://redis:6379/1')
}
```

**Servicio en producción:** contenedor `crm_ls_qcluster` (restart: unless-stopped)

---

## 13. Variables de Entorno (`.env`)

| Variable | Uso | Default dev |
|---|---|---|
| `SECRET_KEY` | Django SECRET_KEY | insecure-default |
| `DEBUG` | True/False | True |
| `ALLOWED_HOSTS` | Lista separada por comas | 127.0.0.1,localhost |
| `POSTGRES_DB` | Nombre de la BD | crm_ls |
| `POSTGRES_USER` | Usuario PostgreSQL | crm_user |
| `POSTGRES_PASSWORD` | Contraseña | crm_password |
| `POSTGRES_HOST` | Host del servicio db | db |
| `POSTGRES_PORT` | Puerto | 5432 |
| `REDIS_URL` | URL Redis para Django Q | redis://redis:6379/1 |

---

## 14. Internacionalización

```python
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_TZ = True
```

Todas las fechas se manejan con `localtime(now())` (no `datetime.now()`) para garantizar hora correcta en zona MX en logs, notas JSONB y filtros de dashboard.

---

## 15. Comandos de Administración

| Comando | Descripción |
|---|---|
| `python manage.py generar_alertas` | Ejecuta el motor proactivo de 5 reglas |
| `python manage.py migrar_catalogos` | Seed inicial de especialidades y productos |
| `python manage.py seed_ladas_mexico` | Carga catálogo IFT nacional de claves LADA |
| `python manage.py collectstatic` | Compila archivos estáticos para producción |
| `python manage.py migrate` | Aplica migraciones de BD |
| `python manage.py qcluster` | Inicia el worker de Django Q2 |

---

*Documento generado conforme al DDS 2.1. Actualizar con cada release que modifique modelos, URLs o service layer.*
