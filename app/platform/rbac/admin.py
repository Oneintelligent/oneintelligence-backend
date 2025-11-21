"""
Django Admin for RBAC models
"""

from django.contrib import admin
from .models import (
    Role,
    Permission,
    ModulePermission,
    RolePermission,
    UserRole,
    RoleInheritance,
    PermissionOverride,
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'code', 'role_type', 'module', 'hierarchy_level', 'is_active', 'is_system_role']
    list_filter = ['role_type', 'module', 'is_active', 'is_system_role']
    search_fields = ['name', 'code', 'display_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'display_name', 'description')
        }),
        ('Role Configuration', {
            'fields': ('role_type', 'module', 'hierarchy_level')
        }),
        ('Status', {
            'fields': ('is_active', 'is_system_role')
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'code', 'category', 'is_system_permission']
    list_filter = ['category', 'is_system_permission']
    search_fields = ['name', 'code', 'display_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ['module', 'permission', 'is_default']
    list_filter = ['module', 'is_default']
    search_fields = ['module', 'permission__name', 'permission__code']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission', 'module']
    list_filter = ['role', 'module', 'permission__category']
    search_fields = ['role__name', 'permission__name', 'module']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'company', 'module', 'is_active', 'assigned_at', 'expires_at']
    list_filter = ['is_active', 'role', 'module', 'company']
    search_fields = ['user__email', 'role__name', 'company__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'assigned_at']
    date_hierarchy = 'assigned_at'


@admin.register(RoleInheritance)
class RoleInheritanceAdmin(admin.ModelAdmin):
    list_display = ['child_role', 'parent_role', 'module']
    list_filter = ['module']
    search_fields = ['child_role__name', 'parent_role__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PermissionOverride)
class PermissionOverrideAdmin(admin.ModelAdmin):
    list_display = ['override_type', 'user', 'team', 'company', 'permission', 'module', 'action', 'is_active', 'expires_at']
    list_filter = ['override_type', 'action', 'module', 'is_active']
    search_fields = ['user__email', 'team__name', 'company__name', 'permission__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'expires_at'

