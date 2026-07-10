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


class DetalleEventoAPITestCase(TestCase):
    def setUp(self):
        # 1. Crear usuarios (Superuser y Vendedor)
        self.director_user = User.objects.create_superuser(username='director', password='password123')
        self.vendedor_user = User.objects.create_user(username='vendedor', password='password123')
        
        # 2. Crear Ubicación y Especialidad
        self.ubicacion = CatUbicacion.objects.create(ciudad='Guadalajara', estado='Jalisco')
        self.especialidad = CatEspecialidad.objects.create(nombre='Podólogo')
        
        # 3. Crear Evento
        self.evento = Evento.objects.create(
            nombre='Taller Láser Guadalajara',
            tipo='TALLER',
            fecha_inicio='2026-08-10',
            fecha_fin='2026-08-12',
            lugar='Expo Guadalajara',
            linea_producto='PODOLOGICO'
        )
        self.evento.vendedores_asignados.add(self.vendedor_user)
        
        # 4. Crear Clientes
        self.cliente1 = CoreLead.objects.create(
            nombre_pila='Juan',
            apellido_paterno='López',
            phone_primary='1234567890',
            estatus='CLIENTE',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion,
            especialidad_cat=self.especialidad
        )
        
        self.cliente2 = CoreLead.objects.create(
            nombre_pila='Maria',
            apellido_paterno='Sánchez',
            phone_primary='0987654321',
            estatus='CLIENTE',
            owner=self.director_user, # Dejar al director como owner de este para tener dos dueños distintos
            ubicacion=self.ubicacion,
            especialidad_cat=self.especialidad
        )
        
        # 5. Vincular Clientes al Evento
        LeadEvento.objects.create(evento=self.evento, lead=self.cliente1, comentarios='Confirmado asistencia')
        LeadEvento.objects.create(evento=self.evento, lead=self.cliente2, comentarios='Interesado en segunda parte')

    def test_api_detalle_evento_acceso_director(self):
        self.client.login(username='director', password='password123')
        url = reverse('api_detalle_evento', kwargs={'evento_id': self.evento.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_registros'], 2)
        
        # Verificar información del evento
        self.assertEqual(data['evento']['nombre'], 'Taller Láser Guadalajara')
        self.assertEqual(data['evento']['tipo'], 'TALLER')
        
        # Verificar listado de clientes
        clientes = data['clientes']
        nombres_clientes = [c['nombre'] for c in clientes]
        self.assertIn('Juan López', nombres_clientes)
        self.assertIn('Maria Sánchez', nombres_clientes)
        
        # Verificar comentarios
        comentarios = [c['comentarios'] for c in clientes]
        self.assertIn('Confirmado asistencia', comentarios)
        
        # Verificar estadísticas por vendedor
        vendedores_stats = data['vendedores_stats']
        # Deben reportarse contribuciones para ambos dueños
        self.assertEqual(len(vendedores_stats), 2)
        cantidades = [s['cantidad'] for s in vendedores_stats]
        self.assertIn(1, cantidades)

    def test_api_detalle_evento_acceso_denegado_vendedor(self):
        self.client.login(username='vendedor', password='password123')
        url = reverse('api_detalle_evento', kwargs={'evento_id': self.evento.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'No autorizado')

    def test_api_detalle_evento_no_autenticado(self):
        url = reverse('api_detalle_evento', kwargs={'evento_id': self.evento.id})
        response = self.client.get(url)
        # Debería redirigir al login
        self.assertEqual(response.status_code, 302)


class DashboardFidelizacionTestCase(TestCase):
    def setUp(self):
        from leads.models import VentaTransaccional
        # 1. Crear usuarios (Superuser y Vendedor)
        self.director_user = User.objects.create_superuser(username='director', password='password123')
        self.vendedor_user = User.objects.create_user(username='vendedor', password='password123')
        
        # 2. Crear Ubicación y Especialidad
        self.ubicacion = CatUbicacion.objects.create(ciudad='Guadalajara', estado='Jalisco')
        self.especialidad = CatEspecialidad.objects.create(nombre='Podólogo')
        
        # 3. Crear Productos
        self.prod_acc = CatProducto.objects.create(nombre='Pieza de Mano Podológica', familia='ACCESORIO')
        self.prod_ser = CatProducto.objects.create(nombre='Mantenimiento Anual', familia='SERVICIO')
        
        # 4. Crear Eventos (Taller y Campaña)
        self.taller = Evento.objects.create(
            nombre='Taller Láser Guadalajara',
            tipo='TALLER',
            fecha_inicio='2026-08-10',
            fecha_fin='2026-08-12',
            lugar='Expo Guadalajara',
            linea_producto='PODOLOGICO'
        )
        self.campana = Evento.objects.create(
            nombre='Campaña Podológica Verano',
            tipo='CAMPAÑA',
            fecha_inicio='2026-06-01',
            fecha_fin='2026-06-30',
            linea_producto='PODOLOGICO'
        )
        
        # 5. Crear Clientes
        self.cliente_taller = CoreLead.objects.create(
            nombre_pila='Juan',
            apellido_paterno='López',
            phone_primary='1234567890',
            estatus='CLIENTE',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion,
            especialidad_cat=self.especialidad
        )
        self.cliente_campana = CoreLead.objects.create(
            nombre_pila='Maria',
            apellido_paterno='Sánchez',
            phone_primary='0987654321',
            estatus='CLIENTE',
            owner=self.vendedor_user,
            ubicacion=self.ubicacion,
            especialidad_cat=self.especialidad
        )
        
        # 6. Vincular Clientes a Eventos
        LeadEvento.objects.create(evento=self.taller, lead=self.cliente_taller)
        LeadEvento.objects.create(evento=self.campana, lead=self.cliente_campana)
        
        # 7. Crear Ventas Transaccionales
        # Venta concretada para cliente de taller
        self.venta1 = VentaTransaccional.objects.create(
            lead=self.cliente_taller,
            producto=self.prod_acc,
            vendedor=self.vendedor_user,
            monto=1500.00,
            estatus='CONCRETADO'
        )
        # Venta concretada para cliente de campaña
        self.venta2 = VentaTransaccional.objects.create(
            lead=self.cliente_campana,
            producto=self.prod_ser,
            vendedor=self.vendedor_user,
            monto=3000.00,
            estatus='CONCRETADO'
        )
        # Venta pendiente (no debería sumarse a facturado)
        self.venta3 = VentaTransaccional.objects.create(
            lead=self.cliente_taller,
            producto=self.prod_acc,
            vendedor=self.vendedor_user,
            monto=800.00,
            estatus='PENDIENTE'
        )

    def test_dashboard_fidelizacion_metrics_acceso_director(self):
        self.client.login(username='director', password='password123')
        url = reverse('director_fidelizacion')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar KPIs financieros en contexto
        self.assertEqual(response.context['monto_concretado'], 4500.00) # 1500 + 3000
        self.assertEqual(response.context['ticket_promedio'], 2250.00) # 4500 / 2
        
        # Verificar atribución
        self.assertEqual(response.context['monto_taller'], 1500.00)
        self.assertEqual(response.context['cantidad_taller'], 1)
        self.assertEqual(response.context['monto_campana'], 3000.00)
        self.assertEqual(response.context['cantidad_campana'], 1)
        
        # Verificar JSON de chart_familia_data
        chart_fam_data = json.loads(response.context['chart_familia_data'])
        self.assertEqual(chart_fam_data['labels'], ['Accesorios', 'Servicios', 'Eventos'])
        self.assertEqual(chart_fam_data['data'], [1, 1, 0]) # 1 accesorio concretado, 1 servicio concretado

    def test_dashboard_fidelizacion_acceso_denegado_vendedor(self):
        self.client.login(username='vendedor', password='password123')
        url = reverse('director_fidelizacion')
        response = self.client.get(url)
        # Debe redirigir o denegar (user_passes_test con login_url='dashboard_agente')
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard/agente/', response.url or '')


