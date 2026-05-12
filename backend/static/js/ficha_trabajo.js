// backend/static/js/ficha_trabajo.js

// Funciones para Modales
function abrirModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    
    el.classList.remove('d-none');
    el.style.display = 'flex';

    // FIX UX: Si abrimos el modal de edición, forzamos la interfaz correcta
    if (id === 'modal-editar' && typeof toggleTipoEntidad === 'function') {
        toggleTipoEntidad();
    }
}

function cerrarModal(id) {
    const el = document.getElementById(id);
    el.classList.add('d-none');
    el.style.display = 'none';
}

// --- ESCUDO ANTI-DOBLE CLIC ---
function disableButton(buttonElement, loadingText = 'Procesando...') {
    if (!buttonElement) return null;
    const originalText = buttonElement.innerHTML;
    buttonElement.disabled = true;
    buttonElement.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText}`;
    return originalText;
}

function enableButton(buttonElement, originalText) {
    if (!buttonElement || !originalText) return;
    buttonElement.disabled = false;
    buttonElement.innerHTML = originalText;
}

// Funciones de utilidad para extraer datos del DOM
function getLeadId() {
    return document.getElementById('lead_id_hidden').value;
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function getDashboardUrl() {
    return document.getElementById('dashboard_url_hidden').value;
}

function ejecutarFetchActualizar(data, btn = null) {
    const leadId = getLeadId();
    const csrfToken = getCsrfToken();
    const origText = disableButton(btn);

    fetch(`/api/lead/${leadId}/actualizar/`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json', 
            'X-CSRFToken': csrfToken 
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            Swal.fire('¡Éxito!', result.mensaje, 'success').then(() => {
                location.reload();
            });
        } else if (result.status === 'deleted') {
            Swal.fire('Eliminado', result.mensaje, 'success').then(() => {
                window.location.href = getDashboardUrl();
            });
        } else { 
            enableButton(btn, origText);
            Swal.fire('Error', result.error, 'error');
        }
    })
    .catch(error => { 
        enableButton(btn, origText);
        Swal.fire('Error de Conexión', 'Ocurrió un error al contactar al servidor.', 'error');
    });
}

function toggleTipoEntidad() {
    const isCorporativo = document.getElementById('tipo_corporativo') && document.getElementById('tipo_corporativo').checked;
    const colTitulo = document.getElementById('col-edit-titulo');
    const colPaterno = document.getElementById('col-edit-paterno');
    const colMaterno = document.getElementById('col-edit-materno');
    const colNombre = document.getElementById('col-edit-nombre');

    // Capturamos el label dentro de colNombre
    const labelNombre = colNombre ? colNombre.querySelector('label') : null;

    if (isCorporativo) {
        // Ocultamos las columnas visualmente (SIN limpiar los valores)
        if(colTitulo) colTitulo.style.display = 'none';
        if(colPaterno) colPaterno.style.display = 'none';
        if(colMaterno) colMaterno.style.display = 'none';
        
        // Solo quitamos la obligatoriedad para que el formulario deje guardar
        const inputPaterno = document.getElementById('edit-paterno');
        if(inputPaterno) { inputPaterno.required = false; }

        // Mover col-md-4 a col-md-12 para expandir la Razón Social
        if(colNombre) {
            colNombre.classList.remove('col-md-4');
            colNombre.classList.add('col-md-12');
            if(labelNombre) labelNombre.innerText = 'Razón Social *';
        }

    } else {
        // Mostramos las columnas de vuelta (los datos seguirán ahí)
        if(colTitulo) colTitulo.style.display = '';
        if(colPaterno) colPaterno.style.display = '';
        if(colMaterno) colMaterno.style.display = '';
        
        // Volvemos a hacer obligatorio el apellido paterno
        const inputPaterno = document.getElementById('edit-paterno');
        if(inputPaterno) { inputPaterno.required = true; }

        // Regresar la columna a su tamaño original para que quepan los apellidos
        if(colNombre) {
            colNombre.classList.remove('col-md-12');
            colNombre.classList.add('col-md-4');
            if(labelNombre) labelNombre.innerText = 'Nombre *';
        }
    }
}

function ejecutarRitual(accion, btn = null) {
    // --- ESCUDO ESTRICTO: No dejar guardar en blanco ---
    if (accion === 'GUARDAR' || accion === 'VALIDAR') {
        const form = document.getElementById('form-editar');
        if (!form.checkValidity()) {
            if (document.getElementById('modal-editar').classList.contains('d-none')) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Datos Incompletos',
                    text: 'Abre la ventana de edición (✏️ Editar) para completar los campos obligatorios antes de validar.',
                    confirmButtonText: 'Abrir Edición',
                    showCancelButton: true,
                    cancelButtonText: 'Cancelar'
                }).then((result) => {
                    if (result.isConfirmed) {
                        abrirModal('modal-editar');
                        setTimeout(() => form.reportValidity(), 300);
                    }
                });
            } else {
                form.reportValidity(); // Muestra el mensaje rojo nativo del navegador
            }
            return;
        }
    }
    
    const radioSelected = document.querySelector('input[name="tipo_entidad"]:checked');
    const tipoEntidad = radioSelected ? radioSelected.value : 'INDIVIDUAL';

    const data = {
        accion: accion,
        tipo_entidad: tipoEntidad,
        titulo_cortesia: document.getElementById('edit-titulo') ? document.getElementById('edit-titulo').value : '',
        nombre_pila: document.getElementById('edit-nombre-pila') ? document.getElementById('edit-nombre-pila').value : '',
        apellido_paterno: document.getElementById('edit-paterno') ? document.getElementById('edit-paterno').value : '',
        apellido_materno: document.getElementById('edit-materno') ? document.getElementById('edit-materno').value : '',
        telefono: document.getElementById('edit-telefono').value,
        celular: document.getElementById('edit-celular').value,
        email: document.getElementById('edit-email').value,
        direccion: document.getElementById('edit-direccion').value,
        especialidad: document.getElementById('edit-especialidad').value,
        ubicacion: document.getElementById('edit-ubicacion') ? document.getElementById('edit-ubicacion').value : '',
        producto: document.getElementById('edit-producto').value
    };

    if (accion === 'DESECHAR') {
        Swal.fire({
            title: '¿Estás completamente seguro?',
            text: "🚨 PELIGRO: Estás a punto de borrar este registro de la base de datos para siempre.",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Sí, borrarlo',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                ejecutarFetchActualizar(data, btn);
            }
        });
        return;
    }

    if (accion === 'DESCARTAR') {
        Swal.fire({
            title: '¿Mandar a la congeladora?',
            text: "⚠️ ATENCIÓN: Estás a punto de archivar este prospecto.",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#f39c12',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Sí, descartar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                Swal.fire({
                    title: 'Motivo del descarte',
                    input: 'text',
                    inputLabel: 'Por favor, escribe el motivo para el historial:',
                    inputPlaceholder: 'Ej. No le alcanzó el presupuesto',
                    showCancelButton: true,
                    inputValidator: (value) => {
                        if (!value) {
                            return '¡El motivo es obligatorio para el reporte de rechazos!';
                        }
                    }
                }).then((motivoResult) => {
                    if (motivoResult.isConfirmed) {
                        data.motivo = motivoResult.value;
                        ejecutarFetchActualizar(data, btn);
                    }
                });
            }
        });
        return;
    }

    if (accion === 'VALIDAR') {
        Swal.fire({
            title: 'Validar Identidad',
            text: "Confirma los datos de contacto y justifica el avance a LEAD.",
            icon: 'info',
            input: 'textarea',
            inputLabel: 'Justificación o nota de validación (obligatoria):',
            inputPlaceholder: 'Ej. Hablé con el doctor y confirmó sus datos...',
            showCancelButton: true,
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Validar Identidad',
            cancelButtonText: 'Cancelar',
            inputValidator: (value) => {
                if (!value) {
                    return '¡La justificación es obligatoria para validar la identidad!';
                }
            }
        }).then((result) => {
            if (result.isConfirmed) {
                data.nota = result.value;
                ejecutarFetchActualizar(data, btn);
            }
        });
        return;
    }

    // Para GUARDAR o cualquier otra acción sin confirmación especial
    ejecutarFetchActualizar(data, btn);
}

function toggleFormatoPedido() {
    const isChecked = $('#switch-pedido').is(':checked');
    
    if (isChecked) {
        $('#bloque-facturacion').collapse('show');
    } else {
        $('#bloque-facturacion').collapse('hide');
    }
}

function copiarDireccionLead() {
    const dRazon = document.getElementById('venta-razon');
    const dCalle = document.getElementById('venta-calle');
    const dCiudad = document.getElementById('venta-ciudad');
    const dEstado = document.getElementById('venta-estado');
    
    if ($('#switch-copiar-direccion').is(':checked')) {
        dRazon.value = document.getElementById('hidden-lead-nombre').value;
        dCalle.value = document.getElementById('hidden-lead-direccion').value;
        dCiudad.value = document.getElementById('hidden-lead-ciudad').value;
        dEstado.value = document.getElementById('hidden-lead-estado').value;
    } else {
        dRazon.value = '';
        dCalle.value = '';
        dCiudad.value = '';
        dEstado.value = '';
    }
}

function guardarCierreVenta(btn = null) {
    const leadId = getLeadId();
    const csrfToken = getCsrfToken();
    
    const isPedidoOn = $('#switch-pedido').is(':checked');
    
    const folioPedido = document.getElementById('venta-folio').value.trim();

    // Validación Estricta
    if (!folioPedido) {
        Swal.fire('Falta Información', 'El Folio de Pedido es obligatorio.', 'warning');
        return;
    }

    const data = {
        accion: 'CERRAR_VENTA',
        pre_llenar_pedido: isPedidoOn,
        folio_pedido: folioPedido
    };

    if (isPedidoOn) {
        const rfc = document.getElementById('venta-rfc').value.trim().toUpperCase();
        const razonSocial = document.getElementById('venta-razon').value.trim();

        if (!rfc || rfc.length < 12) {
            Swal.fire('Falta Información', 'El RFC es obligatorio y debe tener al menos 12 caracteres.', 'warning');
            return;
        }
        if (!razonSocial) {
            Swal.fire('Falta Información', 'La Razón Social es obligatoria para la facturación.', 'warning');
            return;
        }

        data.rfc = rfc;
        data.razon_social = razonSocial;
        data.calle = document.getElementById('venta-calle').value.trim();
        data.colonia = document.getElementById('venta-colonia').value.trim();
        data.ciudad = document.getElementById('venta-ciudad').value.trim();
        data.estado = document.getElementById('venta-estado').value.trim();
        data.cp = document.getElementById('venta-cp').value.trim();
    }

    const origText = disableButton(btn, 'Cerrando venta...');

    fetch(`/api/lead/${leadId}/actualizar/`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json', 
            'X-CSRFToken': csrfToken 
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            Swal.fire({
                title: '🏆 ¡Venta Cerrada!',
                text: 'El prospecto ha sido convertido a CLIENTE exitosamente.',
                icon: 'success',
                confirmButtonColor: '#28a745'
            }).then(() => {
                cerrarModal('modal-cerrar-venta');
                
                if (result.url_descarga) {
                    // window.open(result.url_descarga, '_blank'); // Descarga automática deshabilitada
                }
                
                setTimeout(() => { location.reload(); }, 300);
            });
        } else { 
            enableButton(btn, origText);
            Swal.fire('Error al Cerrar', result.error || 'Ocurrió un problema en el servidor.', 'error'); 
        }
    })
    .catch(error => { 
        enableButton(btn, origText);
        Swal.fire('Error de Conexión', 'No se pudo comunicar con el servidor.', 'error'); 
    });
}

function ejecutarAccionFase2(accion, btn = null) {
    const data = { accion: accion };

    if (accion === 'CALIFICAR') {
        data.calificacion = document.getElementById('select-calificacion').value;
    } else if (accion === 'AGENDAR') {
        const fecha = document.getElementById('input-fecha-agenda').value;
        if (!fecha) { 
            Swal.fire('Atención', 'Debes seleccionar una fecha.', 'warning');
            return; 
        }
        data.fecha_contacto = fecha;
    } else if (accion === 'AGREGAR_NOTA') {
        const inputNota = document.getElementById('input-nueva-nota');
        const nota = inputNota.value.trim();
        if (!nota) {
            Swal.fire('Atención', 'Escribe algo antes de agregar la nota.', 'info');
            return;
        }
        data.nota = nota;
    }

    ejecutarFetchActualizar(data, btn);
}

// Función para el Selector en Cascada
function filtrarProductos360() {
    const familiaSeleccionada = document.getElementById('select-tipo-extra').value;
    const selectProducto = document.getElementById('extra-producto');
    const opciones = selectProducto.querySelectorAll('option');

    // Resetear el selector de productos
    selectProducto.value = "";
    
    if (!familiaSeleccionada) {
        selectProducto.disabled = true;
        opciones[0].text = "-- Selecciona primero el Tipo --";
        opciones.forEach(opt => { 
            if(opt.value) {
                opt.classList.add('d-none');
                opt.style.display = 'none'; 
            } 
        });
        return;
    }

    // Si seleccionó familia, habilitamos y filtramos
    selectProducto.disabled = false;
    opciones[0].text = "-- Ahora selecciona el producto --";
    
    opciones.forEach(opt => {
        // Ignoramos el placeholder base
        if (opt.value === "") return; 
        
        if (opt.getAttribute('data-familia') === familiaSeleccionada) {
            opt.classList.remove('d-none');
            opt.style.display = ''; // Reset para mostrarlo
        } else {
            opt.classList.add('d-none');
            opt.style.display = 'none'; // Ocultarlo
        }
    });
}

function guardarOportunidad360(btn = null) {
    const leadId = getLeadId();
    const csrfToken = getCsrfToken();
    
    const productoId = document.getElementById('extra-producto').value;
    const estatus = document.getElementById('extra-estatus').value;
    const notas = document.getElementById('extra-notas').value.trim();

    if (!productoId) {
        Swal.fire('Atención', '⚠️ Selecciona un Producto o Servicio obligatoriamente.', 'warning');
        return;
    }
    if (!notas) {
        Swal.fire('Atención', '⚠️ Las notas son obligatorias para dejar el rastro.', 'warning');
        return;
    }

    const origText = disableButton(btn, 'Guardando...');

    const data = {
        lead_id: leadId,
        producto_id: productoId, 
        estatus: estatus,
        notas: notas
    };

    fetch(`/api/venta-extra/`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json', 
            'X-CSRFToken': csrfToken 
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            Swal.fire('¡Oportunidad 360 Creada!', result.mensaje, 'success').then(() => {
                cerrarModal('modal-venta-extra');
                location.reload(); 
            });
        } else { 
            enableButton(btn, origText);
            Swal.fire('Error', (result.error || result.mensaje), 'error');
        }
    })
    .catch(error => { 
        enableButton(btn, origText);
        Swal.fire('Error de Conexión', 'Ocurrió un error de conexión al guardar.', 'error'); 
    });
}

function insertarRespuestaRapida(selectElement, targetId) {
    const inputElement = document.getElementById(targetId);
    if (!inputElement) return;

    const valor = selectElement.value;

    if (valor) {
        // Inserción directa de la nota ("Higiene Pura")
        if (inputElement.value.trim() !== '') {
            const separador = inputElement.tagName.toLowerCase() === 'textarea' ? '\n' : ' ';
            inputElement.value += separador + valor;
        } else {
            inputElement.value = valor;
        }

        // Restablecemos el select a la opción por defecto
        selectElement.value = '';

        // Regresamos el foco al input para que el vendedor pueda seguir escribiendo
        inputElement.focus();
    }
}

function marcarNoCierre() {
    Swal.fire({
        title: 'Marcar como No Cierre',
        text: "La oportunidad se moverá fuera del pipeline comercial.",
        icon: 'warning',
        input: 'text',
        inputLabel: 'Motivo de la pérdida:',
        inputPlaceholder: 'Ej. Falta de presupuesto, se fue con competencia...',
        showCancelButton: true,
        confirmButtonColor: '#f39c12',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, registrar No Cierre',
        cancelButtonText: 'Cancelar',
        inputValidator: (value) => {
            if (!value) {
                return '¡Debes escribir un motivo obligatorio!';
            }
        }
    }).then((result) => {
        if (result.isConfirmed) {
            const data = { motivo: result.value };
            const leadId = getLeadId();
            const csrfToken = getCsrfToken();
            
            fetch(`/api/lead/${leadId}/no-cierre/`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json', 
                    'X-CSRFToken': csrfToken 
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(res => {
                if (res.status === 'success') {
                    Swal.fire('Oportunidad Perdida', res.mensaje, 'success').then(() => {
                        cerrarModal('modal-editar');
                        location.reload();
                    });
                } else {
                    Swal.fire('Error FSM', res.error, 'error');
                }
            })
            .catch(err => Swal.fire('Error', 'No se pudo contactar al servidor.', 'error'));
        }
    });
}

function actualizarEstatus360(ventaId, selectElement, estatusAnterior) {
    const nuevoEstatus = selectElement.value;
    const csrfToken = getCsrfToken();

    // Si el usuario seleccionó el mismo estatus, no hacer nada
    if (nuevoEstatus === estatusAnterior) return;

    // --- Notas rápidas contextuales según la transición ---
    const NOTAS_RAPIDAS = {
        'PENDIENTE->EN_GESTION': [
            'Se contactó al cliente',
            'Se envió cotización',
            'Cliente interesado, dará respuesta'
        ],
        'EN_GESTION->CONCRETADO': [
            'Venta cerrada exitosamente',
            'Servicio realizado con éxito',
            'Cliente confirmó asistencia al evento'
        ],
        'EN_GESTION->DESCARTADO': [
            'Sin presupuesto por el momento',
            'No le interesó el producto',
            'Se fue con la competencia'
        ]
    };

    const clave = `${estatusAnterior}->${nuevoEstatus}`;
    const opciones = NOTAS_RAPIDAS[clave] || [];
    const opcionesHTML = opciones.map(n => `<option value="${n}">${n}</option>`).join('');

    Swal.fire({
        title: '📝 Nota para este movimiento',
        html: `
            <select id="swal-nota-rapida" class="swal2-select" style="margin-bottom:10px; font-size:14px;">
                <option value="">-- Nota Rápida (opcional) --</option>
                ${opcionesHTML}
            </select>
            <textarea id="swal-nota-libre" class="swal2-textarea" placeholder="Escribe una nota libre o selecciona una rápida arriba..." style="font-size:14px;"></textarea>
        `,
        showCancelButton: true,
        confirmButtonText: 'Confirmar Cambio',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#28a745',
        cancelButtonColor: '#6c757d',
        didOpen: () => {
            // Cuando selecciona nota rápida, la inyecta en el textarea
            const selectRapida = document.getElementById('swal-nota-rapida');
            const textareaLibre = document.getElementById('swal-nota-libre');
            selectRapida.addEventListener('change', () => {
                if (selectRapida.value) {
                    if (textareaLibre.value.trim()) {
                        textareaLibre.value += '\n' + selectRapida.value;
                    } else {
                        textareaLibre.value = selectRapida.value;
                    }
                    selectRapida.value = '';
                    textareaLibre.focus();
                }
            });
        }
    }).then((result) => {
        if (result.isConfirmed) {
            const nota = document.getElementById('swal-nota-libre').value.trim();

            fetch(`/api/venta-extra/${ventaId}/actualizar/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ estatus: nuevoEstatus, nota: nota })
            })
            .then(response => response.json())
            .then(res => {
                if (res.status === 'success') {
                    Swal.fire('¡Actualizado!', res.mensaje, 'success').then(() => {
                        location.reload();
                    });
                } else {
                    selectElement.value = estatusAnterior;
                    Swal.fire('Error', res.error, 'error');
                }
            })
            .catch(error => {
                selectElement.value = estatusAnterior;
                Swal.fire('Error de Conexión', 'No se pudo comunicar con el servidor.', 'error');
            });
        } else {
            // Canceló → rollback del select
            selectElement.value = estatusAnterior;
        }
    });
}

