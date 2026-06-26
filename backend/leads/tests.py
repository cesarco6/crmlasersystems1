# leads/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from users.models import UserProfile, CatUbicacion, CatProducto, CatEspecialidad
from leads.models import CoreLead, Evento, LeadEvento, ExcepcionEspecialidadLinea
import json

class EventosClienteViewsTestCase(TestCase):
    def setUp(self):
        # 1. Crear usuarios y perfiles
        self.vendedor_user = User.objects.create_user(username='testvendedor', password='password123')
        self.vendedor_profile = UserProfile.objects.create(user=self.vendedor_user, rol='VENDEDOR')

        self.otro_vendedor = User.objects.create_user(username='otro', password='password123')
        self.otro_profile = UserProfile.objects.create(user=self.otro_vendedor, rol='VENDEDOR')

        # 1.5. Crear Ubicación
        self.ubicacion = CatUbicacion.objects.create(ciudad='Querétaro', estado='Querétaro')

        # 1.6. Crear Especialidades y Productos
        self.esp_veterinario = CatEspecialidad.objects.create(nombre='Veterinario')
        self.esp_fisioterapeuta = CatEspecialidad.objects.create(nombre='Fisioterapeuta')
        
        self.prod_pet = CatProducto.objects.create(nombre='Laser IR Pet', familia='EQUIPO')
        self.prod_sport = CatProducto.objects.create(nombre='Laser IR Sport', familia='EQUIPO')

        # 2. Crear Clientes
        self.cliente_pet = CoreLead.objects.create(
            nombre_pila='Juan',
            apellido_paterno='Perez',
            phone_primary='1234567890',
            estatus='CLIENTE',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion,
            especialidad_cat=self.esp_veterinario,
            producto_cat=self.prod_pet
        )

        self.cliente_sport = CoreLead.objects.create(
            nombre_pila='Carlos',
            apellido_paterno='Gomez',
            phone_primary='1112224444',
            estatus='CLIENTE',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion,
            especialidad_cat=self.esp_fisioterapeuta,
            producto_cat=self.prod_sport
        )

        self.prospecto = CoreLead.objects.create(
            nombre_pila='Pedro',
            apellido_paterno='Gomez',
            phone_primary='0987654321',
            estatus='PROSPECTO',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion,
            especialidad_cat=self.esp_veterinario,
            producto_cat=self.prod_pet
        )

        self.cliente_otro = CoreLead.objects.create(
            nombre_pila='Maria',
            apellido_paterno='Lopez',
            phone_primary='1112223333',
            estatus='CLIENTE',
            owner=self.otro_vendedor,
            ubicacion=self.ubicacion,
            especialidad_cat=self.esp_veterinario,
            producto_cat=self.prod_pet
        )

        # 3. Crear Eventos
        self.taller = Evento.objects.create(
            nombre='Taller Laser Test',
            tipo='TALLER',
            linea_producto='SPORT',
            fecha_inicio='2026-06-01',
            fecha_fin='2026-06-05',
            estatus='ACTIVO'
        )
        self.taller.vendedores_asignados.add(self.vendedor_user)

        self.campana = Evento.objects.create(
            nombre='Campaña Test',
            tipo='CAMPAÑA',
            linea_producto='PET',
            fecha_inicio='2026-06-10',
            fecha_fin='2026-06-15',
            estatus='ACTIVO'
        )
        self.campana.vendedores_asignados.add(self.vendedor_user)

        self.expo = Evento.objects.create(
            nombre='Expo Test',
            tipo='EXPO',
            linea_producto='TODAS',
            fecha_inicio='2026-06-20',
            fecha_fin='2026-06-25',
            estatus='ACTIVO'
        )
        self.expo.vendedores_asignados.add(self.vendedor_user)

        # Cliente HTTP
        self.client = Client()

    def test_obtener_eventos_cliente_no_auth(self):
        url = reverse('eventos_cliente')
        response = self.client.get(url, {'lead_id': str(self.cliente_pet.id)})
        self.assertEqual(response.status_code, 302) # Redirecciona a login

    def test_obtener_eventos_cliente_exito(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('eventos_cliente')
        response = self.client.get(url, {'lead_id': str(self.cliente_pet.id)})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Por defecto, Veterinario es compatible con PET (Campaña) pero no con SPORT (Taller)
        self.assertEqual(len(data['eventos']), 1)
        event_names = [ev['nombre'] for ev in data['eventos']]
        self.assertIn('Campaña Test', event_names)
        self.assertNotIn('Taller Laser Test', event_names)
        self.assertNotIn('Expo Test', event_names)

    def test_obtener_eventos_cliente_con_excepcion_permitida(self):
        # Crear excepción para permitir Veterinario en SPORT
        ExcepcionEspecialidadLinea.objects.create(
            especialidad=self.esp_veterinario,
            linea_producto='SPORT',
            permitido=True
        )
        self.client.login(username='testvendedor', password='password123')
        url = reverse('eventos_cliente')
        response = self.client.get(url, {'lead_id': str(self.cliente_pet.id)})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Ahora debe ver tanto Campaña Test (por defecto) como Taller Laser Test (por excepción)
        self.assertEqual(len(data['eventos']), 2)
        event_names = [ev['nombre'] for ev in data['eventos']]
        self.assertIn('Campaña Test', event_names)
        self.assertIn('Taller Laser Test', event_names)

    def test_obtener_eventos_cliente_con_excepcion_bloqueada(self):
        # Crear excepción para bloquear Veterinario en PET
        ExcepcionEspecialidadLinea.objects.create(
            especialidad=self.esp_veterinario,
            linea_producto='PET',
            permitido=False
        )
        self.client.login(username='testvendedor', password='password123')
        url = reverse('eventos_cliente')
        response = self.client.get(url, {'lead_id': str(self.cliente_pet.id)})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Ahora no debe ver ningún evento (PET está bloqueado por excepción, SPORT no es compatible por defecto)
        self.assertEqual(len(data['eventos']), 0)

    def test_obtener_eventos_cliente_solo_cliente_status(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('eventos_cliente')
        # Intentar obtener eventos para un lead con estatus PROSPECTO
        response = self.client.get(url, {'lead_id': str(self.prospecto.id)})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('no es de estatus CLIENTE', data['error'])

    def test_vincular_cliente_evento_prospecto_error(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('vincular_cliente_evento')
        payload = {
            'lead_id': str(self.prospecto.id),
            'evento_id': self.taller.id,
            'accion': 'vincular'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('estatus CLIENTE', data['error'])

    def test_vincular_desvincular_cliente_evento_exito(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('vincular_cliente_evento')
        
        # 1. Vincular
        payload = {
            'lead_id': str(self.cliente_pet.id),
            'evento_id': self.taller.id,
            'accion': 'vincular'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        from leads.models import LeadEvento
        self.assertTrue(LeadEvento.objects.filter(lead=self.cliente_pet, evento=self.taller).exists())

        # 2. Desvincular
        payload['accion'] = 'desvincular'
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(LeadEvento.objects.filter(lead=self.cliente_pet, evento=self.taller).exists())

    def test_vincular_cliente_evento_otro_vendedor_error(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('vincular_cliente_evento')
        # Intentar vincular un cliente propiedad de 'otro_vendedor'
        payload = {
            'lead_id': str(self.cliente_otro.id),
            'evento_id': self.taller.id,
            'accion': 'vincular'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])

    def test_filtrado_clientes_por_especialidad_y_producto(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('ventas_360')
        
        # 1. Ver prospectos de campaña de Línea PET (debe incluir cliente_pet, no cliente_sport)
        response = self.client.get(url, {'tab': 'campanas', 'evento_id': self.campana.id})
        self.assertEqual(response.status_code, 200)
        prospectos = list(response.context['prospectos_campana'])
        prospecto_ids = [p.id for p in prospectos]
        self.assertIn(self.cliente_pet.id, prospecto_ids)
        self.assertNotIn(self.cliente_sport.id, prospecto_ids)

        # 2. Ver prospectos de taller de Línea SPORT (debe incluir cliente_sport, no cliente_pet)
        response = self.client.get(url, {'tab': 'talleres', 'evento_id': self.taller.id})
        self.assertEqual(response.status_code, 200)
        prospectos = list(response.context['prospectos_campana'])
        prospecto_ids = [p.id for p in prospectos]
        self.assertIn(self.cliente_sport.id, prospecto_ids)
        self.assertNotIn(self.cliente_pet.id, prospecto_ids)

    def test_filtrado_clientes_por_especialidad_con_excepcion(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('ventas_360')
        
        # Bloquear Fisioterapeuta de SPORT
        ExcepcionEspecialidadLinea.objects.create(
            especialidad=self.esp_fisioterapeuta,
            linea_producto='SPORT',
            permitido=False
        )
        
        # Ahora cliente_sport no debería aparecer en SPORT (taller) porque Fisioterapeuta está bloqueado por excepción
        response = self.client.get(url, {'tab': 'talleres', 'evento_id': self.taller.id})
        self.assertEqual(response.status_code, 200)
        prospectos = list(response.context['prospectos_campana'])
        prospecto_ids = [p.id for p in prospectos]
        self.assertNotIn(self.cliente_sport.id, prospecto_ids)
        
        # Crear un cliente con Veterinario (especialidad no SPORT) pero con producto Sport
        cliente_vet_sport = CoreLead.objects.create(
            nombre_pila='VetySport',
            apellido_paterno='Gomez',
            phone_primary='1231231234',
            estatus='CLIENTE',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion,
            especialidad_cat=self.esp_veterinario,
            producto_cat=self.prod_sport
        )
        
        # Permitir Veterinario en SPORT
        ExcepcionEspecialidadLinea.objects.create(
            especialidad=self.esp_veterinario,
            linea_producto='SPORT',
            permitido=True
        )
        
        # Ahora cliente_vet_sport debería aparecer en SPORT (taller) porque su especialidad fue explícitamente permitida
        response = self.client.get(url, {'tab': 'talleres', 'evento_id': self.taller.id})
        self.assertEqual(response.status_code, 200)
        prospectos = list(response.context['prospectos_campana'])
        prospecto_ids = [p.id for p in prospectos]
        self.assertIn(cliente_vet_sport.id, prospecto_ids)
