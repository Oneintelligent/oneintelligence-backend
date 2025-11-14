from django.contrib import admin
from .models import SubscriptionPlan, Subscriptions


# ==========================
# SubscriptionPlan Admin
# ==========================
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "multiplier",
        "status",
        "has_trial",
        "trial_days",
        "global_discount_percentage",
        "created_date",
    )

    search_fields = ("name",)
    list_filter = ("status", "has_trial")

    readonly_fields = ("created_date", "last_updated_date")

    fieldsets = (
        ("Plan Details", {
            "fields": ("name", "multiplier", "status")
        }),
        ("Seat Pack Pricing", {
            "fields": ("base_prices",)
        }),
        ("Features", {
            "fields": ("features",)
        }),
        ("Trial", {
            "fields": ("has_trial", "trial_days")
        }),
        ("Discount", {
            "fields": ("global_discount_percentage",)
        }),
        ("System", {
            "fields": ("created_date", "last_updated_date")
        }),
    )


# ==========================
# Subscriptions Admin
# ==========================
@admin.register(Subscriptions)
class SubscriptionsAdmin(admin.ModelAdmin):
    list_display = (
        "subscriptionId",
        "plan",
        "companyId",
        "license_count",
        "final_total_price",
        "status",
        "is_trial",
        "created_date",
    )

    search_fields = ("subscriptionId", "companyId", "userId")
    list_filter = ("status", "is_trial")

    readonly_fields = (
        "applied_discount",
        "final_total_price",
    )

    fieldsets = (
        ("Subscription Info", {
            "fields": ("plan", "companyId", "userId", "license_count", "billing_type")
        }),
        ("Pricing", {
            "fields": ("applied_discount", "final_total_price"),
        }),
        ("Trial", {
            "fields": ("is_trial", "trial_text")
        }),
        ("Dates", {
            "fields": ("start_date", "end_date")
        }),
        ("Status", {
            "fields": ("status",)
        }),
        ("Metadata", {
            "fields": ("notes",)
        }),
        ("System", {
            "fields": ("created_date", "last_updated_date")
        }),
    )
