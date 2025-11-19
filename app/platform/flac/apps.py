from django.apps import AppConfig


class FieldLevelAccessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.platform.flac'
    label = 'flac'
    verbose_name = 'Field-Level Access Control'
