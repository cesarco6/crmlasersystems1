# 📘 Manual de Usuario — CRM Laser Systems
> **Versión:** 3.1 · **Último commit cubierto:** `8488718` — *feat: implement agent dashboard with search filtering & XLSX export*
> **Actualizado:** 03 / Mayo / 2026

---

## Tabla de Contenidos

1. [Introducción y Acceso al Sistema](#1-introducción-y-acceso-al-sistema)
2. [Roles y Permisos](#2-roles-y-permisos)
3. [Navegación General](#3-navegación-general)
4. [Módulo Vendedor / Agente](#4-módulo-vendedor--agente)
   - 4.1 [Dashboard Vendedor](#41-dashboard-vendedor)
   - 4.2 [Filtros Rápidos](#42-filtros-rápidos)
   - 4.3 [Buscador Universal](#43-buscador-universal)
   - 4.4 [Exportar a Excel (XLSX)](#44-exportar-a-excel-xlsx)  ← **NUEVO**
   - 4.5 [Nueva Oportunidad — Alta Rápida](#45-nueva-oportunidad--alta-rápida)
   - 4.6 [Ficha de Trabajo](#46-ficha-de-trabajo)
   - 4.7 [Máquina de Estados (FSM)](#47-máquina-de-estados-fsm)
   - 4.8 [Ventas 360](#48-ventas-360)
5. [Módulo Director](#5-módulo-director)
   - 5.1 [Dashboard Directivo](#51-dashboard-directivo)
   - 5.2 [Directorio Maestro](#52-directorio-maestro)
   - 5.3 [Exportar Directorio a Excel (XLSX)](#53-exportar-directorio-a-excel-xlsx)  ← **NUEVO**
   - 5.4 [Bandeja de Rescate](#54-bandeja-de-rescate)
   - 5.5 [Fidelización 360°](#55-fidelización-360)
   - 5.6 [Eventos y Campañas](#56-eventos-y-campañas)
   - 5.7 [Quirófano — Ingesta Histórica](#57-quirófano--ingesta-histórica)
   - 5.8 [Panel de Territorios](#58-panel-de-territorios)
6. [Sistema de Alertas (Campanas)](#6-sistema-de-alertas-campanas)
7. [Ciclo de Vida de un Lead — Las 3 Fases](#7-ciclo-de-vida-de-un-lead--las-3-fases)
8. [Tipos de Entidad y Distinción Visual](#8-tipos-de-entidad-y-distinción-visual)
9. [Modo Oscuro / Claro](#9-modo-oscuro--claro)
10. [Página de Mantenimiento](#10-página-de-mantenimiento)
11. [Errores Comunes y Soluciones](#11-errores-comunes-y-soluciones)

---

## 1. Introducción y Acceso al Sistema

**CRM Laser Systems** es la plataforma de gestión de relaciones con prospectos y clientes para el equipo de ventas de equipamiento médico especializado. Garantiza la trazabilidad completa del proceso de venta bajo una arquitectura de tres fases con inmutabilidad controlada.

### Inicio de Sesión

| Campo | Descripción |
|---|---|
| URL de acceso | `http(s)://<dominio>/login/` |
| Usuario | Nombre de usuario O correo electrónico (ambos válidos) |
| Contraseña | Asignada por el Administrador |

> **Nota:** Si el servidor está en ventana de mantenimiento, serás redirigido automáticamente a una pantalla de aviso. Solo el administrador puede levantar la bandera de mantenimiento.

---

## 2. Roles y Permisos

| Rol | Ícono | Acceso | Restricciones |
|---|---|---|---|
| **Vendedor / Agente** | 🤵 | Dashboard Agente, Ficha de Trabajo, Ventas 360, Ingesta Masiva | Solo ve sus propios leads (`owner_id`) |
| **Director** | 📈 | Dashboard Directivo, Directorio Maestro, Bandeja de Rescate, Fidelización, Eventos, Quirófano, Territorios | Lectura global + gestión táctica |
| **Admin Sys** | 💻 | Todo lo anterior + panel `/admin/` de Django | Acceso completo incluyendo hard-delete |

---

## 3. Navegación General

La barra de navegación superior es persistente en todas las vistas. Incluye:

- **Logo / Inicio** → Regresa al dashboard principal según tu rol.
- **Campana de alertas** 🔔 → Muestra notificaciones pendientes con pulso animado cuando hay alertas activas. Al hacer clic en cada alerta se abre un diálogo que solicita la razón de atención (SweetAlert2) y redirige a la ficha del lead relacionado.
- **Menú de usuario** → Avatar con inicial del nombre, dropdown para cerrar sesión.
- **Botón de tema** → Alterna entre modo oscuro y claro; la preferencia se guarda localmente.

---

## 4. Módulo Vendedor / Agente

### 4.1 Dashboard Vendedor

**Ruta:** `/dashboard/agente/`

El dashboard es el panel operativo central del vendedor. Se compone de tres zonas:

#### Zona 1 — Embudo de Ventas (KPI Cards)

Cinco tarjetas en la parte superior muestran el estado actual de la cartera personal:

| Tarjeta | Color | Métrica |
|---|---|---|
| **Cartera Activa** | Azul primario | Total de leads activos (sin descartados ni clientes) |
| **Prospectos** | Índigo `#6366f1` | Leads en estatus `PROSPECTO` (clic filtra la lista) |
| **Leads** | Ámbar `#f59e0b` | Leads con identidad validada (`LEAD`) |
| **Calificados** | Púrpura `#a855f7` | Leads en `LEAD_CALIFICADO` |
| **Cierres / Mes** | Verde esmeralda `#10b981` | Clientes cerrados en el mes calendario actual |

> Las tarjetas tienen efecto hover con elevación. La tarjeta **Prospectos** es un enlace que aplica el filtro `frescos` automáticamente.

#### Zona 2 — Filtros y Búsqueda

Barra de herramientas con botones de filtro rápido y campo de búsqueda (ver secciones 4.2 y 4.3).

#### Zona 3 — Tabla "Mis Oportunidades"

Listado paginado (7 registros por página) con las columnas:

| Columna | Descripción |
|---|---|
| **Cliente** | Nombre completo + ícono de tipo de entidad + badge de tipo + teléfono |
| **Última Acción** | Fecha `updated_at` |
| **Etapa** | Badge de estatus FSM |
| **Producto** | Producto de interés del catálogo |
| **Cal.** | Calificación: 🔥 Alta / ⭐ Media / 🧊 Baja |
| **Ciudad** | Ubicación del prospecto |
| **Acción** | Botón **Gestionar** → abre la Ficha de Trabajo |

---

### 4.2 Filtros Rápidos

Los botones de filtro aplican vistas predefinidas sobre la cartera activa del vendedor:

| Botón | Parámetro URL | Lógica aplicada |
|---|---|---|
| 📋 **Todos** | `?filtro=activos` | Todos los leads activos (excluye cerrados, descartados e hibernados) |
| 🔵 **Nuevos** | `?filtro=frescos` | Solo leads en estatus `PROSPECTO` |
| 🟡 **Para Hoy** | `?filtro=hoy` | Leads cuya `next_action_date` es hoy |
| 🔴 **Urgentes** | `?filtro=urgentes` | Leads en `SEGUIMIENTO` con fecha de acción vencida |

> **Regla de Hibernación:** Los leads en plan `EN_ESPERA` con `next_action_date` en el futuro no aparecen en ningún filtro, evitando ruido operativo.

---

### 4.3 Buscador Universal

El campo de búsqueda en la parte superior derecha del dashboard permite encontrar **cualquier registro** de la cartera del vendedor, incluyendo históricos y cerrados.

**Campos donde se busca simultáneamente:**
- Nombre, apellido paterno, apellido materno
- Teléfono principal, celular
- Correo electrónico
- Nombre de la clínica asociada

> Cuando hay una búsqueda activa, los filtros rápidos quedan suspendidos y se muestran **todos** los resultados coincidentes sin restricción de estatus. Aparece un botón `✕` para limpiar la búsqueda y regresar al filtro anterior.

---

### 4.4 Exportar a Excel (XLSX)

> 🆕 **Funcionalidad agregada en el último commit** (`8488718`)

El botón **📥 Exportar XLSX** está ubicado junto a los filtros rápidos en el dashboard.

#### ¿Qué exporta?

Exporta exactamente la misma lista que estás viendo en pantalla: **respeta el filtro activo y la búsqueda actual**.

| Condición | Comportamiento de la exportación |
|---|---|
| Sin búsqueda + filtro `activos` | Exporta todos los leads activos del vendedor |
| Sin búsqueda + filtro `hoy` | Exporta solo los leads para hoy |
| Sin búsqueda + filtro `frescos` | Exporta solo prospectos |
| Sin búsqueda + filtro `urgentes` | Exporta leads urgentes vencidos |
| Con búsqueda activa (`q=...`) | Exporta los resultados de búsqueda (incluye históricos) |

#### Columnas del archivo exportado

| # | Columna | Descripción |
|---|---|---|
| 1 | Nombre Completo | Nombre MDM consolidado |
| 2 | Teléfono | Teléfono principal |
| 3 | Celular | Teléfono celular |
| 4 | Email | Correo electrónico |
| 5 | Estatus | Etapa FSM actual |
| 6 | Calificación | Alta / Media / Baja |
| 7 | Producto | Producto de interés |
| 8 | Especialidad | Especialidad médica |
| 9 | Ciudad | Ubicación |
| 10 | Vendedor | Username del agente asignado |
| 11 | Fecha Registro | Fecha de creación del registro |
| 12 | Notas | Bitácora de seguimiento concatenada |

> El archivo se descarga automáticamente con el nombre `mis_leads_<username>.xlsx` con formato profesional (encabezado azul marino, anchos optimizados por columna).

**Endpoint:** `GET /agente/exportar-leads/?filtro=<filtro>&q=<busqueda>`

---

### 4.5 Nueva Oportunidad — Alta Rápida

El botón **+ Nueva Oportunidad** (esquina superior derecha del dashboard) abre el modal de alta rápida.

**Campos del formulario:**

| Campo | Obligatorio | Descripción |
|---|---|---|
| Título de cortesía | No | Dr., Dra., Lic., etc. |
| Nombre(s) | ✅ | Nombre de pila |
| Apellido Paterno | ✅ | |
| Apellido Materno | No | |
| Teléfono Principal | ✅ | Se valida contra MDM para evitar duplicados |
| Celular | No | |
| Email | No | |
| Especialidad | ✅ | Selección de catálogo |
| Producto de Interés | ✅ | Selección de catálogo |
| Ciudad | ✅ | Selección de catálogo |
| Tipo de entidad | ✅ | Médico Independiente / Clínica Corporativa |

> **Protección MDM:** Si el teléfono ya existe en el sistema, la operación es bloqueada con un mensaje de alerta. Esto evita duplicados en la base de datos.

---

### 4.6 Ficha de Trabajo

**Ruta:** `/trabajo/<uuid:pk>/`

La ficha de trabajo es la vista operativa de un lead individual. Desde aquí el vendedor realiza todas las gestiones del proceso de venta.

**Componentes principales:**

- **Encabezado del Lead:** Nombre, tipo de entidad (con badge visual), estatus actual, calificación y producto.
- **Sección de Contacto:** Teléfonos, email, especialidad, ciudad.
- **Candado de Identidad (Fase 2):** Una vez validada la identidad (`Validar Identidad`), nombre y teléfonos quedan **inmutables**. Solo el Director puede modificarlos.
- **Modal de Edición:** Permite actualizar datos no candados: email, calificación, ciudad, producto, plan de seguimiento, fecha de próxima acción.
- **Historial de Notas (Bitácora JSONB):** Registro cronológico de todas las interacciones y cambios de estado. Las notas de tipo `sistema` se generan automáticamente.
- **Botones de Acción FSM:** Cambian el estado del lead siguiendo la máquina de estados.
- **Sección Cierre de Venta:** Disponible cuando el lead está en etapa de cierre (registro de contrato, facturación, datos fiscales).
- **Botón "Validar Identidad":** Requiere una justificación obligatoria antes de ejecutar el cambio de estado.

---

### 4.7 Máquina de Estados (FSM)

El estatus de un lead sigue un flujo controlado. Las transiciones permitidas son:

```
PROSPECTO
    └─► LEAD (requiere "Validar Identidad" + justificación)
            └─► LEAD_CALIFICADO
                    └─► OPORTUNIDAD
                            ├─► CLIENTE (cierre exitoso)
                            └─► NO_CIERRE (descarte por no venta)
```

**Planes de trabajo (estado interno):**

| Plan | Descripción |
|---|---|
| `SEGUIMIENTO` | Lead en proceso activo de contacto |
| `EN_ESPERA` | Lead en pausa hasta una fecha específica (hiberna del dashboard) |
| `DESCARTADO` | Lead removido del flujo activo |

---

### 4.8 Ventas 360

**Ruta:** `/agente/ventas-360/`

Vista independiente con tres pestañas:

| Pestaña | Contenido |
|---|---|
| **🔔 Campañas y Eventos** | Eventos activos asignados al vendedor. Filtros: Todos, Próximos 7 días, Este mes, Finalizados |
| **🏆 Oportunidades 360** | Historial de ventas de servicio/accesorios (VentaTransaccional). Flujo posventa continuo |
| **📦 Históricos** | Leads marcados como `es_historico=True`. No participan en flujos activos |

**KPIs superiores (Ventas 360):**

- Oportunidades totales registradas
- Oportunidades en gestión (PENDIENTE / EN_GESTION)
- Oportunidades concretadas
- Total de históricos en cartera
- Campañas activas asignadas

---

## 5. Módulo Director

### 5.1 Dashboard Directivo

**Ruta:** `/director/dashboard/`

Vista ejecutiva con KPIs globales y gráficas Chart.js:

- Distribución de leads por estatus (dona)
- Rendimiento por vendedor (barras)
- Actividad semanal (líneas)
- Alertas de estancamiento activas
- Leads calificados en el período

---

### 5.2 Directorio Maestro

**Ruta:** `/director/directorio/`

Vista de **todos los leads del sistema** (scope global). Permite filtrar por:

- Búsqueda de texto libre (nombre, apellido, teléfono)
- Vendedor asignado (dropdown)
- Estatus FSM
- Calificación (Alta / Media / Baja)

Paginación de 25 registros por página con navegación compacta de 5 páginas.

---

### 5.3 Exportar Directorio a Excel (XLSX)

> 🆕 **Funcionalidad agregada en el último commit** (`8488718`)

El botón **📥 Exportar XLSX** en el Directorio Maestro exporta **todos los leads** que coincidan con los filtros activos al momento de hacer clic.

**Los filtros respetados son:**
- Búsqueda de texto (`q`)
- Vendedor asignado (`vendedor_id`)
- Estatus FSM (`estatus`)
- Calificación (`calificacion`)

> Si no hay filtros activos, se exportan **todos los registros del sistema**.

El archivo se descarga con el nombre `directorio_leads.xlsx`.

**Endpoint:** `GET /director/directorio/exportar/?q=<q>&vendedor_id=<id>&estatus=<estatus>&calificacion=<cal>`

**Columnas exportadas:** idénticas a la exportación de agente (12 columnas con encabezado azul marino).

---

### 5.4 Bandeja de Rescate

**Ruta:** `/director/rescate/`

Leads en situación crítica que requieren intervención directa del director:

- Leads sin actividad prolongada
- Leads marcados como `NO_CIERRE` pendientes de revisión

Acciones disponibles:
- **Reasignar** → Cambiar el vendedor propietario
- **Desechar** → Mover a estado descartado definitivo

---

### 5.5 Fidelización 360°

**Ruta:** `/director/fidelizacion/`

Dashboard post-venta para el seguimiento de hitos de calidad:

| Hito | Plazo | Descripción |
|---|---|---|
| **Capacitación** | 8 días desde la venta | Verificar que el cliente recibió capacitación en el equipo |
| **Llamada de Calidad** | 180 días desde la venta | Verificar satisfacción y funcionalidad del equipo |
| **Mantenimiento** | Cada 540 días (18 meses) | Recordatorio cíclico de servicio preventivo |

El director puede marcar cada hito como cumplido desde esta vista. Al hacerlo, la alerta correspondiente se apaga automáticamente.

---

### 5.6 Eventos y Campañas

**Ruta:** `/director/eventos/`

Módulo de gestión de eventos comerciales (congresos, exposiciones, campañas de lanzamiento).

**Creación de un evento:**
- Nombre del evento
- Línea de negocio (Equipos, Servicio, Accesorios)
- Fechas de inicio y fin
- Vendedores asignados (multi-select)
- Descripción

Los eventos creados aparecen automáticamente en la pestaña **Campañas** del módulo Ventas 360 de cada vendedor asignado, y generan una notificación en la campana de alertas.

---

### 5.7 Quirófano — Ingesta Histórica

El quirófano es el módulo de limpieza y migración de bases de datos históricas.

#### Ingesta Masiva por Archivo

**Ruta:** `/director/ingesta-historica/`

Proceso en dos pasos:

1. **Simulación:** Sube un archivo `.csv`, `.xls` o `.xlsx`. El sistema analiza cada fila y muestra un reporte de filas válidas, errores críticos y duplicados detectados por MDM.
2. **Confirmación:** Si la simulación es satisfactoria, el director confirma la inyección real. Si cancela, el archivo temporal se elimina de forma segura.

#### Cola de Staging (Procesamiento Fila por Fila)

**Ruta:** `/director/staging/`

Vista de cola con todos los registros `PENDIENTE` de procesamiento histórico. El director puede:
- **Procesar:** Revisa y enriquece cada registro antes de inyectarlo (asignar vendedor, especialidad, ubicación, producto).
- **Descartar:** Elimina el registro de la cola sin inyectarlo.

El sistema redirige automáticamente al siguiente registro pendiente después de cada acción.

#### Ingesta Express (Registro Manual)

**Ruta:** `/director/ingesta-express/`

Alta individual de clientes históricos sin necesidad de archivo. Útil para agregar registros sueltos con protección MDM completa.

---

### 5.8 Panel de Territorios

**Ruta:** `/director/territorios/`

Asignación y visualización de territorios geográficos (catálogo LADA) por vendedor. Permite al director controlar la cobertura regional del equipo de ventas con el catálogo nacional de claves IFT.

---

## 6. Sistema de Alertas (Campanas)

El motor proactivo de alertas (`generar_alertas.py`, programado vía Django Q) genera notificaciones automáticas en cinco escenarios:

| Tipo | Ícono | Disparador |
|---|---|---|
| `reactivacion` | 🔔 | Lead activo con `next_action_date` vencida |
| `estancamiento` | ⏰ | Lead sin modificación por más de 7 días |
| `capacitacion` | 🎓 | Hito de capacitación a los 8 días de la venta |
| `calidad` | ✅ | Hito de calidad a los 180 días de la venta |
| `mantenimiento` | 🔧 | Reloj flotante cada 540 días (18 meses) |

**Cómo atender una alerta:**

1. Haz clic en la campana 🔔 de la barra de navegación.
2. Selecciona la alerta que deseas atender.
3. Ingresa el motivo de atención en el diálogo (obligatorio).
4. El sistema registra la acción en el historial del lead y te redirige a su ficha de trabajo.

**Auto-resolución silenciosa:** Algunas alertas se apagan automáticamente cuando el vendedor realiza la acción natural:
- Avanzar el estado FSM → apaga `reactivacion` y `estancamiento`
- Marcar hito de capacitación → apaga `capacitacion`
- Marcar hito de calidad → apaga `calidad`
- Registrar venta de servicio → apaga `mantenimiento`

---

## 7. Ciclo de Vida de un Lead — Las 3 Fases

```
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 1: CAPTURA ("El Barrido")                                     │
│  - Ingesta masiva o manual                                          │
│  - Edición libre de todos los campos                                │
│  - Hard Delete permitido para registros inservibles                 │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ Transición: PROSPECTO → LEAD
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 2: TRABAJO ("El Tratamiento")                                 │
│  - Candado de Identidad: Nombre y teléfonos inmutables             │
│  - Gestiones de seguimiento, planes, fechas de acción              │
│  - Historial de notas JSONB obligatorio                            │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ Transición: hacia CLIENTE o NO_CIERRE
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 3: CIERRE ("La Formalización")                                │
│  - Datos fiscales obligatorios para facturación                    │
│  - Registro de contrato y datos de venta                           │
│  - Activación de hitos de postventa (Fidelización 360°)            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Tipos de Entidad y Distinción Visual

El sistema distingue tres tipos de prospecto/cliente con íconos y badges específicos:

| Tipo | Ícono | Badge | Descripción |
|---|---|---|---|
| **Médico Independiente** | 👤 (`bi-person-fill`) | `bg-secondary` | Doctor sin afiliación clínica |
| **Médico de Clínica** | 🏥 (`bi-hospital-fill`) | `bg-primary` | Doctor vinculado a una clínica específica |
| **Clínica Corporativa** | 🏢 (`bi-building-fill`) | `bg-info` | Entidad corporativa (sin apellidos individuales) |

Los registros **históricos** (`es_historico=True`) muestran adicionalmente un badge `Histórico` en gris. Estos registros son visibles en la búsqueda pero excluidos de los flujos de trabajo activos.

---

## 9. Modo Oscuro / Claro

El sistema soporta dos temas visuales accesibles desde la barra de navegación:

- **☀️ Modo Claro:** Fondos blancos y colores pastel.
- **🌙 Modo Oscuro:** Fondos oscuros con texto claro, optimizado para largas jornadas de trabajo.

La preferencia se guarda en `localStorage` del navegador y se aplica automáticamente en futuras sesiones. Todos los modales, tablas y componentes respetan ambos temas mediante variables CSS de Bootstrap 5.3.

---

## 10. Página de Mantenimiento

Cuando el Administrador activa la ventana de mantenimiento (creando el archivo `mantenimientonext.flag` en el servidor), todos los usuarios son redirigidos automáticamente a una pantalla de aviso.

Para retornar al sistema, el Administrador debe eliminar o renombrar dicho archivo y reiniciar el servicio.

---

## 11. Errores Comunes y Soluciones

| Error | Causa probable | Solución |
|---|---|---|
| "Colisión detectada" al dar de alta | El teléfono ya existe en el sistema (MDM) | Busca el registro existente con el buscador universal |
| Badge "Histórico" en un lead activo | El lead fue ingresado por el Quirófano | Es esperado; el lead puede gestionarse normalmente |
| Lead no aparece en el dashboard | El lead está en plan `EN_ESPERA` con fecha futura | Usa el buscador universal para encontrarlo y ajustar la fecha |
| Campos de nombre/teléfono no editables | El lead ya está en Fase 2 (Candado de Identidad activo) | Contacta al Director para modificación excepcional |
| Exportación XLSX sin datos | No hay leads que coincidan con el filtro activo | Verifica el filtro/búsqueda activa y vuelve a intentarlo |
| Alerta no desaparece tras atenderla | El motivo de atención estaba vacío | Abre la alerta nuevamente e ingresa un motivo válido |

---

> *CRM Laser Systems fue desarrollado bajo los estándares de confidencialidad para operación en ventas de equipamiento médico especializado. Este manual se actualiza conforme a cada release del sistema.*
