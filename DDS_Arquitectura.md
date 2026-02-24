# DOCUMENTO DE DISEÑO DE SOFTWARE (DDS) VERSIÓN 2.0 {documento-de-diseño-de-software-dds-versión-2.0}

**Proyecto:** CRM Láser Systems

**Versión ERS Base:** 4.3

**Fecha:** Enero 2026

**Estado:** DEFINITIVO PARA IMPLEMENTACIÓN

## 1. INTRODUCCIÓN Y ALCANCE {introducción-y-alcance}

Este documento define la arquitectura técnica estricta para el CRM Láser Systems. Se prioriza la integridad de los datos, la seguridad por roles (RBAC) y la escalabilidad mediante contenedores.

### 1.1 Objetivos de Arquitectura {objetivos-de-arquitectura}

1.  **Integridad de Datos:** Garantizar que la identidad del Lead (Teléfono, Nombre) sea inmutable una vez validada (Fase 2).

2.  **Seguridad (RBAC):** Implementar un esquema de permisos donde solo el Administrador tiene capacidades destructivas (\"Hard Delete\").

3.  **Observabilidad:** Separar las vistas de Operación (Vendedor) de las de Análisis (Director).

4.  **Portabilidad:** Infraestructura basada 100% en Docker Compose sobre Linux.

### 1.2 Stack Tecnológico {stack-tecnológico}

- **Backend:** Python 3.11 + Django 5.0 (API REST & MVT).

- **Base de Datos:** PostgreSQL 16 (Uso híbrido Relacional + JSONB).

- **Frontend:** Django Templates + htmltemplate + Bootstrap 5 + LuckySheet (JS) + Chart.js.

- **Colas y Caché:** Redis + Django Q (Scheduler).

- **Infraestructura:** Docker Compose (Nginx + Gunicorn + Postgres + Redis).

## 2. DICCIONARIO DE DATOS {diccionario-de-datos}

### 2.1 Entidad Núcleo: CoreLead {entidad-núcleo-corelead}

Representa el átomo del sistema. Ningún campo puede ser modificado sin respetar las reglas de inmutabilidad por fase.

| **Campo**              | **Tipo SQL** | **Regla de Negocio / Restricción**             | **Comportamiento Fase 1** | **Comportamiento Fase 2** |
|------------------------|--------------|------------------------------------------------|---------------------------|---------------------------|
| **id**                 | UUID         | Primary Key (Interna).                         | \-                        | \-                        |
| **phone_primary**      | VARCHAR(15)  | **Unique Key**. Sanitizado (solo nums).        | Editable                  | **BLOQUEADO**             |
| **celular**            | VARCHAR(15)  | **Unique Key**. Sanitizado (solo nums).        | Editable                  | **BLOQUEADO**             |
| **nombre**             | VARCHAR(100) | Nombre del Dr. o Clínica.                      | Editable                  | **BLOQUEADO**             |
| **especialidad**       | VARCHAR(50)  | Texto libre (Búsqueda indexada).               | Editable                  | **BLOQUEADO**             |
| **ubicacion_id**       | FK (Int)     | Relación a CatUbicacion.                       | Editable                  | **BLOQUEADO**             |
| **producto_interes**   | VARCHAR(50)  | Nombre de equipo                               | Editable                  | **BLOQUEADO**             |
| **email**              | EMAIL        | Opcional al inicio.                            | Editable                  | Editable                  |
| **Dirección_completa** | VARCHAR(255) | Calle, col. cp                                 | Editable                  | Bloqueado                 |
| **estatus**            | VARCHAR(20)  | **Enum:** PROSPECTO, LEAD, CLIENTE, NO_CIERRE. | Trigger                   | Trigger                   |
| **calificacion**       | INT          | **Enum:** 0:SIN, 1:BAJA, 2:MEDIA, 3:ALTA.      | Editable                  | Editable                  |
| **plan**               | VARCHAR(20)  | **Enum:** SEGUIMIENTO, EN_ESPERA, DESCARTADO.  | Editable                  | Editable                  |
| **next_action_date**   | DATE         | Requerido si Plan != Descartado.               | Editable                  | Editable                  |
| **notas_variadas**     | JSONB        | Historial acumulativo (Append-Only).           | Append                    | Append                    |
| **owner_id**           | FK (User)    | Dueño del registro.                            | Auto                      | Bloqueado                 |

### 

### 2.2 Entidades Satélite {#entidades-satélite}

- **FiscalProfile (1:1 con Lead):** Se crea SOLO al cierre. Campos: RFC (Regex), Razón Social, Régimen, Dirección Fiscal Completa.

- **SalesGoal:** Metas por vendedor. Campos: user_id, periodo (Mensual/Anual), monto_meta, fecha_inicio, fecha_fin.

- **CatUbicacion:** Catálogo geográfico. Campos: ciudad, estado, region, activo.

- **LeadDisput:** Gestión de conflictos. Campos: lead_id, claimant_user, status, resolution_notes.

#### 2.3 Entidad de Usuarios: UserProfile {#entidad-de-usuarios-userprofile}

Extensión del modelo de usuario nativo de Django (auth_user) para manejar la lógica de negocio sin tocar el núcleo del framework.

| **Campo**            | **Tipo**      | **Regla de Negocio / Restricción**                                                                         |
|----------------------|---------------|------------------------------------------------------------------------------------------------------------|
| **user_id**          | OneToOne (FK) | Relación 1:1 estricta con auth_user. PK Lógica.                                                            |
| **rol**              | VARCHAR(20)   | **Enum:** VENDEDOR, DIRECTOR, ADMIN. Define permisos (Scope).                                              |
| **zona_asignada_id** | FK (Opcional) | Relación con CatUbicacion. Filtrado de leads.                                                              |
| **telefono**         | VARCHAR(15)   | Contacto interno.                                                                                          |
| **color_identidad**  | VARCHAR(7)    | Código Hex (ej. \#FF5733) para diferenciar sus leads en calendarios/mapas compartidos.                     |
| **meta_mensual**     | INT           | Cantidad de Leads convertidos a Clientes esperada por mes.                                                 |
| **is_active**        | BOOL          | **Soft Delete:** Si es False, el usuario no puede entrar, pero sus leads históricos se mantienen intactos. |

## 

## 3. LÓGICA DE NEGOCIO: CICLO DE VIDA (LAS 3 FASES) {lógica-de-negocio-ciclo-de-vida-las-3-fases}

El sistema no utiliza \"modos\" manuales. El comportamiento de la interfaz y la API cambia automáticamente según el estatus.

### FASE 1: CAPTURA Y LIMPIEZA (\"El Barrido\")

- **Disparador:** estatus == PROSPECTO.

- **Interfaz:** LuckySheet (Vista Tabular Editable) o Carga Masiva.

- **Operativa:**

  - Edición libre de todos los campos.

  - **Ruta Basura:** Permiso de DELETE físico para registros inválidos.

  - **Transición:** Al cambiar a LEAD (Validado), se dispara el **Bloqueo de Identidad**.

### FASE 2: TRABAJO Y NEGOCIACIÓN (\"El Tratamiento\")

- **Disparador:** estatus == LEAD o LEAD_CALIFICADO.

- **Interfaz:**

  - **LuckySheet:** Modo Solo Lectura (Índice de navegación).

  - **Ficha Individual:** Modal/Página para gestión detallada.

- **Candado de Integridad:**

  - **Bloqueado:** Teléfono, Nombre, Especialidad, Ubicación, Producto.

  - **Editable:** Notas, Citas, Email, Plan, Calificación.

- **Regla \"Lead Tratado\":** Para avanzar a este sub-estado, es obligatorio asignar una **Calificación** (Baja/Media/Alta).

- **Automatización:** Si plan == EN_ESPERA y se cumple la fecha, el sistema lo regresa a SEGUIMIENTO automáticamente.

### FASE 3: CIERRE O ARCHIVO (\"La Formalización\")

- **Disparador:** Cambio a CLIENTE.

- **Validación Bloqueante:** Requiere FiscalProfile completo.

- **Generación de Pedido:** Wizard que captura condiciones financieras (Plazos, Anticipo) y genera PDF .

- **Estado Final:** Inmutable para el vendedor (salvo notas_variadas para soporte).

## 4. DISEÑO DE MÓDULOS FUNCIONALES {#diseño-de-módulos-funcionales}

4.1 Módulo de Ingesta y Adaptador (M1) --- Actualizado

Este módulo implementa el patrón **Adapter** para procesar fuentes externas (actualmente Excel/CSV) y transformarlas en entidades CoreLead bajo un estricto protocolo de arbitraje.

+1

Protocolo de ingesta y De duplicación (Los 5 Casos)

Al procesar un registro, el sistema validará el nombre y phone_primary y aplicará las siguientes reglas en orden de prelación:

1.  **Caso A (Registro Nuevo):**

    - **Condición:** El teléfono no existe en la base de datos.

    - **Acción:** Crear registro con estatus PROSPECTO.

    - **Asignación:** El sistema asigna el owner_id basándose en el vendedor que esta haciendo la ingesta o si es el director el mismo lo dispone.

2.  **Caso B (A quien le pertenece ya el lead activo):**

    - **Condición:** El teléfono existe, pertenece a otro owner y tiene una antigüedad de gestión \< 1 año.

    - **Acción:** No duplica el registro. Aviso de quien es el owner.

3.  **Caso D (Cliente Histórico):**

    - **Condición:** El teléfono existe y su estatus actual es CLIENTE.

    - **Acción:** El sistema ignora la carga como prospecto nuevo y se deja una nota en el historico.

4.  **Caso E (Reactivación de Registros Antiguos):**

    - **Condición:** El teléfono existe (en estatus PROSPECTO, LEAD o NO_CIERRE), pero su última actividad es **\> 1 año**.

    - **Acción:** El registro se marca para **Revisión Manual**. El vendedor puede visualizar el historial previo y decidir si reactiva al prospecto bajo su propiedad

### 4.2 Módulo de Alertas y Retención (M7) {módulo-de-alertas-y-retención-m7}

**Tecnología:** Django Q (Scheduler) + Redis.

- **Rutina Diaria (01:00 AM):**

  1.  **Regla 1/10:** Alerta si Lead \< 30 días no es Cliente.

  2.  **Reactivación:** Si En Espera llega a su fecha \$\rightarrow\$ Pasa a Seguimiento.

  3.  **Fidelización:** T+8 días (Capacitación), T+30 (Encuesta), T+18 Meses (Mantenimiento).

- **Salida:** Notificaciones en Dashboard (Badges), no emails externos.

  4.2.1 Avisos eventuales a clientes selectos en fechas determinadas en el futuro (talleres, expos, etc).

### 4.3 Módulo de Reportes (M5 - Director) {módulo-de-reportes-m5---director}

**Tecnología:** DataTables (Server-side rendering) + Chart.js.

1.  **Informe Semanal:** Conteo de validaciones (Prospecto \$\rightarrow\$ Lead).

2.  **Forecast Mensual:** Suma de Leads Tratados (Calif Media/Alta) con cierre en mes corriente.

3.  **Embudo de Conversión:** Gráfico de pasos.

4.  **Bandeja de Rescate:** Leads En Espera o No Cierre antiguos.

### 4.4 Módulo de Seguridad y Roles (M10 - RBAC) {#módulo-de-seguridad-y-roles-m10---rbac}

- **Vendedor:** Scope local (owner_id). LuckySheet Editable (F1) / Lectura (F2). Sin permiso de borrar en F2/F3.

- **Director:** Scope Global (Read-only identidad). Acceso a Dashboard de KPIs y Panel de Disputas.

- **Administrador:** Acceso Total (Django Admin). Permiso de Hard Delete y corrección de campos bloqueados.

## 5. DIAGRAMAS DE ARQUITECTURA {#diagramas-de-arquitectura}

### 5.1 Diagrama Entidad-Relación (ERD) {#diagrama-entidad-relación-erd}

erDiagram

%% \-\-- GESTIÓN DE USUARIOS (AUTONOMÍA DIRECTOR) \-\--

AUTH_USER \|\|\--\|\| USERS_PROFILE : \"tiene_perfil\"

USERS_PROFILE {

int user_id FK

string rol \"Enum: VENDEDOR, DIRECTOR, ADMIN\"

string telefono

string color_identidad

int meta_clientes_mensual \"CANTIDAD (No Dinero)\"

bool is_active

}

%% \-\-- TERRITORIOS (M2M - LISTAS) \-\--

USERS_PROFILE \|\|\--o{ ASIGNACION_TERRITORIO : \"se_le_asigna\"

CAT_UBICACION \|\|\--o{ ASIGNACION_TERRITORIO : \"es_cubierta_por\"

ASIGNACION_TERRITORIO {

int id PK

int user_profile_id FK

int ubicacion_id FK

timestamp fecha_asignacion

}

CAT_UBICACION {

int id PK

string ciudad

string estado

bool is_active

}

%% \-\-- OPERACIÓN \-\--

AUTH_USER \|\|\--o{ SALES_GOAL : \"historial_metas\"

AUTH_USER \|\|\--o{ CORE_LEAD : \"es_dueño_de\"

CAT_UBICACION \|\|\--o{ CORE_LEAD : \"ubicacion_lead\"

SALES_GOAL {

int id PK

int user_id FK

date periodo_inicio

date periodo_fin

int cantidad_objetivo \"Meta Numérica\"

}

%% \-\-- EL LEAD \-\--

CORE_LEAD {

uuid id PK

int owner_id FK

int ubicacion_id FK

varchar phone_primary UK

varchar celular

varchar nombre

varchar especialidad

varchar producto

varchar email

varchar dirección_completa

varchar estatus

int calificacion

varchar plan

jsonb notas_variadas

}

%% \-\-- SATÉLITES \-\--

CORE_LEAD \|\|\--o\| FISCAL_PROFILE : \"factura_a\"

FISCAL_PROFILE {

uuid lead_id FK

varchar rfc

varchar razon_social

varchar regimen_fiscal

varchar calle

varchar colonia

varchar ciudad

varchar estado

varchar cp

}

%% \-\-- CONFLICTOS Y ARBITRAJE (¡LA PIEZA QUE FALTABA!) \-\--

CORE_LEAD \|\|\--o{ LEAD_DISPUTE : \"tiene_conflictos\"

AUTH_USER \|\|\--o{ LEAD_DISPUTE : \"reclama\"

LEAD_DISPUTE {

int id PK

uuid lead_id FK

int claimant_user_id FK \"Quien reclama la propiedad\"

string tipo_conflicto \"Enum: DUPLICADO_IMPORT, RECLAMO_MANUAL\"

string status \"Enum: PENDIENTE, RESUELTO, RECHAZADO\"

text notas_resolucion \"Justificación del Director\"

timestamp created_at

}

### 5.2 Diagrama de Estados: Ciclo de Vida del Lead {#diagrama-de-estados-ciclo-de-vida-del-lead}

Este diagrama muestra las transiciones legales y los bloqueos por Fase.

stateDiagram-v2

direction LR

%% FASE 1: CAPTURA

state \"Fase 1: Prospecto\" as F1 {

\[\*\] \--\> PROSPECTO : Ingesta (Excel/Manual)

PROSPECTO \--\> PROSPECTO : Edición Libre / Limpieza

}

%% TRANSICIÓN

PROSPECTO \--\> LEAD : Validación (Bloqueo Identidad)

PROSPECTO \--\> \[\*\] : Hard Delete (Basura)

%% FASE 2: TRABAJO

state \"Fase 2: Trabajo (Candado Activo)\" as F2 {

LEAD \--\> LEAD_TRATADO : Envío Info + Calif

state \"Plan de Acción\" as Plan {

LEAD_TRATADO \--\> EN_ESPERA : \"Búscame en 6 meses\"

EN_ESPERA \--\> SEGUIMIENTO : Trigger Automático (Fecha)

SEGUIMIENTO \--\> LEAD_TRATADO : Gestión

LEAD_TRATADO \--\> EN_ESPERA : "Pausar / Agendar"
Regla de Gestión de Tiempo (Agendar/Pausar):
	Al establecer una `next_action_date` en un LEAD, el sistema evalúa automáticamente el plazo:
	* Corto Plazo (<= 30 días): El `plan` permanece en SEGUIMIENTO. El lead sigue considerándose "caliente" y activo en el embudo diario.
	* Largo Plazo (> 30 días): El `plan` transiciona automáticamente a EN_ESPERA. El lead sale del radar inmediato para limpiar el dashboard.

}

}

%% FASE 3: CIERRE

state \"Fase 3: Formalización\" as F3 {

LEAD_TRATADO \--\> CLIENTE : Pago + Datos Fiscales

LEAD_TRATADO \--\> NO_CIERRE : Rechazo Definitivo

LEAD_TRATADO \--\> DESCARTADO : Sin Interés

}

CLIENTE \--\> \[\*\] : Post-Venta

### 5.3 Diagrama de Componentes: Ingesta. {#diagrama-de-componentes-ingesta.}

Muestra cómo entra la información masiva y cómo se resuelven los conflictos.

flowchart TD

Start(\[Inicio: Carga de Archivo Excel/CSV\]) \--\> Adapter\[Adaptador: Mapeo y Sanitización de Campos\]

Adapter \--\> Loop{¿Hay más filas?}

Loop \-- SÍ \--\> PhoneCheck{¿Teléfono ya existe en DB?}

%% CASO A: Registro Nuevo

PhoneCheck \-- NO \--\> CaseA\[CASO A: Crear Nuevo CORE_LEAD\]

CaseA \--\> ZoneAssign\[Asignar Dueño automáticamente según CatUbicacion\]

ZoneAssign \--\> NextRow\[Siguiente Fila\]

%% CASOS CON REGISTRO EXISTENTE

PhoneCheck \-- SÍ \--\> OwnerCheck{¿Mismo Dueño?}

%% CASO B y D: Es el mismo dueño

OwnerCheck \-- SÍ \--\> StatusCheck{¿Es CLIENTE?}

StatusCheck \-- SÍ \--\> TimeCheckD{¿Antigüedad \> 1 año?}

TimeCheckD \-- SÍ \--\> CaseD\[CASO D: Notificar CLIENTE HISTÓRICO - Up-selling\]

TimeCheckD \-- NO \--\> CaseB\[CASO B: Actualizar Historial JSON - Append Note\]

CaseD \--\> NextRow

CaseB \--\> NextRow

%% CASO C y E: Dueño distinto (Conflicto o Reactivación)

OwnerCheck \-- NO \--\> TimeCheckE{¿Antigüedad \> 1 año?}

TimeCheckE \-- SÍ \--\> CaseE\[CASO E: Registro Liberado - Revisión Manual e Historial\]

TimeCheckE \-- NO \--\> CaseC\[CASO C: BLOQUEAR CARGA y Crear LeadDispute\]

CaseE \--\> NextRow

CaseC \--\> NextRow

Loop \-- NO \--\> End(\[Fin: Notificar Resumen de Carga\])

## 6. INFRAESTRUCTURA Y ESTÁNDARES {#infraestructura-y-estándares}

### 6.1 Dockerización (Docker Compose) {#dockerización-docker-compose}

Entorno idéntico Dev/Prod sobre Linux (Ubuntu/Debian).

- **Web:** Django + Gunicorn (Puerto 8000).

- **DB:** PostgreSQL 16 (Persistencia en Volumen).

- **Worker:** Django Q Cluster.

- **Broker:** Redis.

### 6.2 Estándares de Código (Buenas Prácticas) {#estándares-de-código-buenas-prácticas}

1.  **Gestión de Secretos:** Archivo .env (No trackeado en Git).

2.  **Control de Versiones:** Git + .gitignore robusto (Python/Django).

3.  **Dependencias:** requirements.txt congelado.

4.  **Formato:** Uso de **Black** para auto-formateo.

5.  **Fixtures:** Carga inicial de datos para CatUbicacion y Productos y Core_leads.

6.  **Ambiente virtual.** Usar virtual enviroment para el proyecto.

7\. **Modularización:** Los módulos funcionales que integran esta solución son los siguientes:

**1. Gestión de Datos y Centralización**

Su propósito es unificar la información que actualmente reside en archivos Excel dispersos en una **única base de datos centralizada**.

• **Importación Masiva:** Permite cargar listas de prospectos y clientes desde archivos CSV o Excel.

• **Integridad de Datos:** Valida automáticamente duplicados por nombre o teléfono y genera reportes de registros aceptados o rechazados.

**2. Ventas (Gestión del Pipeline)**

Este módulo es el corazón de la labor comercial diaria y busca dimensionar el trabajo realizado.

• **Pipeline Visual:** Muestra un embudo de ventas por vendedor, clasificado en etapas claras: Prospecto, Seguimiento, Negociación y Cierre.

• **Calificación:** Permite segmentar y filtrar la base de datos por **especialidad médica y ubicación, además de darle al lead estatus y** .plan de acción.

**3. Prospección Asistida**

- **Sugerencias Automatizadas:** Complementa la búsqueda manual del vendedor con sugerencias basadas en zonas y especialidades específicas.

**4. Acceso y Movilidad**

Garantiza que la información esté disponible para los vendedores que trabajan fuera de la oficina.

• **Diseño Adaptativo (*Responsive*):** El sistema es accesible vía navegador móvil, permitiendo el **registro y consulta de datos en tiempo real** desde el campo.

**5. Reportes y Analítica de Productividad**

Enfocado en el monitoreo del desempeño y la toma de decisiones basada en datos.

• **Plan de Ventas Mensual:** Genera informes automáticos que integran solo a los *leads* calificados para cierre en el periodo actual.

• **KPIs de Ventas:** Mide el volumen de trabajo, tasas de rechazo y efectividad de cierre por ejecutivo.

**6. Operación y Automatización Administrativa**

Su meta es agilizar el proceso de cierre y reducir la carga administrativa del vendedor.

• **Generación de Pedidos:** El sistema crea automáticamente formatos de pedido pre-llenados con los datos del cliente desde la base central.

**7. Retención y Seguimiento Sistemático**

Diseñado para asegurar que ningún cliente potencial sea olvidado.

• **Alertas de Seguimiento:** Programación de tareas y recordatorios automáticos para llamadas o contacto.

• **Flujos de Post-Venta:** Genera alertas para verificar la calidad del servicio y detectar oportunidades de renovación o mantenimiento de equipos.

**8. Adopción y Usabilidad**

Módulo crítico para reducir la resistencia al cambio del personal de ventas.

• **Interfaz Familiar:** Presenta vistas de lista **tipo Excel** con capacidad de edición rápida.

**9. Fidelización (Visión 360°)**

Ataca directamente la debilidad de la \"venta única\" (D1) fomentando la recurrencia.

• **Ficha Integral:** Muestra el **historial completo de interacciones** y el inventario de equipos adquiridos por cada cliente.

**10: Gestión de Acceso, Roles y Restricciones**

**1. Autenticación y Control de Ingreso**

• **Acceso mediante Credenciales:** El sistema controlará el ingreso y lo permitirá únicamente a usuarios autorizados mediante un nombre de usuario (basado en el correo electrónico) y una contraseña encriptada.

• **Validación de Estatus:** Al iniciar sesión, el sistema validará automáticamente si el usuario está activo y si la licencia correspondiente no ha expirado.

**2. Control de Acceso Basado en Roles (RBAC)**

• **Definición de Perfiles:** Se implementará una estructura de roles (ej. Administrador, Gerente de Ventas, Ejecutivo de Ventas) donde cada uno tiene niveles de acceso y privilegios específicos sobre las entidades del sistema (leads, clientes, pedidos).

• **Restricciones de Visibilidad:** Atendiendo la solicitud de la dirección, cada vendedor tendrá visibilidad restringida para ver y gestionar únicamente el seguimiento de los prospectos que tiene asignados.

### **A. Esquema JSONB notas_variadas** {#a.-esquema-jsonb-notas_variadas}

{

\"notas\": \[

{

\"id\": \"uuid\",

\"tipo\": \"contacto\|seguimiento\|llamada\|email\",

\"contenido\": \"texto de la nota\",

\"usuario\": \"user_id\",

\"fecha\": \"ISO8601\"

}

\],


\"columnas_excel_historicas\": {

\"columna_antigua_1\": \"valor\",


}
