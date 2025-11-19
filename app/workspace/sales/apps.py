from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.workspace.sales'
    label = 'sales'
    verbose_name = 'Sales & CRM'

