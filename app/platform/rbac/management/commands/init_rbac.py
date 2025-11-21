"""
Management command to initialize RBAC system with default roles and permissions.
Run: python manage.py init_rbac
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from app.platform.rbac.models import Role, Permission, RolePermission, ModulePermission, RoleInheritance
from app.platform.rbac.constants import (
    PlatformRoles,
    CustomerRoles,
    ModuleRoles,
    Permissions,
    Modules,
    ROLE_PERMISSIONS,
    ROLE_HIERARCHY,
)


class Command(BaseCommand):
    help = 'Initialize RBAC system with default roles and permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-initialization (will update existing roles)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('Initializing RBAC system...'))
        
        # Create Permissions
        self.stdout.write('Creating permissions...')
        permissions_map = {}
        for perm in Permissions:
            permission, created = Permission.objects.get_or_create(
                code=perm.value,
                defaults={
                    'name': perm.value,
                    'display_name': perm.value.replace('_', ' ').title(),
                    'description': f'Permission to {perm.value.replace("_", " ")}',
                    'category': self._get_permission_category(perm.value),
                    'is_system_permission': True,
                }
            )
            permissions_map[perm.value] = permission
            if created:
                self.stdout.write(f'  Created permission: {permission.display_name}')
            elif force:
                permission.display_name = perm.value.replace('_', ' ').title()
                permission.description = f'Permission to {perm.value.replace("_", " ")}'
                permission.category = self._get_permission_category(perm.value)
                permission.save()
                self.stdout.write(f'  Updated permission: {permission.display_name}')
        
        # Create Roles
        self.stdout.write('Creating roles...')
        roles_map = {}
        
        # Platform Roles
        platform_roles = [
            (PlatformRoles.PLATFORM_ADMIN, 'Platform Admin', 'OneIntelligence platform administrator with full access'),
            (PlatformRoles.PLATFORM_USER, 'Platform User', 'OneIntelligence platform user'),
            (PlatformRoles.PLATFORM_SUPPORT, 'Platform Support', 'OneIntelligence platform support staff'),
        ]
        
        for role_enum, display_name, description in platform_roles:
            role, created = Role.objects.get_or_create(
                code=role_enum.value,
                defaults={
                    'name': role_enum.value,
                    'display_name': display_name,
                    'description': description,
                    'role_type': 'platform',
                    'hierarchy_level': ROLE_HIERARCHY.get(role_enum, 0),
                    'is_system_role': True,
                    'is_active': True,
                }
            )
            roles_map[role_enum.value] = role
            if created:
                self.stdout.write(f'  Created role: {role.display_name}')
            elif force:
                role.display_name = display_name
                role.description = description
                role.hierarchy_level = ROLE_HIERARCHY.get(role_enum, 0)
                role.save()
                self.stdout.write(f'  Updated role: {role.display_name}')
        
        # Customer Roles
        customer_roles = [
            (CustomerRoles.SUPER_ADMIN, 'Super Admin', 'Company owner/founder with full control'),
            (CustomerRoles.ADMIN, 'Admin', 'Company administrator'),
            (CustomerRoles.MEMBER, 'Member', 'Regular company member'),
        ]
        
        for role_enum, display_name, description in customer_roles:
            role, created = Role.objects.get_or_create(
                code=role_enum.value,
                defaults={
                    'name': role_enum.value,
                    'display_name': display_name,
                    'description': description,
                    'role_type': 'customer',
                    'hierarchy_level': ROLE_HIERARCHY.get(role_enum, 0),
                    'is_system_role': True,
                    'is_active': True,
                }
            )
            roles_map[role_enum.value] = role
            if created:
                self.stdout.write(f'  Created role: {role.display_name}')
            elif force:
                role.display_name = display_name
                role.description = description
                role.hierarchy_level = ROLE_HIERARCHY.get(role_enum, 0)
                role.save()
                self.stdout.write(f'  Updated role: {role.display_name}')
        
        # Module Roles
        module_roles_config = {
            ModuleRoles.AI_MANAGER: ('AI Manager', 'AI module manager with full control', Modules.AI),
            ModuleRoles.AI_USER: ('AI User', 'AI module user', Modules.AI),
            ModuleRoles.AI_VIEWER: ('AI Viewer', 'AI module viewer (read-only)', Modules.AI),
            ModuleRoles.SALES_MANAGER: ('Sales Manager', 'Sales module manager', Modules.SALES),
            ModuleRoles.SALES_REP: ('Sales Rep', 'Sales representative', Modules.SALES),
            ModuleRoles.SALES_USER: ('Sales User', 'Sales module user', Modules.SALES),
            ModuleRoles.SALES_VIEWER: ('Sales Viewer', 'Sales module viewer (read-only)', Modules.SALES),
            ModuleRoles.MARKETING_MANAGER: ('Marketing Manager', 'Marketing module manager', Modules.MARKETING),
            ModuleRoles.MARKETING_USER: ('Marketing User', 'Marketing module user', Modules.MARKETING),
            ModuleRoles.MARKETING_VIEWER: ('Marketing Viewer', 'Marketing module viewer (read-only)', Modules.MARKETING),
            ModuleRoles.SUPPORT_MANAGER: ('Support Manager', 'Support module manager', Modules.SUPPORT),
            ModuleRoles.SUPPORT_AGENT: ('Support Agent', 'Support agent', Modules.SUPPORT),
            ModuleRoles.SUPPORT_USER: ('Support User', 'Support module user', Modules.SUPPORT),
            ModuleRoles.SUPPORT_VIEWER: ('Support Viewer', 'Support module viewer (read-only)', Modules.SUPPORT),
            ModuleRoles.PROJECT_MANAGER: ('Project Manager', 'Project module manager', Modules.PROJECTS),
            ModuleRoles.PROJECT_LEAD: ('Project Lead', 'Project lead', Modules.PROJECTS),
            ModuleRoles.PROJECT_MEMBER: ('Project Member', 'Project member', Modules.PROJECTS),
            ModuleRoles.PROJECT_VIEWER: ('Project Viewer', 'Project viewer (read-only)', Modules.PROJECTS),
            ModuleRoles.TASK_MANAGER: ('Task Manager', 'Task module manager', Modules.TASKS),
            ModuleRoles.TASK_USER: ('Task User', 'Task module user', Modules.TASKS),
            ModuleRoles.TASK_VIEWER: ('Task Viewer', 'Task viewer (read-only)', Modules.TASKS),
            ModuleRoles.DASHBOARD_ADMIN: ('Dashboard Admin', 'Dashboard administrator', Modules.DASHBOARD),
            ModuleRoles.DASHBOARD_USER: ('Dashboard User', 'Dashboard user', Modules.DASHBOARD),
            ModuleRoles.DASHBOARD_VIEWER: ('Dashboard Viewer', 'Dashboard viewer (read-only)', Modules.DASHBOARD),
        }
        
        for role_enum, (display_name, description, module) in module_roles_config.items():
            role, created = Role.objects.get_or_create(
                code=role_enum.value,
                defaults={
                    'name': role_enum.value,
                    'display_name': display_name,
                    'description': description,
                    'role_type': 'module',
                    'module': module.value,
                    'hierarchy_level': ROLE_HIERARCHY.get(role_enum, 0),
                    'is_system_role': True,
                    'is_active': True,
                }
            )
            roles_map[role_enum.value] = role
            if created:
                self.stdout.write(f'  Created role: {role.display_name}')
            elif force:
                role.display_name = display_name
                role.description = description
                role.hierarchy_level = ROLE_HIERARCHY.get(role_enum, 0)
                role.save()
                self.stdout.write(f'  Updated role: {role.display_name}')
        
        # Create Module Permissions
        self.stdout.write('Creating module permissions...')
        for module in Modules:
            for perm in Permissions:
                module_perm, created = ModulePermission.objects.get_or_create(
                    module=module.value,
                    permission=permissions_map[perm.value],
                    defaults={
                        'is_default': perm in [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE],
                    }
                )
                if created:
                    self.stdout.write(f'  Created module permission: {module.value} - {perm.value}')
        
        # Create Role Permissions
        self.stdout.write('Creating role permissions...')
        for role_code, module_perms in ROLE_PERMISSIONS.items():
            if role_code not in roles_map:
                continue
            
            role = roles_map[role_code]
            
            for module_code, perm_list in module_perms.items():
                for perm_code in perm_list:
                    perm_value = perm_code.value if isinstance(perm_code, Permissions) else perm_code
                    if perm_value not in permissions_map:
                        continue
                    
                    permission = permissions_map[perm_value]
                    
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                        module=module_code.value if isinstance(module_code, Modules) else module_code,
                        defaults={}
                    )
                    if created:
                        self.stdout.write(f'  Created role permission: {role.display_name} - {permission.display_name} ({module_code.value if isinstance(module_code, Modules) else module_code})')
        
        # Create Role Inheritance relationships
        self.stdout.write('Creating role inheritance relationships...')
        inheritance_count = 0
        
        # Module roles inherit from customer roles
        # Sales Rep inherits from Sales User
        inheritance_mappings = [
            # Sales module
            (ModuleRoles.SALES_REP, ModuleRoles.SALES_USER, Modules.SALES),
            (ModuleRoles.SALES_USER, ModuleRoles.SALES_VIEWER, Modules.SALES),
            (ModuleRoles.SALES_MANAGER, ModuleRoles.SALES_REP, Modules.SALES),
            
            # Marketing module
            (ModuleRoles.MARKETING_USER, ModuleRoles.MARKETING_VIEWER, Modules.MARKETING),
            (ModuleRoles.MARKETING_MANAGER, ModuleRoles.MARKETING_USER, Modules.MARKETING),
            
            # Support module
            (ModuleRoles.SUPPORT_AGENT, ModuleRoles.SUPPORT_USER, Modules.SUPPORT),
            (ModuleRoles.SUPPORT_USER, ModuleRoles.SUPPORT_VIEWER, Modules.SUPPORT),
            (ModuleRoles.SUPPORT_MANAGER, ModuleRoles.SUPPORT_AGENT, Modules.SUPPORT),
            
            # Projects module
            (ModuleRoles.PROJECT_LEAD, ModuleRoles.PROJECT_MEMBER, Modules.PROJECTS),
            (ModuleRoles.PROJECT_MEMBER, ModuleRoles.PROJECT_VIEWER, Modules.PROJECTS),
            (ModuleRoles.PROJECT_MANAGER, ModuleRoles.PROJECT_LEAD, Modules.PROJECTS),
            
            # Tasks module
            (ModuleRoles.TASK_USER, ModuleRoles.TASK_VIEWER, Modules.TASKS),
            (ModuleRoles.TASK_MANAGER, ModuleRoles.TASK_USER, Modules.TASKS),
            
            # AI module
            (ModuleRoles.AI_USER, ModuleRoles.AI_VIEWER, Modules.AI),
            (ModuleRoles.AI_MANAGER, ModuleRoles.AI_USER, Modules.AI),
            
            # Dashboard module
            (ModuleRoles.DASHBOARD_USER, ModuleRoles.DASHBOARD_VIEWER, Modules.DASHBOARD),
            (ModuleRoles.DASHBOARD_ADMIN, ModuleRoles.DASHBOARD_USER, Modules.DASHBOARD),
            
            # Customer roles
            (CustomerRoles.ADMIN, CustomerRoles.MEMBER, None),
            (CustomerRoles.SUPER_ADMIN, CustomerRoles.ADMIN, None),
        ]
        
        for child_code, parent_code, module_code in inheritance_mappings:
            if child_code not in roles_map or parent_code not in roles_map:
                continue
            
            child_role = roles_map[child_code]
            parent_role = roles_map[parent_code]
            
            inheritance, created = RoleInheritance.objects.get_or_create(
                child_role=child_role,
                parent_role=parent_role,
                module=module_code.value if module_code else None,
                defaults={}
            )
            
            if created:
                inheritance_count += 1
                module_str = f" ({module_code.value})" if module_code else ""
                self.stdout.write(f'  Created inheritance: {child_role.display_name} inherits from {parent_role.display_name}{module_str}')
        
        self.stdout.write(self.style.SUCCESS('\nRBAC system initialized successfully!'))
        self.stdout.write(f'  - Created {len(permissions_map)} permissions')
        self.stdout.write(f'  - Created {len(roles_map)} roles')
        self.stdout.write(f'  - Created role-permission mappings')
        self.stdout.write(f'  - Created {inheritance_count} role inheritance relationships')

    def _get_permission_category(self, perm_code: str) -> str:
        """Determine permission category based on code."""
        if perm_code in ['view', 'create', 'update', 'delete']:
            return 'crud'
        elif perm_code in ['manage', 'assign', 'share']:
            return 'operations'
        elif perm_code in ['configure', 'manage_users', 'manage_roles']:
            return 'admin'
        elif perm_code.startswith('ai_'):
            return 'ai'
        elif 'analytics' in perm_code:
            return 'analytics'
        else:
            return 'general'

