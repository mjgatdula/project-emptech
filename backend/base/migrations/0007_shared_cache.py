from django.core.management import call_command
from django.db import migrations


def create_cache(apps, schema_editor):
    call_command('createcachetable', 'tipped_shared_cache', database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = [('base', '0006_google_identity')]
    operations = [migrations.RunPython(create_cache, migrations.RunPython.noop)]
