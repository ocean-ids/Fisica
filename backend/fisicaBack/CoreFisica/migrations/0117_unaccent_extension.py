from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('CoreFisica', '0116_merge_santodomingo_y_cantones'),
    ]

    operations = [
        UnaccentExtension(),
    ]
