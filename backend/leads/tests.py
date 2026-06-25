# leads/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from users.models import UserProfile, CatUbicacion
from leads.models import CoreLead, Evento, LeadEvento
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

        # 2. Crear Clientes
        self.cliente = CoreLead.objects.create(
            nombre_pila='Juan',
            apellido_paterno='Perez',
            phone_primary='1234567890',
            estatus='CLIENTE',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion
        )

        self.prospecto = CoreLead.objects.create(
            nombre_pila='Pedro',
            apellido_paterno='Gomez',
            phone_primary='0987654321',
            estatus='PROSPECTO',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion
        )

        self.cliente_otro = CoreLead.objects.create(
            nombre_pila='Maria',
            apellido_paterno='Lopez',
            phone_primary='1112223333',
            estatus='CLIENTE',
            owner=self.otro_vendedor,
            ubicacion=self.ubicacion
        )

        # 3. Crear Eventos
        self.taller = Evento.objects.create(
            nombre='Taller Laser Test',
            tipo='TALLER',
            fecha_inicio='2026-06-01',
            fecha_fin='2026-06-05',
            estatus='ACTIVO'
        )
        self.taller.vendedores_asignados.add(self.vendedor_user)

        self.campana = Evento.objects.create(
            nombre='Campaña Test',
            tipo='CAMPAÑA',
            fecha_inicio='2026-06-10',
            fecha_fin='2026-06-15',
            estatus='ACTIVO'
        )
        self.campana.vendedores_asignados.add(self.vendedor_user)

        self.expo = Evento.objects.create(
            nombre='Expo Test',
            tipo='EXPO',
            fecha_inicio='2026-06-20',
            fecha_fin='2026-06-25',
            estatus='ACTIVO'
        )
        self.expo.vendedores_asignados.add(self.vendedor_user)

        # Cliente HTTP
        self.client = Client()

    def test_obtener_eventos_cliente_no_auth(self):
        url = reverse('eventos_cliente')
        response = self.client.get(url, {'lead_id': str(self.cliente.id)})
        self.assertEqual(response.status_code, 302) # Redirecciona a login

    def test_obtener_eventos_cliente_exito(self):
        self.client.login(username='testvendedor', password='password123')
        url = reverse('eventos_cliente')
        response = self.client.get(url, {'lead_id': str(self.cliente.id)})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Deben retornar Taller y Campaña, pero no la Expo
        self.assertEqual(len(data['eventos']), 2)
        event_names = [ev['nombre'] for ev in data['eventos']]
        self.assertIn('Taller Laser Test', event_names)
        self.assertIn('Campaña Test', event_names)
        self.assertNotIn('Expo Test', event_names)

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
            'lead_id': str(self.cliente.id),
            'evento_id': self.taller.id,
            'accion': 'vincular'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(LeadEvento.objects.filter(lead=self.cliente, evento=self.taller).exists())

        # 2. Desvincular
        payload['accion'] = 'desvincular'
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(LeadEvento.objects.filter(lead=self.cliente, evento=self.taller).exists())

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
