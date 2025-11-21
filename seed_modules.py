#!/usr/bin/env python3
"""
Seed initial product definitions for the platform
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from app.platform.products.models import ModuleDefinition

PRODUCTS = [
    {
        "code": "projects",
        "name": "Projects",
        "category": "workspace",
        "description": "Plan, execute, and track cross-functional initiatives with tasks, milestones, and owners.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "tasks",
        "name": "Tasks",
        "category": "workspace",
        "description": "Manage daily workflows, track progress, and organize work efficiently.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "sales",
        "name": "Sales",
        "category": "workspace",
        "description": "Manage pipeline, accounts, and deals with AI nudges and automated hand-offs.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "customers",
        "name": "Customers",
        "category": "workspace",
        "description": "Central customer 360 with health, revenue, contracts, and renewal intelligence.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "tickets",
        "name": "Tickets",
        "category": "workspace",
        "description": "Unified support desk for issues, SLAs, escalations, and linked projects/tasks.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "marketing",
        "name": "Marketing",
        "category": "workspace",
        "description": "Campaign planning, automation journeys, and attribution dashboards.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "ai_chat",
        "name": "OneIntelligent AI Chat",
        "category": "ai",
        "description": "Talk to get whatever you want to grow - conversational copilot for every workspace action, insight, and workflow.",
        "plans": ["Pro Max", "Ultra"],
        "metadata": {"ai": True}
    },
    {
        "code": "ai_recommendations",
        "name": "OneIntelligent AI Recommendations",
        "category": "ai",
        "description": "Give recommendations across all products to grow - account, deal, and project recommendations powered by graph + telemetry.",
        "plans": ["Pro Max", "Ultra"],
        "metadata": {"ai": True}
    },
    {
        "code": "dashboard",
        "name": "Dashboard",
        "category": "workspace",
        "description": "Central overview of all workspace activities, metrics, and insights.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "analytics",
        "name": "Analytics",
        "category": "workspace",
        "description": "Executive dashboards, board-ready reporting, and product-level insights.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
    {
        "code": "connect",
        "name": "Connect",
        "category": "workspace",
        "description": "Internal user chat like MS Teams - context-aware collaboration across projects, tickets, and docs.",
        "plans": ["Pro", "Pro Max", "Ultra"]
    },
]

def seed_products():
    """Create product definitions if they don't exist"""
    created = 0
    updated = 0
    
    for product_data in PRODUCTS:
        product, created_flag = ModuleDefinition.objects.get_or_create(
            code=product_data["code"],
            defaults={
                "name": product_data["name"],
                "category": product_data["category"],
                "description": product_data["description"],
                "plans": product_data["plans"],
                "metadata": product_data.get("metadata", {})
            }
        )
        
        if created_flag:
            created += 1
            print(f"✓ Created product: {product.name} ({product.code})")
        else:
            # Update if exists
            product.name = product_data["name"]
            product.category = product_data["category"]
            product.description = product_data["description"]
            product.plans = product_data["plans"]
            if "metadata" in product_data:
                product.metadata = product_data["metadata"]
            product.save()
            updated += 1
            print(f"↻ Updated product: {product.name} ({product.code})")
    
    print(f"\nSummary: {created} created, {updated} updated")
    return created + updated

if __name__ == "__main__":
    print("Seeding product definitions...")
    seed_products()
    print("Done!")

