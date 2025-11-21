from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.platform.rbac'
    verbose_name = 'Role-Based Access Control'

