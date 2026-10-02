from django.db import migrations

# Las bases que vienen de la prueba del módulo Eventuales (ya revertida) tienen en
# CoreFisica_reportevacaciones una columna "tipo" NOT NULL que el modelo no conoce: al crear un
# registro de Sacavacaciones la base rechaza el INSERT (IntegrityError, 500). Se le quita la
# restricción NOT NULL (los datos no se tocan). En bases sin esa columna no hace nada.
SQL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'CoreFisica_reportevacaciones' AND column_name = 'tipo'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE "CoreFisica_reportevacaciones" ALTER COLUMN "tipo" DROP NOT NULL;
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0202_horas_eventual_turno'),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]
