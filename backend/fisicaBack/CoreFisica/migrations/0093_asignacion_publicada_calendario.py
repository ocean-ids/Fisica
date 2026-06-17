from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0092_alter_asignacion_options'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE \"CoreFisica_asignacion\" ADD COLUMN IF NOT EXISTS \"publicada_calendario\" boolean DEFAULT FALSE NOT NULL;",
                    "ALTER TABLE \"CoreFisica_asignacion\" DROP COLUMN IF EXISTS \"publicada_calendario\";"
                ),
                migrations.RunSQL(
                    "CREATE INDEX IF NOT EXISTS \"CoreFisica_asignacion_publicada_calendario_idx\" ON \"CoreFisica_asignacion\" (\"publicada_calendario\");",
                    "DROP INDEX IF EXISTS \"CoreFisica_asignacion_publicada_calendario_idx\";"
                ),
                migrations.RunSQL(
                    "UPDATE \"CoreFisica_asignacion\" SET \"publicada_calendario\" = TRUE WHERE \"publicada_calendario\" IS NULL;",
                    migrations.RunSQL.noop
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='asignacion',
                    name='publicada_calendario',
                    field=models.BooleanField(default=False, db_index=True),
                ),
            ],
        ),
    ]
