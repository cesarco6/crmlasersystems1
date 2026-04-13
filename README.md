# CRM Laser Systems 🚀

**CRM Laser Systems** es una plataforma integral de gestión de relaciones con clientes y prospectos diseñada bajo una estricta arquitectura de tres fases y seguridad híbrida relacional. Su objetivo principal es asegurar la trazabilidad del proceso de venta médica a través un control absoluto de inmutabilidad, escalabilidad dockerizada y visualización por roles.

---

## ⚙️ Stack Tecnológico

El proyecto está diseñado pensando en la robustez y alto rendimiento computacional en backend apoyado de visuales orgánicos y responsivos al cliente.

* **Backend Framework:** Python 3.11 + Django 5.0 (MVT & API REST)
* **Persistencia Principal:** PostgreSQL 16 (Estructuras Relacionales + campos `JSONB` robustos para notas de seguimiento).
* **Frontend:** Motor de Django Templates, Bootstrap 5.3, Custom Vanilla JS & CSS interactivo (Dynamic Dark/Light Modes) con visuales Chart.js y SweetAlert2.
* **Procesos en 2do Plano:** Redis + Django Q (Scheduler Automático / Disparador de Alertas Críticas).
* **Despliegue & DevOps:** Solución portable 100% en Docker Compose (Nginx, Gunicorn, Web, DB, Redis).

---

## 🏛️ Lógica de Negocio y Data Flow (Las 3 Fases)

El ciclo de la vida de un `CoreLead` (Unidad Atómica del sistema) está estrictamente gobernado por tres fases ineludibles que cierran o abren la capacidad de interactuar con el registro:

1. **Fase 1: Captura ("El Barrido"):** 
   * Interfaz de ingesta masiva (Staging / Quirófano) y manual.
   * Total libertad de edición para la limpieza de la base de datos de basureros externos. Permiso físico de Hard Delete para descargas inservibles.
2. **Fase 2: Trabajo ("El Tratamiento"):**
   * Disparado por la transición exitosa de *Prospecto* a *Lead*.
   * **Candado de Identidad Crítico:** El Nombre, Teléfono(s) y Especialidad del prospecto quedan totalmente inmutables a nivel UI y persistencia, garantizando consistencia legal y rastreo para el Director. 
   * Se permiten gestiones temporales y calendarios mediante planes (Seguimiento, En Espera).
3. **Fase 3: Cierre o Archivo ("La Formalización"):**
   * Transición a `Cliente` o `Descartado`. Requisitos bloqueantes como la necesidad estricta de un Perfil Fiscal para la facturación (Filtros de rigor).

---

## 👥 Arquitectura de Seguridad y Roles (RBAC)

La plataforma distribuye el tráfico y la visibilidad de datos mediante políticas nativas de separación de roles extendiendo el `auth_user` original.

* **🤵‍♂️ Ventas / Agentes:** Scope *Local Limitado*. Cada persona sólo tiene permiso de interrogar a la base de datos por sus registros (`owner_id`) asignados. Carecen de poder sobre la alteración catastrófica (eliminar registros validados).
* **📈 Dirección:** Scope *Global Read-Only / Gestión Táctica*. Vistas ejecutivas privilegiadas en las que consumen la operación holística, incluyendo un "Dashboard Panorámico", la visual de la "Directorio Maestro", Módulo "Fidelización 360°" y el rol de arbitraje (Bandejas de revisión y Ingesta Histórica).
* **💻 Admin Sys:** Posee privilegios cruzados para mantenimiento integral, soft y hard deletes.

---

## 🛡️ Estándares para Desarrollo (Interno)

Si vas a contribuir o levantar entornos de réplica para este proyecto, sigue estos estándares estipulados en el **DDS de Arquitectura (v2.0)**:

1. **Gestión de variables sensibles:** Todo se rige bajo carga dinámica con un archivo `.env` bloqueado por el `.gitignore`.
2. **Pipelines / Dependencias:** Ambiente virtual estandarizado con un `requirements.txt` pre-congelado.
3. **Auto-formateo:** Se delega a `Black` el pre-formateo del backend Pythonico.
4. **Bases Híbridas:** Toda la recarga transaccional irregular (como la bitácora de actividad impredecible) se destina al campo dinámico `notas_variadas (JSONB)` mitigando la necesidad de migraciones agresivas.

---

*CRM Laser Systems fue desarrollado bajo los estándares de confidencialidad para operación en ventas de equipamiento médico especializado. Documento generado iterativamente conforme al DDS.*
