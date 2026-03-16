# 🏛️ Arquitectura del Sistema de Avisos (CRM Laser Systems)

Estatus actual del módulo de notificaciones y blindaje.

## 1. Capa de Datos (Modelos)

*   **`Notificacion`**: Registro individual de alerta.
    *   `tipo`: (capacitacion, calidad, mantenimiento, estancamiento, reactivacion).
    *   `leida`: Booleano para control de visibilidad.
*   **`TrackingPostVenta`**: Tabla satélite One-to-One con `CoreLead` para hitos de fidelización.
*   **`VentaTransaccional`**: Usada para el "Reloj Flotante". Registra ventas de servicio o descartes de mantenimiento.

---

## 2. Motor de Inteligencia (generar_alertas.py)

Comando encargado de la generación proactiva basada en 5 reglas de negocio de alto impacto:

1.  **Agenda Diaria (`reactivacion`)**: Detecta leads activos con `next_action_date` vencida.
2.  **Telarañas (`estancamiento`)**: Detecta leads sin modificación (`updated_at`) por más de 7 días.
3.  **Hito: Capacitación**: Alerta a los 8 días de la venta si no se ha marcado como cumplida.
4.  **Hito: Calidad**: Alerta a los 180 días de la venta si no se ha realizado la llamada.
5.  **Reloj Flotante (`mantenimiento`)**: Alerta recurrente cada 18 meses (540 días) analizando el flujo transaccional.

---

## 3. Capa de Control y Blindaje (views.py)

### A. Blindaje (API Atender)
Refactorización de seguridad para asegurar auditoría.
*   **Endpoint**: `/api/alerta/<id>/atender/` (POST).
*   **Auditoría**: Inyecta una nota de tipo "sistema" en el JSON `notas_variadas` del Lead con el motivo proporcionado.
*   **Lógica de Negocio**: Si es mantenimiento, crea un registro `DESCARTADO` para resetear el reloj.

### B. Auto-resolución (Silenciosa)
Limpieza automática de la campana cuando el vendedor realiza la acción natural en el CRM:
*   **FSM Transitions**: Apaga `estancamiento` y `reactivacion`.
*   **Hitos Postventa**: Apaga `capacitacion` o `calidad` al marcarlos.
*   **Venta Extra**: Apaga `mantenimiento` si se registra un producto del catálogo `SERVICIO`.

---

## 4. Interfaz de Usuario (base.html)

Componentes modernos para una experiencia fluida:
*   **SweetAlert2**: Captura de motivos obligatorios/opcionales con validación.
*   **Data Attributes**: Uso de `data-alerta-id`, `data-alerta-tipo` para desacoplar el HTML del JavaScript.
*   **Fetch API (POST)**: Comunicación asíncrona con el backend con manejo de tokens CSRF.
*   **Redirección Dinámica**: Envío automático a la `ficha_trabajo` del lead relacionado tras atender el aviso.
