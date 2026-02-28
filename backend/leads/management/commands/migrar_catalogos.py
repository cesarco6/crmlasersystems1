import unicodedata
from django.core.management.base import BaseCommand
from django.utils import timezone
from leads.models import CoreLead
from users.models import CatEspecialidad, CatProducto

def normalizar_texto(texto):
    if not texto:
        return ""
    # Remover espacios al inicio y final
    texto = str(texto).strip()
    # Convertir a minúsculas
    texto = texto.lower()
    # Quitar acentos (NFD separa los caracteres de sus marcas diacríticas)
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                  if unicodedata.category(c) != 'Mn')
    return texto

class Command(BaseCommand):
    help = 'Migrar datos de texto libre a llaves foráneas en el modelo CoreLead.'

    def handle(self, *args, **options):
        # Traer todos los productos a memoria
        productos_db = list(CatProducto.objects.all())
        
        # Traer todas las especialidades a memoria
        especialidades_db = list(CatEspecialidad.objects.all())
        
        procesados_exito = 0
        total_leads = CoreLead.objects.count()
        
        self.stdout.write(self.style.WARNING(f"Iniciando migración para {total_leads} leads..."))
        
        # Iterar sobre todos los registros usando iterator()
        for lead in CoreLead.objects.iterator():
            
            # ==========================================
            # 1. LÓGICA PARA PRODUCTOS (Estricta)
            # ==========================================
            producto_texto = lead.producto_interes
            prod_norm = normalizar_texto(producto_texto)
            producto_encontrado = None
            
            if prod_norm:
                for prod in productos_db:
                    # Coincidencia con nombre normalizado
                    if normalizar_texto(prod.nombre) == prod_norm:
                        producto_encontrado = prod
                        break
                    
                    # Coincidencia con alias
                    if prod.alias:
                        # Asumiendo que los alias están separados por comas
                        aliases = [normalizar_texto(a) for a in prod.alias.split(',')]
                        if prod_norm in aliases:
                            producto_encontrado = prod
                            break
            
            if producto_encontrado:
                lead.producto_cat = producto_encontrado
            else:
                # Buscar o crear producto "Por Definir / Otro"
                prod_default, _ = CatProducto.objects.get_or_create(
                    nombre="Por Definir / Otro"
                )
                if prod_default not in productos_db:
                    productos_db.append(prod_default)
                    
                lead.producto_cat = prod_default
                
                # Inyectar la nota en notas_variadas
                nueva_nota = {
                    "tipo": "sistema",
                    "contenido": f"Migración: Producto original era '{producto_texto}'",
                    "fecha": timezone.now().isoformat()
                }
                
                # Manejo defensivo por si notas_variadas no tiene el formato esperado
                if not isinstance(lead.notas_variadas, dict):
                    lead.notas_variadas = {}
                    
                if "notas" not in lead.notas_variadas or not isinstance(lead.notas_variadas["notas"], list):
                    lead.notas_variadas["notas"] = []
                    
                lead.notas_variadas["notas"].append(nueva_nota)

            
            # ==========================================
            # 2. LÓGICA PARA ESPECIALIDADES (Dinámica)
            # ==========================================
            esp_texto = lead.especialidad
            
            if not esp_texto or not str(esp_texto).strip():
                # Si está vacío, asignar "General"
                esp_default, _ = CatEspecialidad.objects.get_or_create(
                    nombre="General"
                )
                if esp_default not in especialidades_db:
                    especialidades_db.append(esp_default)
                lead.especialidad_cat = esp_default
            else:
                esp_norm = normalizar_texto(esp_texto)
                esp_encontrada = None
                
                # Buscar en memoria si coincide la especialidad normalizada
                for esp in especialidades_db:
                    if normalizar_texto(esp.nombre) == esp_norm:
                        esp_encontrada = esp
                        break
                
                if esp_encontrada:
                    lead.especialidad_cat = esp_encontrada
                else:
                    # Crear nuevo CatEspecialidad con el texto ORIGINAL (respetando mayúsculas y acentos)
                    nueva_esp = CatEspecialidad.objects.create(
                        nombre=str(esp_texto).strip()
                    )
                    especialidades_db.append(nueva_esp)
                    lead.especialidad_cat = nueva_esp
            
            # Guardamos la actualización de los tres campos clave
            lead.save(update_fields=['especialidad_cat', 'producto_cat', 'notas_variadas'])
            procesados_exito += 1
            
            # Contador en consola
            if procesados_exito % 100 == 0:
                self.stdout.write(f"Procesados {procesados_exito} / {total_leads} leads...")
                
        self.stdout.write(self.style.SUCCESS(f"Migración completada con éxito. Total de leads procesados: {procesados_exito}"))
