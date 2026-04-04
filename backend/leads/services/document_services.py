import os
from datetime import datetime
from django.conf import settings
from docxtpl import DocxTemplate

def generar_formato_pedido(lead, datos_fiscales, folio_pedido):
    """
    Genera un formato de pedido automatizado en Word usando docxtpl.
    Aplica la Regla Visual de Negocio (Filtro 'Pendiente') si el RFC es el genérico.
    """
    # 1. Definir rutas
    # Suponiendo que la carpeta docs está en BASE_DIR/templates/docs
    template_path = os.path.join(settings.BASE_DIR, 'templates', 'docs', 'plantilla_pedido.docx')
    
    if not os.path.exists(template_path):
        # Fallback de seguridad o simplemente lanzar el error
        raise FileNotFoundError(f"La plantilla de pedido no existe en la ruta configurada: {template_path}")

    # Asegurar que el directorio media/pedidos existe
    pedidos_dir = os.path.join(settings.MEDIA_ROOT, 'pedidos')
    os.makedirs(pedidos_dir, exist_ok=True)
    
    # Construir el nombre del archivo final
    file_name = f"Pedido_{folio_pedido}_{lead.id}.docx"
    output_path = os.path.join(pedidos_dir, file_name)
    
    # URL pública (asumiendo que MEDIA_URL está como '/media/')
    # Remover el trailing slash si está presente para evitar doble barra
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    if not media_url.endswith('/'):
        media_url += '/'
    url_publica = f"{media_url}pedidos/{file_name}"

    # 2. Preparar el contexto base
    contexto = {
        'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
        'folio_pedido': folio_pedido,
        'nombre_completo': lead.nombre_completo_mdm or '',
        'celular': lead.phone_primary or lead.celular or '',
        'email': lead.email or '',
        'direccion_completa': lead.direccion_completa or '',
        'check_domicilio': 'X',  # Regla de checkbox activo por defecto solicitada
        'vendedor_nombre': lead.owner.get_full_name() if lead.owner.get_full_name() else lead.owner.username,
    }

    # 3. REGLA VISUAL DE NEGOCIO (Filtro 'Pendiente')
    rfc = datos_fiscales.get('rfc', '').strip().upper()
    
    if rfc == 'XAXX010101000' or not rfc:
        # Vía Rápida / Comodín SAT: Ocultar datos fiscales en el documento
        contexto.update({
            'razon_social': 'PENDIENTE',
            'rfc': '',
            'calle': '',
            'colonia': '',
            'ciudad': '',
            'estado': '',
            'codigo_postal': '',
            'regimen_fiscal': ''  # Para que no se imprima el '616' a la vista
        })
    else:
        # Vía Completa: RFC Real
        contexto.update({
            'razon_social': datos_fiscales.get('razon_social', ''),
            'rfc': rfc,
            'calle': datos_fiscales.get('calle', ''),
            'colonia': datos_fiscales.get('colonia', ''),
            'ciudad': datos_fiscales.get('ciudad', ''),
            'estado': datos_fiscales.get('estado', ''),
            'codigo_postal': datos_fiscales.get('codigo_postal', ''),
            'regimen_fiscal': datos_fiscales.get('regimen_fiscal', '')
        })

    # 4. Inyección del Contexto vía docxtpl
    doc = DocxTemplate(template_path)
    doc.render(contexto)
    
    # 5. Guardado físico
    doc.save(output_path)

    return url_publica