function marcarHitoPostVenta(hito, leadId) {
    const csrfToken = getCsrfToken();
    const nombres = {
        'capacitacion': '🎓 Capacitación Post-Venta',
        'calidad': '📞 Llamada de Calidad'
    };

    Swal.fire({
        title: '¿Confirmar hito completado?',
        text: `Vas a marcar "${nombres[hito] || hito}" como realizado. Esta acción no se puede deshacer.`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: '✅ Sí, marcar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#198754',
        cancelButtonColor: '#6c757d'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/api/hito-postventa/${leadId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ hito: hito })
            })
            .then(response => response.json())
            .then(res => {
                if (res.status === 'success') {
                    Swal.fire('¡Completado!', res.mensaje, 'success').then(() => {
                        location.reload();
                    });
                } else {
                    Swal.fire('Error', res.error, 'error');
                }
            })
            .catch(error => {
                Swal.fire('Error de Conexión', 'No se pudo comunicar con el servidor.', 'error');
            });
        }
    });
}

// Inicialización On-Load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('form-editar') && typeof toggleTipoEntidad === 'function') {
        toggleTipoEntidad();
    }
    
    const inputFechaAgenda = document.getElementById('input-fecha-agenda');
    if (inputFechaAgenda) {
        // --- Restricción de 3 días hábiles para Prospectos ---
        const estatus = inputFechaAgenda.getAttribute('data-estatus');
        if (estatus === 'PROSPECTO') {
            let count = 0;
            let limitDate = new Date();
            limitDate.setHours(0, 0, 0, 0);
            
            while (count < 3) {
                limitDate.setDate(limitDate.getDate() + 1);
                // 0 = Domingo, 6 = Sábado
                if (limitDate.getDay() !== 0 && limitDate.getDay() !== 6) {
                    count++;
                }
            }
            
            // Desfase de zona horaria (trick para toISOString)
            limitDate.setMinutes(limitDate.getMinutes() - limitDate.getTimezoneOffset());
            const maxDateStr = limitDate.toISOString().split('T')[0];
            inputFechaAgenda.setAttribute('max', maxDateStr);
            
            const todayDate = new Date();
            todayDate.setMinutes(todayDate.getMinutes() - todayDate.getTimezoneOffset());
            inputFechaAgenda.setAttribute('min', todayDate.toISOString().split('T')[0]);
        }

        inputFechaAgenda.addEventListener('change', (e) => {
            const fecha = e.target.value;
            if (!fecha) {
                const badge = document.getElementById('citas-dia-badge');
                if (badge) badge.classList.add('d-none');
                return;
            }
            
            fetch(`/api/citas-dia/?fecha=${fecha}`)
                .then(res => res.json())
                .then(data => {
                    const badge = document.getElementById('citas-dia-badge');
                    if (badge && data.citas_programadas !== undefined) {
                        badge.classList.remove('d-none');
                        badge.innerText = `Tienes ${data.citas_programadas} citas ya programadas para este día`;
                        if (data.citas_programadas > 0) {
                            badge.classList.remove('bg-success');
                            badge.classList.add('bg-warning', 'text-dark');
                        } else {
                            badge.classList.remove('bg-warning', 'text-dark');
                            badge.classList.add('bg-success');
                        }
                    }
                })
                .catch(err => console.error("Error obteniendo citas del día", err));
        });
    }
});
