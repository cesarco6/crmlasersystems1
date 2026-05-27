// static/js/modals.js

function toggleTipoEntidadAlta() {
    const isCorporativo = document.getElementById('alta_tipo_corporativo') && document.getElementById('alta_tipo_corporativo').checked;
    const colTitulo = document.getElementById('col-alta-titulo');
    const colPaterno = document.getElementById('col-alta-paterno');
    const colMaterno = document.getElementById('col-alta-materno');
    const colNombre = document.getElementById('col-alta-nombre-pila');
    
    // Capturamos el label para cambiar el texto visualmente
    const labelNombre = colNombre ? colNombre.querySelector('label') : null;

    if (isCorporativo) {
        if(colTitulo) colTitulo.style.display = 'none';
        if(colPaterno) colPaterno.style.display = 'none';
        if(colMaterno) colMaterno.style.display = 'none';
        
        const inputPaterno = document.getElementById('alta-apellido-paterno');
        const inputMaterno = document.getElementById('alta-apellido-materno');
        const selectTitulo = document.getElementById('alta-titulo');

        if(inputPaterno) { inputPaterno.value = ''; inputPaterno.required = false; }
        if(inputMaterno) { inputMaterno.value = ''; }
        if(selectTitulo) { selectTitulo.value = ''; }

        if(colNombre) {
            colNombre.classList.remove('col-md-4');
            colNombre.classList.add('col-md-12');
            if(labelNombre) labelNombre.innerText = 'Razón Social / Clínica *'; // UX Fix
        }

    } else {
        if(colTitulo) colTitulo.style.display = '';
        if(colPaterno) colPaterno.style.display = '';
        if(colMaterno) colMaterno.style.display = '';
        
        const inputPaterno = document.getElementById('alta-apellido-paterno');
        if(inputPaterno) { inputPaterno.required = true; }

        if(colNombre) {
            colNombre.classList.remove('col-md-12');
            colNombre.classList.add('col-md-4');
            if(labelNombre) labelNombre.innerText = 'Nombre(s) *'; // UX Fix
        }
    }
}

function guardarLeadManual(event) {
    event.preventDefault();

    const radioSelected = document.querySelector('input[name="alta_tipo_entidad"]:checked');
    const tipoEntidad = radioSelected ? radioSelected.value : 'INDIVIDUAL';

    const telefono = document.getElementById('alta-telefono').value;
    const titulo = document.getElementById('alta-titulo').value;
    const nombrePila = document.getElementById('alta-nombre-pila').value;
    const apellidoPaterno = document.getElementById('alta-apellido-paterno').value;
    const apellidoMaterno = document.getElementById('alta-apellido-materno').value;
    
    const especialidad = document.getElementById('alta-especialidad').value;
    const ubicacion = document.getElementById('alta-ubicacion').value;
    const celular = document.getElementById('alta-celular').value;
    const email = document.getElementById('alta-email').value;
    const eventoId = document.getElementById('alta-evento-id') ? document.getElementById('alta-evento-id').value : '';

    const payload = {
        tipo_entidad: tipoEntidad,
        telefono: telefono,
        titulo_cortesia: titulo,
        nombre_pila: nombrePila,
        apellido_paterno: apellidoPaterno,
        apellido_materno: apellidoMaterno,
        especialidad: especialidad,
        ubicacion: ubicacion,
        celular: celular,
        email: email,
        evento_id: eventoId
    };

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

  // Apuntamos a la ruta correcta de tu urls.py
    fetch('/api/alta-manual/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
    })
        .then(async response => {
            // Manejamos los errores HTTP (400, 500) para poder extraer el JSON del error
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Error desconocido del servidor');
            }
            return data;
        })
        .then(data => {
            if (data.status === 'success') {
                Swal.fire({
                    title: '¡Éxito!',
                    text: data.mensaje || 'Prospecto creado correctamente.',
                    icon: 'success'
                }).then(() => window.location.reload());
            } 
        })
        .catch(error => {
            console.error('Error:', error);
            // Mostrar la alerta de duplicado o error que escupe evaluar_duplicidad_estricta
            Swal.fire('Atención', error.message, 'warning');
        });
}
