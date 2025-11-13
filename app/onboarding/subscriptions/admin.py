from django.contrib import admin
from .models import SubscriptionPlan, Subscriptions

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "monthly_price", "yearly_price", "global_discount_percentage")

@admin.register(Subscriptions)
class SubscriptionsAdmin(admin.ModelAdmin):
    list_display = ("subscriptionId", "plan", "license_count", "final_total_price", "status", "created_date")
    readonly_fields = ("base_price_per_license", "final_price_per_license", "final_total_price", "applied_discount")
