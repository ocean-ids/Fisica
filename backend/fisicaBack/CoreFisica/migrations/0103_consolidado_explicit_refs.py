from django.db import migrations, models


def forward_fill_explicit_refs(apps, schema_editor):
    Consolidado = apps.get_model('CoreFisica', 'Consolidado')
    Persona = apps.get_model('CoreFisica', 'Persona')
    Asignacion = apps.get_model('CoreFisica', 'Asignacion')

    for row in Consolidado.objects.all().iterator():
        ref_id = row.referencia_id
        if not ref_id:
            continue

        if row.tipo == 'CONSOLa':
            if Persona.objects.filter(id=ref_id).exists():
                row.persona_ref_id = ref_id
                row.asignacion_ref_id = None
                row.save(update_fields=['persona_ref'])
        elif row.tipo == 'GUARDIA':
            if Asignacion.objects.filter(id=ref_id).exists():
                row.asignacion_ref_id = ref_id
                row.persona_ref_id = None
                row.save(update_fields=['asignacion_ref'])


def backward_fill_reference_id(apps, schema_editor):
    Consolidado = apps.get_model('CoreFisica', 'Consolidado')

    for row in Consolidado.objects.all().iterator():
        if row.tipo == 'CONSOLa' and row.persona_ref_id:
            row.referencia_id = row.persona_ref_id
            row.save(update_fields=['referencia_id'])
        elif row.tipo == 'GUARDIA' and row.asignacion_ref_id:
            row.referencia_id = row.asignacion_ref_id
            row.save(update_fields=['referencia_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0102_consolidado_puesto'),
    ]

    operations = [
        migrations.AddField(
            model_name='consolidado',
            name='asignacion_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='consolidados', to='CoreFisica.asignacion'),
        ),
        migrations.AddField(
            model_name='consolidado',
            name='persona_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='consolidados', to='CoreFisica.persona'),
        ),
        migrations.RunPython(forward_fill_explicit_refs, backward_fill_reference_id),
        migrations.AddIndex(
            model_name='consolidado',
            index=models.Index(fields=['tipo', 'persona_ref'], name='CoreFisica__tipo_a0c34c_idx'),
        ),
        migrations.AddIndex(
            model_name='consolidado',
            index=models.Index(fields=['tipo', 'asignacion_ref'], name='CoreFisica__tipo_d5ead1_idx'),
        ),
        migrations.AddConstraint(
            model_name='consolidado',
            constraint=models.CheckConstraint(
                check=(
                    ~models.Q(tipo='CONSOLa') |
                    (
                        models.Q(asignacion_ref__isnull=True) &
                        (models.Q(persona_ref__isnull=False) | models.Q(referencia_id__gt=0))
                    )
                ),
                name='corefisica_consolidado_consola_ref_ck',
            ),
        ),
        migrations.AddConstraint(
            model_name='consolidado',
            constraint=models.CheckConstraint(
                check=(
                    ~models.Q(tipo='GUARDIA') |
                    (
                        models.Q(persona_ref__isnull=True) &
                        (models.Q(asignacion_ref__isnull=False) | models.Q(referencia_id__gt=0))
                    )
                ),
                name='corefisica_consolidado_guardia_ref_ck',
            ),
        ),
    ]
