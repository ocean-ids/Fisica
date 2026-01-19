# Script de migración de datos de dia_1...dia_31 a Asistencia
# Ejecutar después de aplicar la migración 0007

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Migra los datos de dia_1 a dia_31 del modelo antiguo a registros de Asistencia'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  NOTA: Este script solo funciona ANTES de eliminar los campos dia_1...dia_31'))
        self.stdout.write(self.style.WARNING('    Úsalo como referencia si necesitas migrar datos antiguos guardados'))
        
        # Ejemplo de cómo se haría la migración si aún existieran los campos
        ejemplo_codigo = '''
# Este código solo funcionaría si los campos dia_1...dia_31 aún existieran:

total_migrated = 0
errors = []

for asignacion in Asignacion.objects.all():
    try:
        mes = asignacion.mes
        anio = asignacion.anio
        
        # Obtener número de días del mes
        num_dias = calendar.monthrange(anio, mes)[1]
        
        for dia in range(1, num_dias + 1):
            # Obtener el valor del campo dia_X
            valor_dia = getattr(asignacion, f'dia_{dia}', None)
            
            if valor_dia:
                # Parsear el valor (ej: "D", "N", "DS30", "NF", etc.)
                turno = None
                codigo_cliente = None
                estado = 'NORMAL'
                
                valor = valor_dia.strip().upper()
                
                # Detectar turno
                if valor.startswith('D'):
                    turno = 'D'
                    resto = valor[1:]
                elif valor.startswith('N'):
                    turno = 'N'
                    resto = valor[1:]
                else:
                    resto = valor
                
                # Detectar estado
                if 'F' in resto:
                    estado = 'FRANCO'
                elif 'DISP' in resto:
                    estado = 'DISPONIBLE'
                
                # Extraer código cliente (ej: S30)
                if resto and not resto in ['F', 'DISP']:
                    codigo_cliente = resto
                
                # Crear fecha
                fecha = date(anio, mes, dia)
                
                # Crear registro de asistencia
                Asistencia.objects.get_or_create(
                    asignacion=asignacion,
                    fecha=fecha,
                    defaults={
                        'turno': turno,
                        'codigo_cliente': codigo_cliente,
                        'estado': estado,
                    }
                )
                total_migrated += 1
        
        self.stdout.write(f'✓ Migrada asignación {asignacion.id}')
        
    except Exception as e:
        errors.append(f'Error en asignación {asignacion.id}: {str(e)}')
        self.stdout.write(self.style.ERROR(f'✗ Error en asignación {asignacion.id}: {e}'))

self.stdout.write(self.style.SUCCESS(f'\\n✓ Migración completada: {total_migrated} registros de asistencia creados'))
if errors:
    self.stdout.write(self.style.ERROR(f'\\nErrores ({len(errors)}):'))
    for error in errors:
        self.stdout.write(self.style.ERROR(f'  - {error}'))
        '''
        
        self.stdout.write(self.style.SUCCESS('\n📝 Código de referencia para migración manual:'))
        self.stdout.write(ejemplo_codigo)
        self.stdout.write(self.style.SUCCESS('\n✓ Script de referencia generado'))
