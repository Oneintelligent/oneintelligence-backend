from django.apps import AppConfig


class ModulesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.platform.modules'
    label = 'modules'
    verbose_name = 'Module Registry'

