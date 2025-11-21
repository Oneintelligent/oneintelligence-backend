"""Product registry viewsets."""
import logging
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from app.utils.response import api_response
from app.utils.exception_handler import format_validation_error
from app.platform.accounts.models import User
from .models import ModuleDefinition, CompanyModule
from .serializers import ModuleDefinitionSerializer, CompanyModuleSerializer
from .defaults import ensure_default_module_definitions

logger = logging.getLogger(__name__)


@extend_schema(tags=["Products"])
class ModuleDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ModuleDefinition.objects.all()
    serializer_class = ModuleDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]  # Changed from IsAdminUser to allow authenticated users

    @extend_schema(
        summary="List all available products",
        description="Public endpoint to list all available products for selection",
    )
    def list(self, request):
        """Public list of available products."""
        ensure_default_module_definitions()
        modules = ModuleDefinition.objects.all().order_by("category", "name")
        data = ModuleDefinitionSerializer(modules, many=True).data
        return api_response(200, "success", data)


@extend_schema(tags=["Company Products"])
class CompanyModuleViewSet(viewsets.ViewSet):
    serializer_class = CompanyModuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _handle_exception(self, exc, where=""):
        logger.exception(f"{where}: {exc}")
        from rest_framework.exceptions import ValidationError
        from rest_framework.serializers import ValidationError as SerializerValidationError
        
        if isinstance(exc, (ValidationError, SerializerValidationError)):
            error_message = format_validation_error(exc.detail)
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="failure",
                data={},
                error_code="VALIDATION_ERROR",
                error_message=error_message,
            )
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            status="failure",
            data={},
            error_code="SERVER_ERROR",
            error_message=str(exc),
        )

    @extend_schema(
        summary="Get enabled products for current user's company",
        description="Returns all products enabled for the authenticated user's company",
    )
    @action(detail=False, methods=["get"], url_path="company")
    def get_company_modules(self, request):
        """Get products enabled for the company."""
        try:
            user = request.user
            if not user.company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User is not associated with a company."
                )

            company_modules = CompanyModule.objects.filter(
                company_id=user.company.companyId,
                enabled=True
            ).select_related("module")

            data = CompanyModuleSerializer(company_modules, many=True).data
            return api_response(200, "success", {"products": data, "count": len(data)})

        except Exception as exc:
            return self._handle_exception(exc, "get_company_modules")

    @extend_schema(
        summary="Enable products for company",
        description="Enable one or more products for the authenticated user's company",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "module_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product codes to enable"
                    }
                }
            }
        },
    )
    @action(detail=False, methods=["post"], url_path="enable")
    @transaction.atomic
    def enable_modules(self, request):
        """Enable products for the company. Requires Super Admin or Admin role."""
        try:
            ensure_default_module_definitions()
            user = request.user
            if not user.company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User is not associated with a company."
                )
            
            # Check RBAC permissions
            from app.platform.rbac.utils import is_super_admin, is_company_admin
            
            if not (is_super_admin(user, company=user.company) or is_company_admin(user, company=user.company)):
                return api_response(
                    403, "failure", {},
                    "PERMISSION_DENIED",
                    "Only Super Admin or Admin can enable products."
                )

            module_codes = request.data.get("module_codes", [])
            if not isinstance(module_codes, list) or len(module_codes) == 0:
                return api_response(
                    400, "failure", {},
                    "INVALID_INPUT",
                    "module_codes must be a non-empty array."
                )

            # Get module definitions
            modules = ModuleDefinition.objects.filter(code__in=module_codes)
            found_codes = set(modules.values_list("code", flat=True))
            missing_codes = set(module_codes) - found_codes

            if missing_codes:
                return api_response(
                    400, "failure", {},
                    "MODULES_NOT_FOUND",
                    f"Modules not found: {', '.join(missing_codes)}"
                )

            # Enable modules (create or update)
            enabled_modules = []
            for module in modules:
                company_module, created = CompanyModule.objects.get_or_create(
                    company_id=user.company.companyId,
                    module=module,
                    defaults={"enabled": True}
                )
                if not created and not company_module.enabled:
                    company_module.enabled = True
                    company_module.save(update_fields=["enabled", "last_updated_date"])
                enabled_modules.append(company_module)

            # Update company products list
            user.company.products = list(found_codes)
            user.company.save(update_fields=["products", "last_updated_date"])

            data = CompanyModuleSerializer(enabled_modules, many=True).data
            return api_response(200, "success", {"products": data, "count": len(data)})

        except Exception as exc:
            return self._handle_exception(exc, "enable_modules")

    @extend_schema(
        summary="Disable a product for company",
        description="Disable a product for the authenticated user's company",
    )
    @action(detail=True, methods=["post"], url_path="disable")
    @transaction.atomic
    def disable_module(self, request, pk=None):
        """Disable a product for the company. Requires Super Admin or Admin role."""
        try:
            user = request.user
            if not user.company:
                return api_response(
                    400, "failure", {},
                    "NO_COMPANY",
                    "User is not associated with a company."
                )
            
            # Check RBAC permissions
            from app.platform.rbac.utils import is_super_admin, is_company_admin
            
            if not (is_super_admin(user, company=user.company) or is_company_admin(user, company=user.company)):
                return api_response(
                    403, "failure", {},
                    "PERMISSION_DENIED",
                    "Only Super Admin or Admin can disable products."
                )

            company_module = CompanyModule.objects.filter(
                company_id=user.company.companyId,
                module_id=pk
            ).first()

            if not company_module:
                return api_response(
                    404, "failure", {},
                    "NOT_FOUND",
                    "Product not enabled for this company."
                )

            company_module.enabled = False
            company_module.save(update_fields=["enabled", "last_updated_date"])

            # Update company products list
            if user.company.products:
                user.company.products = [
                    code for code in user.company.products
                    if code != company_module.module.code
                ]
                user.company.save(update_fields=["products", "last_updated_date"])

            return api_response(200, "success", {"message": "Product disabled"})

        except Exception as exc:
            return self._handle_exception(exc, "disable_module")

