"""El banco se guarda solo con la ENTIDAD, en MAYÚSCULAS: 'Banco Pichincha' -> 'PICHINCHA'."""
from django.test import SimpleTestCase, TestCase

from CoreFisica.models import EmpleadoOtrosDatos, Persona, entidad_banco


class EntidadBancoTests(SimpleTestCase):
    def test_normaliza(self):
        casos = {
            'Banco Pichincha': 'PICHINCHA', 'BANCO PICHINCHA': 'PICHINCHA', 'pichincha': 'PICHINCHA',
            'Banco Guayaquil': 'GUAYAQUIL', 'Produbanco': 'PRODUBANCO', 'PRODUBANCO': 'PRODUBANCO',
            'Banco del Pacífico': 'PACIFICO', 'Banco de Machala': 'MACHALA',
            'Banco General Rumiñahui': 'GENERAL RUMIÑAHUI', 'BanEcuador': 'BANECUADOR',
            'Cooperativa Jardín Azuayo': 'COOPERATIVA JARDIN AZUAYO', 'Banco': 'BANCO',
            '  banco   bolivariano ': 'BOLIVARIANO', '': '', None: '',
        }
        for entrada, esperado in casos.items():
            self.assertEqual(entidad_banco(entrada), esperado, entrada)


class GuardarBancoTests(TestCase):
    def test_al_guardar_queda_la_entidad(self):
        p = Persona.objects.create(nombres='ANA', apellidos='LOPEZ', cedula='0999999991', tipo='EVENTUAL')
        od = EmpleadoOtrosDatos.objects.create(persona=p, banco='Banco del Pacífico')
        od.refresh_from_db()
        self.assertEqual(od.banco, 'PACIFICO')
