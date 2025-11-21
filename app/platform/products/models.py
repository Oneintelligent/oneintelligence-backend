"\"\"\"Module registry models (placeholder).\"\"\""
from django.db import models

from app.core.models import CoreBaseModel


class ModuleDefinition(CoreBaseModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=64, default="workspace")
    description = models.TextField(blank=True)
    plans = models.JSONField(default=list, blank=True)  # e.g., ["pro", "promax"]
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "platform_module_definitions"


class CompanyModule(CoreBaseModel):
    company_id = models.UUIDField()
    module = models.ForeignKey(ModuleDefinition, on_delete=models.CASCADE, related_name="company_modules")
    enabled = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "platform_company_modules"
        unique_together = ("company_id", "module")

