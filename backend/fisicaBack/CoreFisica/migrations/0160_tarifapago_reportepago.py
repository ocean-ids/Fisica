from django.db import migrations, models
import django.db.models.deletion


def seed_tarifas(apps, schema_editor):
    Tarifa = apps.get_model('CoreFisica', 'TarifaPago')
    data = {
        'Guardias fijos':                        [(1, 3, 5), (4, 6, 10), (7, 9, 15), (10, 12, 20), (13, 15, 25)],
        'Horas extras supervisor fijo':          [(1, 3, 7.5), (4, 6, 15), (7, 9, 22.5), (10, 12, 30), (13, 15, 37.5)],
        'Eventuales':                            [(1, 3, 6.25), (4, 6, 12.5), (7, 9, 18.75), (10, 12, 25), (13, 15, 31.25)],
        'Supervisores eventuales':               [(1, 3, 8.75), (4, 6, 17.5), (7, 9, 26.25), (10, 12, 35), (13, 15, 43.75)],
        'Servicios adicionales personal fijos':  [(1, 6, 12), (7, 9, 15), (10, 12, 25), (13, 15, 25)],
    }
    orden = 0
    for tipo, bandas in data.items():
        for (hmin, hmax, valor) in bandas:
            Tarifa.objects.get_or_create(
                tipo_servicio=tipo, horas_min=hmin, horas_max=hmax,
                defaults={'valor': valor, 'orden': orden},
            )
            orden += 1


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0159_reportevacaciones_anio'),
    ]

    operations = [
        migrations.CreateModel(
            name='TarifaPago',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_servicio', models.CharField(db_index=True, max_length=80)),
                ('horas_min', models.PositiveIntegerField()),
                ('horas_max', models.PositiveIntegerField()),
                ('valor', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['tipo_servicio', 'horas_min'],
                'unique_together': {('tipo_servicio', 'horas_min', 'horas_max')},
            },
        ),
        migrations.CreateModel(
            name='ReportePago',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(db_index=True)),
                ('turno', models.CharField(choices=[('Diurno', 'Diurno'), ('Nocturno', 'Nocturno')], db_index=True, max_length=10)),
                ('seccion', models.CharField(blank=True, default='', max_length=15)),
                ('cliente', models.CharField(blank=True, default='', max_length=120)),
                ('puesto', models.CharField(blank=True, default='', max_length=160)),
                ('persona_nombre', models.CharField(blank=True, default='', max_length=160)),
                ('cedula', models.CharField(blank=True, default='', max_length=20)),
                ('banco', models.CharField(blank=True, default='', max_length=80)),
                ('tipo_cuenta', models.CharField(blank=True, default='', max_length=20)),
                ('numero_cuenta', models.CharField(blank=True, default='', max_length=30)),
                ('tipo_servicio', models.CharField(blank=True, default='', max_length=80)),
                ('horas', models.PositiveIntegerField(blank=True, null=True)),
                ('valor_calculado', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('valor_total', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('referencia', models.CharField(blank=True, default='', max_length=200)),
                ('auto', models.BooleanField(default=True)),
                ('orden', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('persona_ref', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pagos', to='CoreFisica.persona')),
                ('reporte_guardia_ref', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pagos', to='CoreFisica.reporteguardia')),
            ],
            options={
                'ordering': ['fecha', 'turno', 'orden', 'id'],
            },
        ),
        migrations.RunPython(seed_tarifas, noop),
    ]
