"""Cierra asignaciones mensuales solapadas poniendo end_date al día anterior
del inicio de la siguiente asignación del mismo (puesto, persona).

Problema: existen muchas asignaciones recurrentes (una por mes) con
recurring=True y end_date vacío, que nunca se cerraron. Todas quedan activas
para siempre y se solapan, por lo que un mismo día tiene VARIOS calendarios
activos (la del mes correcto + las de meses anteriores que rotan a D/N). Eso
hace que en días de franco (F) la persona igual aparezca en el reporte por la
asignación vieja, y que en días laborables salga duplicada.

Solución: dentro de cada grupo (puesto, persona), ordenar por start_date y
cerrar cada asignación (recurring sin end_date) el día anterior al inicio de la
siguiente. La última (más reciente) queda abierta. Idempotente y reversible
(para revertir: limpiar los end_date que esta corrida puso).

Uso:
  python manage.py cerrar_asignaciones_solapadas              # dry-run (no escribe)
  python manage.py cerrar_asignaciones_solapadas --apply      # aplica los cambios
  python manage.py cerrar_asignaciones_solapadas --cedula 0704511872   # enfocar una persona
"""
import datetime
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from CoreFisica.models import Asignacion


class Command(BaseCommand):
    help = 'Cierra (end_date) asignaciones mensuales solapadas para que no se pisen.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Aplica los cambios. Sin esta bandera es solo dry-run.')
        parser.add_argument('--cedula', default='',
                            help='Si se indica, muestra el detalle del chain de esa cédula.')

    def handle(self, *args, **options):
        apply = options.get('apply')
        cedula_focus = (options.get('cedula') or '').strip()

        qs = (Asignacion.objects
              .filter(estado='ACTIVO', persona__isnull=False, start_date__isnull=False)
              .select_related('persona')
              .values('id', 'puesto_id', 'persona_id', 'persona__cedula',
                      'start_date', 'end_date', 'recurring', 'mes', 'anio'))

        grupos = defaultdict(list)
        for a in qs:
            grupos[(a['puesto_id'], a['persona_id'])].append(a)

        a_cerrar = []          # (id, nuevo_end_date, start_actual)
        anomalias = []         # mismos start_date (no se pueden secuenciar)
        grupos_solapados = 0

        for key, asigs in grupos.items():
            if len(asigs) < 2:
                continue
            asigs.sort(key=lambda x: (x['start_date'], x['id']))
            grupos_solapados += 1
            for i in range(len(asigs) - 1):
                cur = asigs[i]
                nxt = asigs[i + 1]
                # misma fecha de inicio -> duplicado real, no secuenciable
                if nxt['start_date'] == cur['start_date']:
                    anomalias.append((cur['id'], nxt['id'], cur['start_date']))
                    continue
                nuevo_end = nxt['start_date'] - datetime.timedelta(days=1)
                if nuevo_end < cur['start_date']:
                    anomalias.append((cur['id'], nxt['id'], cur['start_date']))
                    continue
                # Solo cerrar las que bleed: recurring y sin end_date (o end_date que se pasa)
                end_actual = cur['end_date']
                if cur['recurring'] and (end_actual is None or end_actual > nuevo_end):
                    a_cerrar.append((cur['id'], nuevo_end, cur['start_date'], end_actual))

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Grupos (puesto+persona) con >1 asignación: {grupos_solapados}"))
        self.stdout.write(f"Asignaciones a cerrar (poner end_date): {len(a_cerrar)}")
        self.stdout.write(f"Anomalías (mismo start_date, NO se tocan): {len(anomalias)}")

        # Detalle de una cédula concreta
        if cedula_focus:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\nDetalle cédula {cedula_focus}:"))
            foco = [a for lst in grupos.values() for a in lst
                    if str(a['persona__cedula']) == cedula_focus]
            foco.sort(key=lambda x: (x['puesto_id'], x['start_date'], x['id']))
            cerrar_map = {c[0]: c[1] for c in a_cerrar}
            for a in foco:
                nuevo = cerrar_map.get(a['id'])
                marca = f"  -> nuevo end_date: {nuevo}" if nuevo else ""
                self.stdout.write(
                    f"  asig {a['id']} | mes/anio {a['mes']}/{a['anio']} | "
                    f"start {a['start_date']} | end {a['end_date']} | rec {a['recurring']}{marca}"
                )

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDRY-RUN: no se escribió nada. Ejecuta con --apply para aplicar."))
            return

        with transaction.atomic():
            n = 0
            for aid, nuevo_end, _start, _end in a_cerrar:
                Asignacion.objects.filter(id=aid).update(end_date=nuevo_end)
                n += 1
        self.stdout.write(self.style.SUCCESS(f"\nAplicado: {n} asignaciones cerradas."))
