"""
RBAC Constants - Role and Permission Definitions
Following world-class standards from Atlassian, Freshworks, Microsoft
"""

from enum import Enum


class PlatformRoles(str, Enum):
    """OneIntelligence Platform-level roles"""
    PLATFORM_ADMIN = "platform_admin"
    PLATFORM_USER = "platform_user"
    PLATFORM_SUPPORT = "platform_support"


class CustomerRoles(str, Enum):
    """Customer workspace-level roles"""
    SUPER_ADMIN = "super_admin"  # Owner/Founder
    ADMIN = "admin"  # Company Admin
    MEMBER = "member"  # Regular user


class ModuleRoles(str, Enum):
    """Module-specific roles (workspace modules)"""
    # AI Module
    AI_MANAGER = "ai_manager"
    AI_USER = "ai_user"
    AI_VIEWER = "ai_viewer"
    
    # Sales Module
    SALES_MANAGER = "sales_manager"
    SALES_REP = "sales_rep"
    SALES_USER = "sales_user"
    SALES_VIEWER = "sales_viewer"
    
    # Marketing Module
    MARKETING_MANAGER = "marketing_manager"
    MARKETING_USER = "marketing_user"
    MARKETING_VIEWER = "marketing_viewer"
    
    # Support Module
    SUPPORT_MANAGER = "support_manager"
    SUPPORT_AGENT = "support_agent"
    SUPPORT_USER = "support_user"
    SUPPORT_VIEWER = "support_viewer"
    
    # Projects Module
    PROJECT_MANAGER = "project_manager"
    PROJECT_LEAD = "project_lead"
    PROJECT_MEMBER = "project_member"
    PROJECT_VIEWER = "project_viewer"
    
    # Tasks Module
    TASK_MANAGER = "task_manager"
    TASK_USER = "task_user"
    TASK_VIEWER = "task_viewer"
    
    # Dashboard Module
    DASHBOARD_ADMIN = "dashboard_admin"
    DASHBOARD_USER = "dashboard_user"
    DASHBOARD_VIEWER = "dashboard_viewer"


class Permissions(str, Enum):
    """Granular permissions"""
    # CRUD Operations
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    
    # Advanced Operations
    MANAGE = "manage"  # Full control (create, update, delete, assign)
    ASSIGN = "assign"  # Assign records to others
    SHARE = "share"  # Share records with others
    EXPORT = "export"  # Export data
    IMPORT = "import"  # Import data
    
    # Administrative
    CONFIGURE = "configure"  # Configure module settings
    MANAGE_USERS = "manage_users"  # Add/remove users from module
    MANAGE_ROLES = "manage_roles"  # Assign roles to users
    VIEW_ANALYTICS = "view_analytics"  # View reports and analytics
    MANAGE_ANALYTICS = "manage_analytics"  # Create/edit reports
    
    # AI-specific
    AI_CHAT = "ai_chat"  # Use AI chat
    AI_INSIGHTS = "ai_insights"  # View AI insights
    AI_CONFIGURE = "ai_configure"  # Configure AI settings
    
    # Special Permissions
    SUPER_PLAN_ACCESS = "super_plan_access"  # Grants all-plan access (Pro, Pro Max, Ultra features)
    BILLING_ADMIN = "billing_admin"  # Manage billing and subscriptions


class Modules(str, Enum):
    """Workspace products"""
    PROJECTS = "projects"
    TASKS = "tasks"
    SALES = "sales"
    CUSTOMERS = "customers"
    TICKETS = "tickets"
    MARKETING = "marketing"
    AI_CHAT = "ai_chat"
    AI_RECOMMENDATIONS = "ai_recommendations"
    DASHBOARD = "dashboard"
    ANALYTICS = "analytics"
    CONNECT = "connect"
    # Internal/System
    AI = "ai"
    SUPPORT = "support"
    TEAMS = "teams"
    COMPANIES = "companies"


