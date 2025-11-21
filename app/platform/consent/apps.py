"""
Consent Management App Config
"""

from django.apps import AppConfig


class ConsentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.platform.consent'
    verbose_name = 'Consent Management'

