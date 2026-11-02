from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('base', '0005_notification_audience'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='GOOGLE_IDENTITY', fields=[
        ('user', models.OneToOneField(primary_key=True, serialize=False, on_delete=django.db.models.deletion.CASCADE, related_name='google_identity', to=settings.AUTH_USER_MODEL)),
        ('subject', models.CharField(max_length=255, unique=True)),
        ('verified_email', models.EmailField(max_length=254)),
        ('linked_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
    ])]
