from django.apps import AppConfig


class LicensingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.platform.licensing'
    label = 'licensing'
    verbose_name = 'Licensing & Seat Management'

