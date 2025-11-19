from django.apps import AppConfig

class CompaniesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.platform.companies'
    label = 'companies'
    verbose_name = 'Company Management'
