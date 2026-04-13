# Arquitectura de Software: CRM Laser Systems 🚀

**Versión Doc:** 1.0  
**Ubicación:** `backend/docs/avisos_architecture.md`  
**Objetivo:** Este documento traza el esqueleto de diseño de software para ingenieros de desarrollo (Backend & DevOps). Explica *por qué* el CRM Laser Systems está estructurado de esta manera, detallando los paradigmas y Patrones de Diseño implementados para sostener su operación estricta.

---

## 🏗️ 1. Paradigma Metodológico: Modelo-Vista-Template (MVT)

El sistema orbita alrededor de **Django** como framework fundamental, explotando su patrón **MVT** para lograr la inyección bidireccional (Separation of Concerns).

- **M (Modelo):** Componente agnóstico encargado de la persistencia ORM de PostgreSQL (ej. `CoreLead`). Emplea integridad híbrida utilizando columnas determinísticas (`phone_primary`) y columnas no-estructuradas (`JSONB` para `notas_variadas`).
- **V (View - Controlador):** El nexo del flujo (`views.py`). En CRM Laser Systems, nos apegamos a la filosofía *"Skinny Controllers"*: Las vistas únicamente actúan como **Routers HTTP y Gestores de Contexto**. No realizan sanitización masiva; delegan ese trabajo exhaustivo a la Capa de Servicios.
- **T (Template - Vista):** Renderizado servido desde el backend (`.html`), hidratado con lógica temporal y variables estáticas de CSS/JS asíncrono para mantener ligeros los clientes.

---

## 🛠️ 2. Patrones de Diseño de Software Integrados

Para garantizar que el software escala y resiste inyecciones masivas de archivos sin romperse, hemos desacoplado la lógica fuerte usando enfoques puros de *Design Patterns*:

### A) **Service Layer Pattern (Capa de Servicios)**
Históricamente, los CRM en Django colapsan debido a archivos `views.py` masivos (~3,000 líneas). Para mitigar esto, externalizamos toda la manipulación transaccional en el directorio aislante `backend/leads/services/`.
*   **Ejemplos Reales:** `dashboard_services.py` computa las matrices métricas de desempeño; `lead_creation_service.py` valida la inyección atómica de Leads en base de datos. 
*   **Beneficio:** Las vistas quedan extremadamente legibles. Los Servicios pueden ser consumidos tanto por una URL HTTP, como por una consola de comandos, o un Cronjob externo (celery/Django-Q) sin duplicar código.

### B) **Patrón Adapter (Adaptador Estructural)**
Explotado extensivamente en el "Quirófano / Staging". 
Puesto que los Vendedores ingestan *Leads* empleando excels heterogéneos (distintos encabezados, minúsculas, espacios corrompidos), el controlador no asimila eso directamente. Un "Adaptador" toma la sábana irregular, homogeneiza los tipos de celda a Strings de Python estándar y las adapta para insertarlas en un modelo estricto de Pydantic/Django.

### C) **Finite State Machine (FSM - Máquina de Estados Finita)**
La trayectoria transaccional de un prospecto no está liberada al criterio libre del usuario, lo rige una máquina de estados implícita en la lógica de actualización (`fsm_services.py`).
1.  **Fase 1 (Prospecto):** Interfaz editable y efímera (Ruta permitida al Hard Delete).
2.  **Fase 2 (Tratamiento/Lead):** Candado de Integridad encendido. Inmutabilidad de identidad médica. Avance lineal (Pausado o En Espera).
3.  **Fase 3 (Concretado):** Terminus transaccional. Dispara el acoplamiento con entidades Fiscales (Facturación Relacional 1:1).

### D) **Observer / Signals Pattern (Patrón Observador Acoplado)**
Manejamos señales en 2do plano mediante Tareas Asíncronas programadas con `Django-Q` y `Redis` (o nativas de Django Signals para logs). Permite reaccionar (Observer) a la expiración de contratos, cambios de metas de vendedores o transcurso del tiempo de un estado "EN_ESPERA" para despertarlo automáticamente sin saturar el flujo o requerir recargas de ventana por parte de los Vendedores.

---

## 🔐 3. Control de Accesos: Patrón RBAC y Segregación por Middleware

La arquitectura repulsa la autorización horizontal.
A lo largo de los decoradores en `views.py` e implementaciones nativas en `users/permissions.py`, la aplicación ejerce un **Role-Based Access Control (RBAC)** que modula las inyecciones SQL subyacentes (Consultas *Querysets*).

*   **VISTA LOCAL (Ventas):** El Queryset añade implícitamente siempre un `.filter(owner_id=request.user.id)`. Es ciego computacionalmente al resto del ecosistema médico del país.
*   **VISTA GLOBAL (Dirección):** El filtro omite el `owner_id`. Permite agregaciones (`Sum`, `Count`) en vistas como *Directorio Maestro*, *Fidelización 360°*, y otorga capacidad de Resolución de Disputas de Propiedad (MDM Duplication Management).

---

## 📂 Estructura Semántica del Directorio /backend/

```text
📁 backend/
 ├─ 📁 config/                 # Router Maestro, Settings.py, Inyecciones WSGI/ASGI
 ├─ 📁 leads/                 # ⚙️ Módulo Core (Unidad Transaccional del CRM)
 │   ├─ 📄 models.py          # Esquema relacional & inmutabilidad de CoreLead
 │   ├─ 📄 views.py           # Vistas MVT limpias, sin lógica de DB
 │   ├─ 📁 services/          # ♥️ CORAZÓN LÓGICO [Service Layer Pattern]
 │   │   ├─ mdm_service.py    # De-duplicación, Conflictos, Reactivación.
 │   │   ├─ fsm_services.py   # Máquina de estados (Proyect \-> Cliente)
 │   │   └─ ...
 ├─ 📁 users/                 # 🔐 Módulo Satélite (RBAC, Vendedores, Directores)
 ├─ 📁 templates/             # Vistas de Frontera HTML (Jinja2/Django Format)
 │   └─ 📁 partials/          # Componentes reusables de interfaz (Modales)
 └─ 📁 static/                # Activos del Cliente (CSS Vanilla con variables integradas, ChartJS)
```

---
*Documento estructurado como preludio estático a la inyección masiva de Docstrings en código Python, asegurando el futuro traspaso de conocimiento del proyecto.*
