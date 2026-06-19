"""Consolida puestos duplicados (mismo nombre+instalacion+zona+tipo) en uno solo.

Contexto: el import antiguo creaba N registros de Puesto cuando la "cantidad" era N.
Con el modelo nuevo un puesto es UN registro con N cupos (cantidad_puestos). Este
comando fusiona esos duplicados:

  - Elige un puesto PRINCIPAL por grupo (el de menor id).
  - Reapunta al principal todo lo que dependa de los duplicados:
      Asignacion, AsignacionSemanal, SacafrancoFila, ReporteAsistencia, NovedadPuesto.
  - Fija cantidad_puestos del principal = numero de registros del grupo (cada uno = 1 cupo).
  - Borra los registros sobrantes (sus PuestoHorario se eliminan en cascada).

Seguridad:
  - Por defecto es DRY-RUN: solo muestra lo que haria, no toca nada.
  - Para aplicar: --apply
  - Filtros opcionales: --nombre "CREATIVAESCOOL"  --instalacion 137

Nota: Asignacion tiene unique_together (persona, mes, anio), por lo que una persona
no puede estar en dos puestos el mismo mes; reapuntar no genera colisiones de persona.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from CoreFisica.models import (
    Puesto, Asignacion, AsignacionSemanal,
    CoberturaSacafranco, ReporteAsistencia, NovedadPuesto,
)


class Command(BaseCommand):
    help = "Fusiona puestos duplicados (mismo nombre+instalacion+zona+tipo) en uno solo con la capacidad correcta."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Aplica los cambios. Sin esta bandera solo simula (dry-run).')
        parser.add_argument('--nombre', type=str, default=None,
                            help='Filtra por nombre exacto del puesto (opcional).')
        parser.add_argument('--instalacion', type=int, default=None,
                            help='Filtra por id de instalacion (opcional).')

    def handle(self, *args, **opts):
        apply = opts['apply']
        f_nombre = opts.get('nombre')
        f_inst = opts.get('instalacion')

        qs = Puesto.objects.all()
        if f_nombre:
            qs = qs.filter(nombre=f_nombre)
        if f_inst:
            qs = qs.filter(instalacion_id=f_inst)

        # Agrupar por (nombre, instalacion, zona, tipo): solo duplicados reales.
        grupos = (qs.values('nombre', 'instalacion_id', 'zona_id', 'tipo')
                    .annotate(n=Count('id'))
                    .filter(n__gt=1)
                    .order_by('nombre'))

        if not grupos:
            self.stdout.write(self.style.SUCCESS('No hay puestos duplicados con esos criterios.'))
            return

        modo = 'APLICAR' if apply else 'DRY-RUN (simulacion)'
        self.stdout.write(self.style.WARNING(f'== Consolidacion de puestos duplicados [{modo}] =='))

        total_grupos = 0
        total_borrar = 0
        total_asig = total_sem = total_saca = total_rep = total_nov = 0

        for g in grupos:
            ids = list(qs.filter(
                nombre=g['nombre'], instalacion_id=g['instalacion_id'],
                zona_id=g['zona_id'], tipo=g['tipo'],
            ).order_by('id').values_list('id', flat=True))
            if len(ids) < 2:
                continue
            principal = ids[0]
            secundarios = ids[1:]
            capacidad = len(ids)

            n_asig = Asignacion.objects.filter(puesto_id__in=secundarios).count()
            n_sem = AsignacionSemanal.objects.filter(puesto_id__in=secundarios).count()
            n_saca = CoberturaSacafranco.objects.filter(puesto_id__in=secundarios).count()
            n_rep = ReporteAsistencia.objects.filter(puesto_id__in=secundarios).count()
            n_nov = NovedadPuesto.objects.filter(puesto_id__in=secundarios).count()

            total_grupos += 1
            total_borrar += len(secundarios)
            total_asig += n_asig
            total_sem += n_sem
            total_saca += n_saca
            total_rep += n_rep
            total_nov += n_nov

            self.stdout.write(
                f"\n- '{g['nombre']}' (inst {g['instalacion_id']}, zona {g['zona_id']}, tipo {g['tipo']})\n"
                f"    principal={principal}  fusiona={secundarios}  capacidad->{capacidad}\n"
                f"    reapunta: asign={n_asig} semanal={n_sem} saca={n_saca} reporte={n_rep} novedad={n_nov}"
            )

            if not apply:
                continue

            with transaction.atomic():
                Asignacion.objects.filter(puesto_id__in=secundarios).update(puesto_id=principal)
                AsignacionSemanal.objects.filter(puesto_id__in=secundarios).update(puesto_id=principal)
                CoberturaSacafranco.objects.filter(puesto_id__in=secundarios).update(puesto_id=principal)
                ReporteAsistencia.objects.filter(puesto_id__in=secundarios).update(puesto_id=principal)
                NovedadPuesto.objects.filter(puesto_id__in=secundarios).update(puesto_id=principal)
                # Los PuestoHorario de los secundarios se borran en cascada al borrar el puesto.
                Puesto.objects.filter(id__in=secundarios).delete()
                # Capacidad = numero de registros que tenia el grupo.
                p = Puesto.objects.get(id=principal)
                p.cantidad_puestos = capacidad
                try:
                    p.sync_from_horarios()
                except Exception:
                    pass
                p.save()

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('== Resumen =='))
        self.stdout.write(
            f'Grupos duplicados: {total_grupos}\n'
            f'Puestos a eliminar: {total_borrar}\n'
            f'Asignaciones reapuntadas: {total_asig}\n'
            f'Calendario (semanal): {total_sem}\n'
            f'Sacafranco: {total_saca}\n'
            f'Reportes: {total_rep}\n'
            f'Novedades: {total_nov}'
        )
        if apply:
            self.stdout.write(self.style.SUCCESS('\nConsolidacion APLICADA.'))
        else:
            self.stdout.write(self.style.NOTICE('\nDRY-RUN: no se modifico nada. Ejecuta con --apply para aplicar.'))
