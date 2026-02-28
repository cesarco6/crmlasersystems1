def contador_alertas(request):
    """
    Inyecta el número de notificaciones y la lista de las 5 más recientes.
    """
    if request.user.is_authenticated:
        # Buscamos todas las alertas no leídas de este usuario
        alertas = request.user.notificaciones.filter(leida=False).order_by('-fecha_creacion')
        
        return {
            'notificaciones_no_leidas': alertas.count(),
            'lista_alertas': alertas[:5]  # Mandamos solo las 5 más nuevas para no saturar el menú
        }
    
    return {'notificaciones_no_leidas': 0, 'lista_alertas': []}