class VisibilityLevels(str, Enum):
    """Record visibility levels"""
    OWNER = "owner"  # Only owner can see
    TEAM = "team"  # Team members can see
    COMPANY = "company"  # All company users can see
    SHARED = "shared"  # Explicitly shared users can see
    PUBLIC = "public"  # Public (rare, for specific use cases)


# Role Hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    # Platform
    PlatformRoles.PLATFORM_ADMIN: 100,
    PlatformRoles.PLATFORM_USER: 50,
    PlatformRoles.PLATFORM_SUPPORT: 30,
    
    # Customer
    CustomerRoles.SUPER_ADMIN: 90,
    CustomerRoles.ADMIN: 70,
    CustomerRoles.MEMBER: 10,
    
    # AI Module
    ModuleRoles.AI_MANAGER: 80,
    ModuleRoles.AI_USER: 40,
    ModuleRoles.AI_VIEWER: 10,
    
    # Sales Module
    ModuleRoles.SALES_MANAGER: 80,
    ModuleRoles.SALES_REP: 50,
    ModuleRoles.SALES_USER: 30,
    ModuleRoles.SALES_VIEWER: 10,
    
    # Marketing Module
    ModuleRoles.MARKETING_MANAGER: 80,
    ModuleRoles.MARKETING_USER: 40,
    ModuleRoles.MARKETING_VIEWER: 10,
    
    # Support Module
    ModuleRoles.SUPPORT_MANAGER: 80,
    ModuleRoles.SUPPORT_AGENT: 50,
    ModuleRoles.SUPPORT_USER: 30,
    ModuleRoles.SUPPORT_VIEWER: 10,
    
    # Projects Module
    ModuleRoles.PROJECT_MANAGER: 80,
    ModuleRoles.PROJECT_LEAD: 60,
    ModuleRoles.PROJECT_MEMBER: 40,
    ModuleRoles.PROJECT_VIEWER: 10,
    
    # Tasks Module
    ModuleRoles.TASK_MANAGER: 80,
    ModuleRoles.TASK_USER: 40,
    ModuleRoles.TASK_VIEWER: 10,
    
    # Dashboard Module
    ModuleRoles.DASHBOARD_ADMIN: 80,
    ModuleRoles.DASHBOARD_USER: 40,
    ModuleRoles.DASHBOARD_VIEWER: 10,
}


