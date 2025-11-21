# Roles, Permissions, Access Control & Onboarding

**Complete Guide to OneIntelligence RBAC System and Onboarding Flow**

---

## Table of Contents

1. [Overview](#overview)
2. [Roles & Permissions System](#roles--permissions-system)
3. [Access Control](#access-control)
4. [Complete Onboarding Flow](#complete-onboarding-flow)
5. [API Reference](#api-reference)
6. [Implementation Guide](#implementation-guide)

---

## Overview

OneIntelligence uses a world-class Role-Based Access Control (RBAC) system following best practices from Atlassian, Freshworks, and Microsoft. The system provides:

- **Two-tier architecture**: Platform-level and Customer-level roles
- **Module-scoped permissions**: Granular control per workspace module
- **Role hierarchy**: Inherited permissions from parent roles
- **Special permissions**: `super_plan_access` for feature unlocking
- **Complete onboarding**: 10-step flow with annual-only billing

---

## Roles & Permissions System

### Two-Tier Architecture

#### 1. Platform-Level Roles (OneIntelligence Internal)

| Role | Code | Description | Hierarchy Level |
|------|------|-------------|-----------------|
| Platform Admin | `platform_admin` | Full platform access, manage all companies | 100 |
| Platform User | `platform_user` | Limited platform access | 50 |
| Platform Support | `platform_support` | Support staff access | 30 |

#### 2. Customer-Level Roles (Workspace)

| Role | Code | Description | Hierarchy Level |
|------|------|-------------|-----------------|
| Super Admin | `super_admin` | Company owner, full control | 90 |
| Admin | `admin` | Company administration | 70 |
| Member | `member` | Regular user | 10 |

**Note**: Super Admin automatically receives `super_plan_access` permission on workspace activation.

#### 3. Module-Specific Roles

Each workspace module has dedicated roles:

**AI Module:**
- `ai_manager` (80) - Full AI control
- `ai_user` (40) - Use AI features
- `ai_viewer` (10) - Read-only

**Sales Module:**
- `sales_manager` (80) - Full sales control
- `sales_rep` (50) - Manage deals
- `sales_user` (30) - Basic sales access
- `sales_viewer` (10) - Read-only

**Marketing Module:**
- `marketing_manager` (80) - Full marketing control
- `marketing_user` (40) - Create campaigns
- `marketing_viewer` (10) - Read-only

**Support Module:**
- `support_manager` (80) - Full support control
- `support_agent` (50) - Handle tickets
- `support_user` (30) - Create tickets
- `support_viewer` (10) - Read-only

**Projects Module:**
- `project_manager` (80) - Full project control
- `project_lead` (60) - Lead projects
- `project_member` (40) - Work on projects
- `project_viewer` (10) - Read-only

**Tasks Module:**
- `task_manager` (80) - Full task control
- `task_user` (40) - Manage tasks
- `task_viewer` (10) - Read-only

**Dashboard Module:**
- `dashboard_admin` (80) - Configure dashboards
- `dashboard_user` (40) - View dashboards
- `dashboard_viewer` (10) - Read-only

### Permissions

#### Permission Categories

**CRUD Operations:**
- `view` - View records
- `create` - Create records
- `update` - Update records
- `delete` - Delete records

**Advanced Operations:**
- `manage` - Full control (create, update, delete, assign)
- `assign` - Assign records to others
- `share` - Share records with others
- `export` - Export data
- `import` - Import data

**Administrative:**
- `configure` - Configure module settings
- `manage_users` - Add/remove users from module
- `manage_roles` - Assign roles to users
- `view_analytics` - View reports and analytics
- `manage_analytics` - Create/edit reports

**AI-Specific:**
- `ai_chat` - Use AI chat
- `ai_insights` - View AI insights
- `ai_configure` - Configure AI settings

**Special Permissions:**
- `super_plan_access` - Grants Pro/Ultra features WITHOUT additional charge
- `billing_admin` - Manage billing and subscriptions

### Role Hierarchy

Roles inherit permissions from parent roles:

```
Super Admin (90)
  └── Admin (70)
      └── Member (10)

Sales Manager (80)
  └── Sales Rep (50)
      └── Sales User (30)
          └── Sales Viewer (10)
```

**Inheritance Rules:**
- Child roles inherit all permissions from parent roles
- Higher hierarchy level = more permissions
- Inheritance is recursive (grandparent → parent → child)
- Module-specific inheritance is scoped to the module

### Special Permission: super_plan_access

**Capabilities:**
- Grants Pro and Ultra features WITHOUT additional charge
- Unlocks AI Recommendations, AI Insights, Conversational AI
- Overrides plan restrictions
- No billing impact

**Rules:**
- Only ONE user per company can have this permission
- Only Super Admin can assign/revoke
- Automatically assigned to Super Admin on workspace activation
- Can be reassigned to another user (revoke first)

**What It Does NOT Affect:**
- Billing cost (user gets features without being charged)
- Plan in database (subscription plan remains unchanged)
- User bucket usage (doesn't count against license limits)
- Workspace activation state
- FLAC for sensitive fields (still follows field-level access control)

---

## Access Control

### Visibility Levels

Records support visibility levels:

| Level | Code | Description |
|-------|------|-------------|
| Owner Only | `owner` | Only record owner can see |
| Team | `team` | Team members can see |
| Company | `company` | All company users can see |
| Shared | `shared` | Explicitly shared users can see |
| Public | `public` | Public (rare, for specific use cases) |

### Permission Checking

**Utility Functions:**

```python
from app.platform.rbac.utils import (
    has_permission,
    has_module_permission,
    has_role,
    can_view_record,
    can_edit_record,
    can_delete_record,
    is_super_admin,
    is_company_admin,
    get_user_permissions,
    get_user_roles,
)
from app.platform.rbac.constants import Permissions, Modules, CustomerRoles

# Check permission
if has_permission(user, Permissions.CREATE, company=company):
    # User can create records

# Check module permission
if has_module_permission(user, Modules.SALES, Permissions.VIEW, company=company):
    # User can view sales records

# Check role
if has_role(user, CustomerRoles.SUPER_ADMIN, company=company):
    # User is super admin

# Check record access
if can_view_record(user, record, module=Modules.SALES):
    # User can view this record

# Check if user has super_plan_access
user_permissions = get_user_permissions(user, company=company)
has_super_access = Permissions.SUPER_PLAN_ACCESS.value in user_permissions
```

**DRF Permission Classes:**

```python
from app.platform.rbac.permissions import (
    HasPermission,
    HasModulePermission,
    HasRole,
    CanViewRecord,
    CanEditRecord,
    CanDeleteRecord,
    IsSuperAdmin,
    IsCompanyAdmin,
)
from app.platform.rbac.constants import Permissions, Modules, CustomerRoles

class SalesViewSet(viewsets.ModelViewSet):
    permission_classes = [
        HasModulePermission(Modules.SALES, Permissions.VIEW),
    ]
    
    def get_permissions(self):
        if self.action == 'create':
            return [HasModulePermission(Modules.SALES, Permissions.CREATE)]
        elif self.action == 'destroy':
            return [HasModulePermission(Modules.SALES, Permissions.DELETE)]
        return super().get_permissions()
```

### Field-Level Access Control (FLAC)

FLAC allows Super Admin to configure field-level permissions:

- **View**: User can see the field
- **Edit**: User can edit the field
- **Hidden**: User cannot see the field

**Configuration:**
```json
{
  "sales": {
    "account_value": {
      "super_admin": "edit",
      "admin": "view",
      "member": "hidden"
    }
  }
}
```

**Note**: Users with `super_plan_access` still follow FLAC for sensitive fields.

---

## Complete Onboarding Flow

### Overview

10-step onboarding flow with annual-only billing, license buckets, and special permissions.

**Flow**: Signup → Company → Plan → License Bucket → Payment → Users → Special Permission → Modules → FLAC → Workspace Ready

### Pricing Model

#### Annual Plan Prices (Per User Per Year)

| Plan | Price (INR) | Description | Trial |
|------|-------------|-------------|-------|
| Pro | ₹9,999 | No AI | 90 days free, no credit card |
| Pro Max | ₹14,999 | AI Recommendations + AI Insights | 90 days free, no credit card |
| Ultra | ₹49,999 | Full Conversational AI | Coming Soon |

#### License Bucket Discounts

| Bucket | Discount |
|--------|----------|
| 1 user | 0% |
| 3 users | 10% |
| 5 users | 15% |
| 10 users | 20% |
| 20 users | 25% |
| 50 users | 30% |
| 100 users | 40% |
| 1000+ users | 50% |

**Pricing Formula:**
```
final_price = plan_price × users × (1 - discount_percent)
```

**Example:**
- Plan: Pro Max (₹14,999/user/year)
- Users: 10
- Discount: 20% (10-user bucket)
- Calculation: ₹14,999 × 10 × (1 - 0.20) = ₹119,992
- Savings: ₹29,998

### Step-by-Step Onboarding

#### STEP 1: User Signup

**Endpoint**: `POST /api/v1/users/signup/`

**Collects:**
- First name
- Last name
- Email
- Phone
- Password

**System Actions:**
- Create user with role: Super Admin
- Create temporary workspace (status: `pending_setup`)

#### STEP 2: Company Setup

**Endpoint**: `POST /api/v1/onboarding/complete/step2-company/`

**Collects:**
- Company name
- Industry
- Country
- Team size (optional)

**System Actions:**
- Link company → super admin
- Move workspace to `setup_in_progress`
- Assign Super Admin role via RBAC

**Request:**
```json
{
  "name": "Acme Corp",
  "industry": "Technology",
  "country": "India",
  "team_size": "50-100"
}
```

#### STEP 3: Select Annual Plan

**Endpoint**: `GET /api/v1/onboarding/complete/step3-plans/`

**Returns:**
- Available annual plans (Pro, Pro Max, Ultra)
- Plan features
- Pricing per user per year
- Trial information (90 days free for Pro/Pro Max)
- Plan status (Ultra is "coming_soon")

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "plans": [
      {
        "id": 1,
        "name": "Pro",
        "price_per_user_year": 9999,
        "description": "No AI",
        "has_trial": true,
        "trial_days": 90,
        "trial_requires_card": false,
        "status": "active",
        "recommended": false
      },
      {
        "id": 2,
        "name": "Pro Max",
        "price_per_user_year": 14999,
        "description": "AI Recommendations + AI Insights",
        "has_trial": true,
        "trial_days": 90,
        "trial_requires_card": false,
        "status": "active",
        "recommended": true
      },
      {
        "id": 3,
        "name": "Ultra",
        "price_per_user_year": 49999,
        "description": "Full Conversational AI",
        "has_trial": false,
        "status": "coming_soon",
        "recommended": false
      }
    ],
    "billing_type": "annual_only"
  }
}
```

#### STEP 4: Choose License Bucket

**Endpoint**: `POST /api/v1/onboarding/complete/step4-license-bucket/`

**Collects:**
- Plan name
- License count (must be one of: 1, 3, 5, 10, 20, 50, 100, 1000+)

**Returns:**
- Pricing breakdown with discounts
- Base price
- Discount percentage
- Discount amount
- Final price
- Savings message

**Request:**
```json
{
  "plan_name": "Pro Max",
  "license_count": 10
}
```

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "plan_name": "Pro Max",
    "license_count": 10,
    "pricing": {
      "base_price": 149990,
      "base_price_per_user": 14999,
      "discount_percent": 20,
      "discount_amount": 29998,
      "final_price": 119992,
      "savings": 29998,
      "formula": "₹14999 × 10 users × (1 - 20%) = ₹119992"
    }
  }
}
```

#### STEP 5: Review & Payment

**Endpoint**: `POST /api/v1/onboarding/complete/step5-payment/`

**Collects:**
- Plan ID (Pro or Pro Max only - Ultra is disabled)
- License count
- Payment data (optional for trial)

**System Actions:**
- Create subscription with 90-day free trial (Pro/Pro Max)
- No payment required for trial
- Activate workspace: `active`
- Assign Super Admin full access
- Assign `super_plan_access` permission to Super Admin automatically
- Enable plan features for workspace

**Request:**
```json
{
  "plan_id": 2,
  "license_count": 10,
  "is_trial": true
}
```

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "subscription": {
      "subscriptionId": "uuid",
      "plan": "Pro Max",
      "license_count": 10,
      "billing_type": "Yearly",
      "final_total_price": 0,
      "is_trial": true,
      "trial_days": 90,
      "trial_requires_card": false
    },
    "trial_info": {
      "is_trial": true,
      "trial_days": 90,
      "no_credit_card_required": true,
      "message": "90 days free trial - No credit card required"
    },
    "super_plan_access": "granted"
  }
}
```

#### STEP 6: Add Users

**Endpoint**: `POST /api/v1/onboarding/complete/step6-add-users/`

**Collects:**
- Users array (name, email, role, department, team)

**Rules:**
- Must respect purchased user bucket
- Status: `invited`
- Email invite sent

**Request:**
```json
{
  "users": [
    {
      "email": "user1@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "User"
    }
  ]
}
```

#### STEP 7: Assign Special Permission (Optional)

**Endpoint**: `POST /api/v1/onboarding/complete/step7-special-permission/`

**Collects:**
- User ID

**System Actions:**
- Assign `super_plan_access` permission to ONE user per company
- Grants Pro/Ultra features WITHOUT additional charge
- Only Super Admin can assign

**Request:**
```json
{
  "user_id": "uuid"
}
```

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "message": "super_plan_access granted (Pro/Ultra features without charge)",
    "user": {...},
    "note": "Only ONE user per company can have this permission"
  }
}
```

**Revoke Permission:**
**Endpoint**: `POST /api/v1/onboarding/complete/revoke-special-permission/`

#### STEP 8: Configure Modules

**Endpoint**: `POST /api/v1/onboarding/complete/step8-modules/`

**Collects:**
- Module codes array

**Available Modules:**
- `projects` - Project management
- `tasks` - Task management
- `sales` - CRM / Sales pipeline
- `accounts` - Account management
- `support` - Support tickets
- `marketing` - Marketing campaigns
- `dashboard` - Analytics dashboard

**System Actions:**
- Enable selected modules
- Modules reflect plan restrictions for normal users
- Full access for users with `super_plan_access`

**Request:**
```json
{
  "module_codes": ["projects", "tasks", "sales", "support"]
}
```

#### STEP 9: FLAC Configuration

**Endpoint**: `POST /api/v1/onboarding/complete/step9-flac/`

**Collects:**
- FLAC configuration (View/Edit/Hidden per role per module field)

**System Actions:**
- Store FLAC configuration
- Users with `super_plan_access` still follow FLAC for sensitive fields

**Request:**
```json
{
  "flac_config": {
    "sales": {
      "account_value": {
        "super_admin": "edit",
        "admin": "view",
        "member": "hidden"
      }
    }
  }
}
```

#### STEP 10: Workspace Ready

**Endpoint**: `GET /api/v1/onboarding/complete/step10-workspace-ready/`

**Returns:**
- Dashboard configuration based on plan
- Redirect URL
- Feature list

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "workspace_ready": true,
    "redirect_url": "/workspace/dashboard",
    "dashboard_config": {
      "plan": "Pro Max",
      "has_super_plan_access": true,
      "features": [
        "all_plan_features",
        "ai_recommendations",
        "ai_insights",
        "conversational_ai"
      ]
    }
  }
}
```

### Progress Tracking

**Endpoint**: `GET /api/v1/onboarding/complete/progress/`

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "current_step": 5,
    "total_steps": 10,
    "progress_percentage": 50
  }
}
```

---

## API Reference

### Onboarding APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/onboarding/complete/step2-company/` | POST | Company setup |
| `/api/v1/onboarding/complete/step3-plans/` | GET | Get annual plans |
| `/api/v1/onboarding/complete/step4-license-bucket/` | POST | Calculate pricing |
| `/api/v1/onboarding/complete/step5-payment/` | POST | Create subscription & activate |
| `/api/v1/onboarding/complete/step6-add-users/` | POST | Add team members |
| `/api/v1/onboarding/complete/step7-special-permission/` | POST | Assign super_plan_access |
| `/api/v1/onboarding/complete/revoke-special-permission/` | POST | Revoke super_plan_access |
| `/api/v1/onboarding/complete/step8-modules/` | POST | Enable modules |
| `/api/v1/onboarding/complete/step9-flac/` | POST | Configure FLAC |
| `/api/v1/onboarding/complete/step10-workspace-ready/` | GET | Get workspace config |
| `/api/v1/onboarding/complete/progress/` | GET | Get onboarding progress |

### Consent APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/consent/status/` | GET | Get consent status |
| `/api/v1/consent/all/` | GET | Get all consent records |
| `/api/v1/consent/update/` | POST | Grant/revoke consent |

---

## Implementation Guide

### Initialization

1. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Initialize RBAC:**
   ```bash
   python manage.py init_rbac
   ```

3. **Sync existing users (if any):**
   ```bash
   python manage.py sync_roles_to_rbac
   ```

### Assigning Roles

```python
from app.platform.rbac.helpers import (
    assign_role_to_user,
    assign_super_admin_role,
    assign_admin_role,
    assign_member_role,
    assign_module_role,
)

# Assign Super Admin (automatically done on company creation)
assign_super_admin_role(user, company, assigned_by=user)

# Assign Admin
assign_admin_role(user, company, assigned_by=super_admin)

# Assign Member
assign_member_role(user, company, assigned_by=admin)

# Assign module role
assign_module_role(
    user=user,
    role_code="sales_manager",
    company=company,
    module="sales",
    assigned_by=super_admin
)
```

### Checking Permissions in Views

```python
from app.platform.rbac.utils import has_permission, has_module_permission
from app.platform.rbac.constants import Permissions, Modules

def my_view(request):
    user = request.user
    company = user.company
    
    # Check permission
    if not has_permission(user, Permissions.CREATE, company=company):
        return api_response(403, "failure", {}, "PERMISSION_DENIED", "Cannot create")
    
    # Check module permission
    if not has_module_permission(user, Modules.SALES, Permissions.VIEW, company=company):
        return api_response(403, "failure", {}, "PERMISSION_DENIED", "Cannot view sales")
    
    # Proceed with operation
    ...
```

### Using DRF Permission Classes

```python
from rest_framework import viewsets
from app.platform.rbac.permissions import (
    HasModulePermission,
    CanViewRecord,
    CanEditRecord,
    IsSuperAdmin,
)
from app.platform.rbac.constants import Permissions, Modules

class SalesViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    
    def get_permissions(self):
        if self.action == 'list':
            return [HasModulePermission(Modules.SALES, Permissions.VIEW)]
        elif self.action == 'create':
            return [HasModulePermission(Modules.SALES, Permissions.CREATE)]
        elif self.action in ['update', 'partial_update']:
            return [CanEditRecord()]
        elif self.action == 'destroy':
            return [HasModulePermission(Modules.SALES, Permissions.DELETE)]
        return super().get_permissions()
    
    def get_queryset(self):
        # Filter based on user permissions and visibility
        from app.platform.rbac.utils import can_view_record
        queryset = super().get_queryset()
        return [r for r in queryset if can_view_record(self.request.user, r, module=Modules.SALES)]
```

### Checking super_plan_access

```python
from app.platform.rbac.utils import get_user_permissions
from app.platform.rbac.constants import Permissions

def check_plan_features(user, company):
    """Check if user has access to plan features"""
    user_permissions = get_user_permissions(user, company=company)
    has_super_access = Permissions.SUPER_PLAN_ACCESS.value in user_permissions
    
    if has_super_access:
        # User has Pro/Ultra features without charge
        return {
            "ai_recommendations": True,
            "ai_insights": True,
            "conversational_ai": True,
        }
    else:
        # Check subscription plan
        subscription = get_subscription(company)
        plan_name = subscription.plan.name if subscription else "Pro"
        
        if plan_name == "Ultra":
            return {
                "ai_recommendations": True,
                "ai_insights": True,
                "conversational_ai": True,
            }
        elif plan_name == "Pro Max":
            return {
                "ai_recommendations": True,
                "ai_insights": True,
                "conversational_ai": False,
            }
        else:  # Pro
            return {
                "ai_recommendations": False,
                "ai_insights": False,
                "conversational_ai": False,
            }
```

### Best Practices

1. **Always check permissions at the view level** using DRF permission classes
2. **Use module-scoped permissions** for workspace modules
3. **Respect visibility levels** when querying records
4. **Use role hierarchy** for permission escalation checks
5. **Cache permission checks** for performance in high-traffic endpoints
6. **Audit role assignments** using the assigned_by field
7. **Check super_plan_access** before enforcing plan restrictions
8. **Validate license limits** when adding users
9. **Enforce one-user-per-company** for super_plan_access
10. **Use transactions** for multi-step operations

### Security Considerations

- All permission checks are enforced at the database level
- Role assignments are company-scoped to prevent cross-company access
- Permission overrides can be time-limited
- System roles cannot be deleted or modified
- All role assignments are audited
- super_plan_access is limited to ONE user per company
- Ultra plan is disabled and cannot be purchased

### Performance

- Use `select_related` when querying UserRole
- Cache permission sets for frequently accessed users
- Use database indexes (already configured)
- Consider Redis caching for permission checks in high-traffic scenarios
- Batch permission checks when possible

---

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `PERMISSION_DENIED` | User doesn't have required permissions |
| `NO_COMPANY` | User not associated with company |
| `PLAN_UNAVAILABLE` | Plan is coming soon or disabled |
| `LICENSE_LIMIT_EXCEEDED` | Cannot add more users than license count |
| `CONSENT_REQUIRED` | Consent required for feature |
| `USER_NOT_FOUND` | Target user not found |
| `INVALID_USER` | User doesn't belong to same company |

---

## Migration Guide

### For Existing Users

1. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Initialize RBAC:
   ```bash
   python manage.py init_rbac
   ```

3. Sync existing users:
   ```bash
   python manage.py sync_roles_to_rbac
   ```

### For New Onboarding

1. Ensure RBAC is initialized
2. All new users automatically get RBAC roles during signup/onboarding
3. Super Admin automatically gets `super_plan_access` on workspace activation

---

## Summary

This document provides a complete guide to:

- **Roles**: Platform, Customer, and Module-specific roles
- **Permissions**: Granular permissions with inheritance
- **Access Control**: Visibility levels and permission checking
- **Onboarding**: Complete 10-step flow with annual-only billing
- **Special Permissions**: super_plan_access for feature unlocking
- **Implementation**: Code examples and best practices

The system is designed to be:
- **Scalable**: Database constraints and efficient queries
- **Secure**: Company-scoped permissions and audit trails
- **Flexible**: Role hierarchy and permission overrides
- **Compliant**: Consent management and GDPR support

