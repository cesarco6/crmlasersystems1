from django.core.management.base import BaseCommand
from users.models import CatLada, CatUbicacion
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Puebla el Diccionario Nacional de LADAS (IFT) y las enlaza a CatUbicacion.'

    def handle(self, *args, **options):
        # Mapeo Simplificado de LADAS Principales y sus Referencias
        # Basado en el listado del IFT
        LADAS_MEXICO = [
            ('55', 'CDMX/EdoMex', 'Ciudad de México'), ('56', 'CDMX/EdoMex', 'Ciudad de México'),
            ('33', 'Jalisco', 'Guadalajara'), ('81', 'Nuevo León', 'Monterrey'),
            ('222', 'Puebla', 'Puebla'), ('442', 'Querétaro', 'Querétaro'),
            ('771', 'Hidalgo', 'Pachuca'), ('998', 'Quintana Roo', 'Cancún'),
            ('664', 'Baja California', 'Tijuana'), ('477', 'Guanajuato', 'León'),
            ('999', 'Yucatán', 'Mérida'), ('443', 'Michoacán', 'Morelia'),
            ('614', 'Chihuahua', 'Chihuahua'), ('667', 'Sinaloa', 'Culiacán'),
            ('844', 'Coahuila', 'Saltillo'), ('229', 'Veracruz', 'Veracruz'),
            ('951', 'Oaxaca', 'Oaxaca de Juárez'), ('961', 'Chiapas', 'Tuxtla Gutiérrez'),
            ('444', 'San Luis Potosí', 'San Luis Potosí'), ('722', 'EdoMex', 'Toluca'),
            ('449', 'Aguascalientes', 'Aguascalientes'), ('662', 'Sonora', 'Hermosillo'),
            ('686', 'Baja California', 'Mexicali'), ('322', 'Jalisco', 'Puerto Vallarta'),
            ('312', 'Colima', 'Colima'), ('744', 'Guerrero', 'Acapulco'),
            ('246', 'Tlaxcala', 'Tlaxcala'), ('492', 'Zacatecas', 'Zacatecas'),
            ('834', 'Tamaulipas', 'Ciudad Victoria'), ('618', 'Durango', 'Durango'),
            ('624', 'Baja California Sur', 'Cabo San Lucas'), ('777', 'Morelos', 'Cuernavaca'),
            ('981', 'Campeche', 'Campeche'), ('993', 'Tabasco', 'Villahermosa'),
            ('461', 'Guanajuato', 'Celaya'), ('473', 'Guanajuato', 'Guanajuato'),
            ('271', 'Veracruz', 'Córdoba'), ('272', 'Veracruz', 'Orizaba'),
            ('833', 'Tamaulipas', 'Tampico'), ('867', 'Tamaulipas', 'Nuevo Laredo'),
            ('868', 'Tamaulipas', 'Matamoros'), ('899', 'Tamaulipas', 'Reynosa'),
            ('656', 'Chihuahua', 'Ciudad Juárez'), ('631', 'Sonora', 'Nogales'),
            ('644', 'Sonora', 'Ciudad Obregón'), ('668', 'Sinaloa', 'Los Mochis'),
            ('669', 'Sinaloa', 'Mazatlán'), ('311', 'Nayarit', 'Tepic'),
            ('445', 'Guanajuato', 'Valle de Santiago'), ('452', 'Michoacán', 'Uruapan'),
            ('462', 'Guanajuato', 'Irapuato'), ('464', 'Guanajuato', 'Salamanca'),
            ('753', 'Michoacán', 'Lázaro Cárdenas'), ('782', 'Veracruz', 'Poza Rica'),
            ('783', 'Veracruz', 'Tuxpan'), ('921', 'Veracruz', 'Coatzacoalcos'),
            ('922', 'Veracruz', 'Minatitlán'), ('962', 'Chiapas', 'Tapachula'),
            ('228', 'Veracruz', 'Xalapa'), ('238', 'Puebla', 'Tehuacán'),
            ('415', 'Guanajuato', 'San Miguel de Allende'), ('427', 'Querétaro', 'San Juan del Río'),
            ('721', 'EdoMex', 'Tenancingo'), ('735', 'Morelos', 'Cuautla'),
            ('775', 'Hidalgo', 'Tulancingo'), ('871', 'Coahuila/Durango', 'Torreón'),
            ('938', 'Campeche', 'Ciudad del Carmen'), ('984', 'Quintana Roo', 'Playa del Carmen')
        ]

        total_creadas = 0
        total_enlazadas = 0

        for clave, estado, ciudad in LADAS_MEXICO:
            lada_obj, created = CatLada.objects.get_or_create(
                clave=clave,
                defaults={
                    'estado_referencia': estado,
                    'ciudad_referencia': ciudad
                }
            )
            
            if created:
                total_creadas += 1

            # Intentar enlace automático con CatUbicacion existente
            # Buscamos por coincidencia exacta de ciudad (ignorando acentos en el futuro)
            ubicacion = CatUbicacion.objects.filter(ciudad__icontains=ciudad).first()
            if ubicacion:
                lada_obj.ubicacion_oficial = ubicacion
                lada_obj.save()
                total_enlazadas += 1

        self.stdout.write(self.style.SUCCESS(f'Éxito: Se procesaron {len(LADAS_MEXICO)} ladas.'))
        self.stdout.write(f'- Creadas: {total_creadas}')
        self.stdout.write(f'- Enlazadas a Ubicación CRM: {total_enlazadas}')