# Default Permission Sets for Each Role
ROLE_PERMISSIONS = {
    # Platform Roles
    PlatformRoles.PLATFORM_ADMIN: {
        Modules.AI: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE],
        Modules.SALES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE],
        Modules.MARKETING: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE],
        Modules.SUPPORT: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE],
        Modules.PROJECTS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE],
        Modules.TASKS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE],
        Modules.DASHBOARD: [Permissions.VIEW, Permissions.MANAGE_ANALYTICS, Permissions.CONFIGURE],
        Modules.COMPANIES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE],
    },
    
    # Customer Roles
    CustomerRoles.SUPER_ADMIN: {
        Modules.AI: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE, Permissions.AI_CHAT, Permissions.AI_INSIGHTS, Permissions.AI_CONFIGURE],
        Modules.SALES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.CONFIGURE, Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS],
        Modules.MARKETING: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.CONFIGURE, Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS],
        Modules.SUPPORT: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.CONFIGURE, Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS],
        Modules.PROJECTS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.CONFIGURE, Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS],
        Modules.TASKS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.CONFIGURE, Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS],
        Modules.DASHBOARD: [Permissions.VIEW, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS, Permissions.CONFIGURE],
        Modules.COMPANIES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.CONFIGURE, Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES],
    },
    
    CustomerRoles.ADMIN: {
        Modules.AI: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.AI_CHAT, Permissions.AI_INSIGHTS],
        Modules.SALES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
        Modules.MARKETING: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
        Modules.SUPPORT: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
        Modules.PROJECTS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
        Modules.TASKS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
        Modules.DASHBOARD: [Permissions.VIEW, Permissions.VIEW_ANALYTICS],
    },
    
    CustomerRoles.MEMBER: {
        Modules.AI: [Permissions.VIEW, Permissions.AI_CHAT],
        Modules.SALES: [Permissions.VIEW],
        Modules.MARKETING: [Permissions.VIEW],
        Modules.SUPPORT: [Permissions.VIEW],
        Modules.PROJECTS: [Permissions.VIEW],
        Modules.TASKS: [Permissions.VIEW],
        Modules.DASHBOARD: [Permissions.VIEW],
    },
    
    # AI Module Roles
    ModuleRoles.AI_MANAGER: {
        Modules.AI: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.AI_CHAT, Permissions.AI_INSIGHTS, Permissions.AI_CONFIGURE, Permissions.MANAGE_USERS],
    },
    ModuleRoles.AI_USER: {
        Modules.AI: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.AI_CHAT, Permissions.AI_INSIGHTS],
    },
    ModuleRoles.AI_VIEWER: {
        Modules.AI: [Permissions.VIEW],
    },
    
    # Sales Module Roles
    ModuleRoles.SALES_MANAGER: {
        Modules.SALES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS, Permissions.MANAGE_USERS],
    },
    ModuleRoles.SALES_REP: {
        Modules.SALES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
    },
    ModuleRoles.SALES_USER: {
        Modules.SALES: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.SHARE],
    },
    ModuleRoles.SALES_VIEWER: {
        Modules.SALES: [Permissions.VIEW],
    },
    
    # Marketing Module Roles
    ModuleRoles.MARKETING_MANAGER: {
        Modules.MARKETING: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS, Permissions.MANAGE_USERS],
    },
    ModuleRoles.MARKETING_USER: {
        Modules.MARKETING: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.SHARE, Permissions.VIEW_ANALYTICS],
    },
    ModuleRoles.MARKETING_VIEWER: {
        Modules.MARKETING: [Permissions.VIEW],
    },
    
    # Support Module Roles
    ModuleRoles.SUPPORT_MANAGER: {
        Modules.SUPPORT: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS, Permissions.MANAGE_USERS],
    },
    ModuleRoles.SUPPORT_AGENT: {
        Modules.SUPPORT: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
    },
    ModuleRoles.SUPPORT_USER: {
        Modules.SUPPORT: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.SHARE],
    },
    ModuleRoles.SUPPORT_VIEWER: {
        Modules.SUPPORT: [Permissions.VIEW],
    },
    
    # Projects Module Roles
    ModuleRoles.PROJECT_MANAGER: {
        Modules.PROJECTS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS, Permissions.MANAGE_USERS],
    },
    ModuleRoles.PROJECT_LEAD: {
        Modules.PROJECTS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.VIEW_ANALYTICS],
    },
    ModuleRoles.PROJECT_MEMBER: {
        Modules.PROJECTS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.SHARE],
    },
    ModuleRoles.PROJECT_VIEWER: {
        Modules.PROJECTS: [Permissions.VIEW],
    },
    
    # Tasks Module Roles
    ModuleRoles.TASK_MANAGER: {
        Modules.TASKS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.DELETE, Permissions.MANAGE, Permissions.ASSIGN, Permissions.SHARE, Permissions.EXPORT, Permissions.IMPORT, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS, Permissions.MANAGE_USERS],
    },
    ModuleRoles.TASK_USER: {
        Modules.TASKS: [Permissions.VIEW, Permissions.CREATE, Permissions.UPDATE, Permissions.SHARE],
    },
    ModuleRoles.TASK_VIEWER: {
        Modules.TASKS: [Permissions.VIEW],
    },
    
    # Dashboard Module Roles
    ModuleRoles.DASHBOARD_ADMIN: {
        Modules.DASHBOARD: [Permissions.VIEW, Permissions.VIEW_ANALYTICS, Permissions.MANAGE_ANALYTICS, Permissions.CONFIGURE],
    },
    ModuleRoles.DASHBOARD_USER: {
        Modules.DASHBOARD: [Permissions.VIEW, Permissions.VIEW_ANALYTICS],
    },
    ModuleRoles.DASHBOARD_VIEWER: {
        Modules.DASHBOARD: [Permissions.VIEW],
    },
}

