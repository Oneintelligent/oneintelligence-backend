"""
Default workspace product definitions used across onboarding and product APIs.
"""

from typing import List, Dict

from .models import ModuleDefinition

DEFAULT_WORKSPACE_MODULES: List[Dict] = [
    {
        "code": "projects",
        "name": "Projects",
        "category": "workspace",
        "description": "Plan, execute, and track cross-functional initiatives with tasks, milestones, and owners.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "tasks",
        "name": "Tasks",
        "category": "workspace",
        "description": "Manage daily workflows, track progress, and organize work efficiently.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "sales",
        "name": "Sales",
        "category": "workspace",
        "description": "Manage pipeline, accounts, and deals with AI nudges and automated hand-offs.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "customers",
        "name": "Customers",
        "category": "workspace",
        "description": "Central customer 360 with health, revenue, contracts, and renewal intelligence.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "tickets",
        "name": "Tickets",
        "category": "workspace",
        "description": "Unified support desk for issues, SLAs, escalations, and linked projects/tasks.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "marketing",
        "name": "Marketing",
        "category": "workspace",
        "description": "Campaign planning, automation journeys, and attribution dashboards.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "ai_chat",
        "name": "OneIntelligent AI Chat",
        "category": "ai",
        "description": "Talk to get whatever you want to grow - conversational copilot for every workspace action, insight, and workflow.",
        "plans": ["Pro Max", "Ultra"],
        "metadata": {"ai": True},
    },
    {
        "code": "ai_recommendations",
        "name": "OneIntelligent AI Recommendations",
        "category": "ai",
        "description": "Give recommendations across all products to grow - account, deal, and project recommendations powered by graph + telemetry.",
        "plans": ["Pro Max", "Ultra"],
        "metadata": {"ai": True},
    },
    {
        "code": "dashboard",
        "name": "Dashboard",
        "category": "workspace",
        "description": "Central overview of all workspace activities, metrics, and insights.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "analytics",
        "name": "Analytics",
        "category": "workspace",
        "description": "Executive dashboards, board-ready reporting, and product-level insights.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
    {
        "code": "connect",
        "name": "Connect",
        "category": "workspace",
        "description": "Internal user chat like MS Teams - context-aware collaboration across projects, tickets, and docs.",
        "plans": ["Pro", "Pro Max", "Ultra"],
    },
]


def ensure_default_module_definitions() -> None:
    """
    Make sure the core workspace products exist so onboarding and product APIs
    always have something to return, even on fresh environments.
    Updates existing records to ensure they match current definitions.
    Also handles migration of old product codes to new ones.
    """
    
    # Map old codes to new codes for migration
    CODE_MIGRATIONS = {
        "accounts": "customers",  # Old "accounts" -> new "customers"
        "chat": "connect",  # Old "chat" -> new "connect"
    }
    
    # First, migrate old product codes to new ones
    for old_code, new_code in CODE_MIGRATIONS.items():
        try:
            old_product = ModuleDefinition.objects.filter(code=old_code).first()
            if old_product:
                # Check if new product already exists
                new_product = ModuleDefinition.objects.filter(code=new_code).first()
                if new_product:
                    # If new product exists, delete old one (data should be migrated)
                    old_product.delete()
                else:
                    # Update old product to new code
                    old_product.code = new_code
                    old_product.save()
        except Exception:
            pass  # Continue if migration fails
    
    # Now ensure all current products exist and are up to date
    for module in DEFAULT_WORKSPACE_MODULES:
        product, created = ModuleDefinition.objects.get_or_create(
            code=module["code"],
            defaults={
                "name": module["name"],
                "category": module.get("category", "workspace"),
                "description": module.get("description", ""),
                "plans": module.get("plans", ["Pro", "Pro Max", "Ultra"]),
                "metadata": module.get("metadata", {}),
            },
        )
        
        # Update existing records to ensure they match current definitions
        if not created:
            product.name = module["name"]
            product.category = module.get("category", "workspace")
            product.description = module.get("description", "")
            product.plans = module.get("plans", ["Pro", "Pro Max", "Ultra"])
            if "metadata" in module:
                product.metadata = module.get("metadata", {})
            product.save()

