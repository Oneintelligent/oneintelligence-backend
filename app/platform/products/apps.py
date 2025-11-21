from django.apps import AppConfig


class ModulesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.platform.products'
    label = 'products'
    verbose_name = 'Product Registry'

