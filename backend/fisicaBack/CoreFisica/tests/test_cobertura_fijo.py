"""Cobertura de FIJO: un fijo con token D/N + nominativo (ej. DK37) ese dia cubre OTRA
instalacion -> sale en el reporte bajo ese nominativo, no en su puesto propio."""
import datetime
from django.test import TestCase
from django.utils import timezone

from CoreFisica.models import (
    Provincia, Canton, Cliente, Instalacion, Puesto, Persona, Asignacion, AsignacionSemanal,
)
from CoreFisica.views.reporte_asistencia_views import _build_reporte_asistencia_data
from CoreFisica.views.importar_puestos_asignaciones import _cal_valor_ok


class CoberturaFijoTests(TestCase):
    def test_cal_valor_ok_acepta_cobertura_en_fijo(self):
        # Fijo ahora acepta tokens de COBERTURA (D/N + nominativo), ademas de D/N/F/T/V.
        self.assertTrue(_cal_valor_ok('DK37', es_saca=False))
        self.assertTrue(_cal_valor_ok('NK35', es_saca=False))
        self.assertTrue(_cal_valor_ok('D', es_saca=False))
        self.assertTrue(_cal_valor_ok('F', es_saca=False))
        # Base (DB/NB) NO es cobertura -> el fijo no lo acepta.
        self.assertFalse(_cal_valor_ok('DB', es_saca=False))
        # Basura -> no reconocido.
        self.assertFalse(_cal_valor_ok('XYZ', es_saca=False))

    def _rows(self, res):
        return res[0] if isinstance(res, tuple) else res

    def test_fijo_con_token_cobertura_sale_bajo_nominativo(self):
        prov, _ = Provincia.objects.get_or_create(nombre='GUAYAS')
        can, _ = Canton.objects.get_or_create(nombre='GUAYAQUIL', provincia=prov)
        cliA = Cliente.objects.create(razon_social='CLIA', nombre_comercial='CLIENTE A')
        cliB = Cliente.objects.create(razon_social='CLIB', nombre_comercial='CELCO GYE')
        instA = Instalacion.objects.create(cliente=cliA, canton=can, nombre='PUESTO PROPIO', codigo='K35')
        instB = Instalacion.objects.create(cliente=cliB, canton=can, nombre='CELCO GUAYAQUIL', codigo='K37')
        puestoA = Puesto.objects.create(instalacion=instA, nombre='PUESTO PROPIO', tipo='CONTROL')
        Puesto.objects.create(instalacion=instB, nombre='CELCO GUAYAQUIL', tipo='CONTROL')
        persona = Persona.objects.create(cedula='0900000001', nombres='LUIS', apellidos='TEST', tipo='FIJOS', is_active=True)

        hoy = timezone.localdate()
        fecha = datetime.date(hoy.year, hoy.month, 15)
        month_start = fecha.replace(day=1)
        if fecha.month == 12:
            end = datetime.date(fecha.year, 12, 31)
        else:
            end = datetime.date(fecha.year, fecha.month + 1, 1) - datetime.timedelta(days=1)

        asig = Asignacion.objects.create(
            persona=persona, cliente=cliA, instalacion=instA, puesto=puestoA,
            mes=fecha.month, anio=fecha.year, estado='ACTIVO',
            recurring=True, start_date=month_start, end_date=end, fecha=None,
        )
        # Calendario: el dia 15 con token de cobertura DK37 (cubre K37 en Diurno).
        ws = month_start + datetime.timedelta(days=((15 - 1) // 7) * 7)
        day_field = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][fecha.weekday()]
        sem = AsignacionSemanal.objects.create(asignacion=asig, puesto=puestoA, week_start=ws)
        setattr(sem, day_field, 'DK37')
        sem.save()

        rows = self._rows(_build_reporte_asistencia_data(fecha=fecha.isoformat(), turno='Diurno'))
        fila = [r for r in rows if isinstance(r, dict) and r.get('asignacion_id') == asig.id]
        self.assertEqual(len(fila), 1, 'el fijo debe aparecer en Diurno ese dia')
        # Debe salir bajo el nominativo CUBIERTO (K37), no en su puesto propio (K35).
        self.assertEqual(fila[0].get('codigo'), 'K37')
        self.assertEqual(fila[0].get('cliente'), 'CELCO GYE')
        self.assertEqual(fila[0].get('instalacion_nombre'), 'CELCO GUAYAQUIL')

        # En un dia NORMAL (D) sale en su puesto propio (K35).
        otro = datetime.date(hoy.year, hoy.month, 16)
        ws2 = month_start + datetime.timedelta(days=((16 - 1) // 7) * 7)
        df2 = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][otro.weekday()]
        sem2, _ = AsignacionSemanal.objects.get_or_create(asignacion=asig, week_start=ws2, defaults={'puesto': puestoA})
        setattr(sem2, df2, 'D')
        sem2.save()
        rows2 = self._rows(_build_reporte_asistencia_data(fecha=otro.isoformat(), turno='Diurno'))
        fila2 = [r for r in rows2 if isinstance(r, dict) and r.get('asignacion_id') == asig.id]
        self.assertEqual(len(fila2), 1)
        self.assertEqual(fila2[0].get('codigo'), 'K35', 'dia normal -> su puesto propio')
