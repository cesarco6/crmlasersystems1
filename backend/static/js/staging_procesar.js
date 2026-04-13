/**
 * Initialization wrapper for the Lead Staging (Quarantine) resolution panel.
 * Listens for changes in the entity type dropdown to dynamically adjust the DOM 
 * grid showing/hiding Atomic Identity fields vs Corporate names.
 */
document.addEventListener('DOMContentLoaded', function() {
    const selectEntidad = document.getElementById('tipo_entidad');
    const divTitulo = document.getElementById('div_titulo');
    const divPaterno = document.getElementById('div_paterno');
    const divMaterno = document.getElementById('div_materno');
    const divNombre = document.getElementById('div_nombre');
    const labelNombre = document.getElementById('label_nombre');

    /**
     * Toggles visibility of Individual vs Corporate fields dynamically.
     */
    function toggleCamposIdentidad() {
        if (selectEntidad.value === 'CORPORATIVO') {
            // Ocultar campos de individuo
            divTitulo.classList.add('d-none');
            divPaterno.classList.add('d-none');
            divMaterno.classList.add('d-none');
            // Expandir la caja del nombre y cambiar etiqueta
            divNombre.classList.replace('col-md-9', 'col-md-12');
            labelNombre.innerText = 'Razón Social / Nombre de Clínica *';
        } else {
            // Mostrar campos de individuo
            divTitulo.classList.remove('d-none');
            divPaterno.classList.remove('d-none');
            divMaterno.classList.remove('d-none');
            // Regresar la caja del nombre a su tamaño original
            divNombre.classList.replace('col-md-12', 'col-md-9');
            labelNombre.innerText = 'Nombre de Pila *';
        }
    }

    // Ejecutar al inicio por si el registro ya carga como CORPORATIVO
    toggleCamposIdentidad();
    
    // Ejecutar cada vez que el usuario cambie la opción
    selectEntidad.addEventListener('change', toggleCamposIdentidad);
});