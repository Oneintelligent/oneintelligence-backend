# Module Access Validation - Implementation Summary

**Date:** 2024  
**Status:** ✅ **COMPLETED**

---

## Overview

The workspace module access control now validates access at **three levels** to ensure proper security and access control:

1. **Company-Level Module Access** - Module must be enabled for the company
2. **Role-Based Access** - User must have appropriate roles for the module
3. **Permission-Based Access** - User must have specific permissions for the action

---

## Three-Level Validation

### Level 1: Company Module Enabled ✅
**Check:** `CompanyModule.enabled = True` for the company

**Purpose:** Ensures the module is enabled at the company level before any user can access it.

**Implementation:**
- Checks `CompanyModule` model for `enabled=True` and `is_active=True`
- Validates that `ModuleDefinition` exists and is active
- Returns `False` if module is not enabled for the company

**Example:**
```python
from app.platform.rbac.utils import is_module_enabled_for_company

# Check if Sales module is enabled for company
enabled = is_module_enabled_for_company(Modules.SALES, company)
```

### Level 2: User Roles ✅
**Check:** User has appropriate roles assigned for the module

**Purpose:** Validates that the user has been assigned roles that grant access to the module.

**Implementation:**
- Checks `UserRole` model for active roles
- Validates role is scoped to the company and module
- Checks role hierarchy and inheritance

**Example:**
```python
from app.platform.rbac.utils import has_role, get_user_roles

# Check if user has sales_manager role
has_sales_role = has_role(user, ModuleRoles.SALES_MANAGER, company=company, module=Modules.SALES)

# Get all user roles for a module
roles = get_user_roles(user, company=company, module=Modules.SALES)
```

### Level 3: User Permissions ✅
**Check:** User has specific permissions for the action (view, create, update, delete, etc.)

**Purpose:** Validates that the user has the specific permission needed for the action they're trying to perform.

**Implementation:**
- Checks permissions from user roles (with inheritance)
- Applies permission overrides (grants/denials)
- Validates permission is scoped to the module

**Example:**
```python
from app.platform.rbac.utils import has_permission, has_module_permission

# Check if user has VIEW permission for Sales module
can_view = has_module_permission(user, Modules.SALES, Permissions.VIEW, company=company)
```

---

## Comprehensive Validation Function

### `validate_module_access()`

A comprehensive function that checks all three levels and returns detailed results:

```python
from app.platform.rbac.utils import validate_module_access
from app.platform.rbac.constants import Modules, Permissions

# Validate access with detailed results
result = validate_module_access(
    user=user,
    module=Modules.SALES,
    permission=Permissions.VIEW,
    company=company
)

# Result structure:
{
    'has_access': True/False,        # Overall access granted
    'module_enabled': True/False,     # Level 1: Module enabled for company
    'has_permission': True/False,     # Level 3: User has permission
    'has_role': True/False,           # Level 2: User has role
    'reason': str                     # Reason for denial (if has_access is False)
}
```

### `has_module_permission()` - Enhanced ✅

The `has_module_permission()` function now automatically validates all three levels:

```python
from app.platform.rbac.utils import has_module_permission
from app.platform.rbac.constants import Modules, Permissions

# This now checks:
# 1. Module enabled for company
# 2. User has role
# 3. User has permission
can_access = has_module_permission(
    user=user,
    module=Modules.SALES,
    permission=Permissions.VIEW,
    company=company
)
```

**What it checks:**
1. ✅ Module is enabled for the company (`CompanyModule.enabled = True`)
2. ✅ User has appropriate roles for the module
3. ✅ User has the specific permission for the action

**Returns:** `True` only if ALL three levels pass

---

## Integration Points

### 1. DRF Permission Classes ✅

All DRF permission classes automatically use the enhanced validation:

```python
from app.platform.rbac.permissions import HasModulePermission
from app.platform.rbac.constants import Modules, Permissions

class SalesViewSet(viewsets.ModelViewSet):
    permission_classes = [
        HasModulePermission(Modules.SALES, Permissions.VIEW)
    ]
    # Automatically validates all three levels
```

**Permission Classes:**
- `HasModulePermission` - Validates module access with permission
- `HasPermission` - Validates permission (with optional module)
- `CanViewRecord` - Validates record-level view access
- `CanEditRecord` - Validates record-level edit access
- `CanDeleteRecord` - Validates record-level delete access
- `CanManageRecord` - Validates record-level manage access

### 2. RBAC Utility Functions ✅

All utility functions now include company module validation:

```python
# These functions now check module enabled status:
has_module_permission(user, module, permission, company)
can_view_record(user, record, module=module)
can_edit_record(user, record, module=module)
can_delete_record(user, record, module=module)
can_manage_record(user, record, module=module)
```

### 3. Workspace Module Views ✅

Workspace module views automatically benefit from the validation:

**Sales Module:**
- `app/workspace/sales/views.py` - Uses `has_module_permission()`
- `app/workspace/sales/permissions.py` - Uses `HasModulePermission`

**Projects Module:**
- `app/workspace/projects/permissions.py` - Uses `has_module_permission()`

**Tasks Module:**
- `app/workspace/tasks/permissions.py` - Uses `has_module_permission()`

**Support Module:**
- `app/workspace/support/permissions.py` - Uses `has_module_permission()`

---

## Validation Flow

```
User Request → has_module_permission()
    │
    ├─→ Level 1: is_module_enabled_for_company()
    │   └─→ Check CompanyModule.enabled = True
    │       └─→ ❌ Deny if module not enabled
    │
    ├─→ Level 2: get_user_roles()
    │   └─→ Check UserRole for module
    │       └─→ Check role hierarchy/inheritance
    │
    └─→ Level 3: has_permission()
        └─→ Check RolePermission for permission
            └─→ Apply PermissionOverride (grants/denials)
                └─→ ✅ Grant if all checks pass
```

---

## Usage Examples

### Example 1: Basic Permission Check

```python
from app.platform.rbac.utils import has_module_permission
from app.platform.rbac.constants import Modules, Permissions

def my_view(request):
    user = request.user
    company = user.company
    
    # Check if user can view Sales module
    if not has_module_permission(user, Modules.SALES, Permissions.VIEW, company=company):
        return Response({"error": "Access denied"}, status=403)
    
    # User has access - proceed
    ...
```

### Example 2: Detailed Validation

```python
from app.platform.rbac.utils import validate_module_access
from app.platform.rbac.constants import Modules, Permissions

def my_view(request):
    user = request.user
    company = user.company
    
    # Get detailed validation results
    validation = validate_module_access(
        user=user,
        module=Modules.SALES,
        permission=Permissions.CREATE,
        company=company
    )
    
    if not validation['has_access']:
        return Response({
            "error": "Access denied",
            "reason": validation['reason'],
            "details": {
                "module_enabled": validation['module_enabled'],
                "has_role": validation['has_role'],
                "has_permission": validation['has_permission']
            }
        }, status=403)
    
    # User has access - proceed
    ...
```

### Example 3: DRF ViewSet

```python
from rest_framework import viewsets
from app.platform.rbac.permissions import HasModulePermission
from app.platform.rbac.constants import Modules, Permissions

class SalesViewSet(viewsets.ModelViewSet):
    permission_classes = [
        HasModulePermission(Modules.SALES, Permissions.VIEW)
    ]
    
    # All actions automatically validate:
    # 1. Sales module enabled for company
    # 2. User has Sales role
    # 3. User has VIEW permission
    ...
```

---

## Testing Scenarios

### Scenario 1: Module Not Enabled
- **Setup:** Company has Sales module disabled
- **User:** Has `sales_manager` role and `view` permission
- **Expected:** ❌ Access denied - "Module 'sales' is not enabled for company"

### Scenario 2: User Has No Role
- **Setup:** Company has Sales module enabled
- **User:** No Sales-related roles assigned
- **Expected:** ❌ Access denied - "User does not have 'view' permission for module 'sales'"

### Scenario 3: User Has Role But No Permission
- **Setup:** Company has Sales module enabled, user has `sales_viewer` role
- **User:** Role doesn't grant `create` permission
- **Expected:** ❌ Access denied - "User does not have 'create' permission for module 'sales'"

### Scenario 4: All Checks Pass
- **Setup:** Company has Sales module enabled
- **User:** Has `sales_manager` role with `view` permission
- **Expected:** ✅ Access granted

### Scenario 5: Platform Admin
- **Setup:** Any configuration
- **User:** Platform admin
- **Expected:** ✅ Access granted (bypasses all checks)

---

## Benefits

1. **Security:** Three-layer validation ensures proper access control - **no bypasses**
2. **Consistency:** All module access uses the same validation logic - **enforced everywhere**
3. **Transparency:** Detailed validation results show why access was denied
4. **Maintainability:** Centralized validation logic in one place
5. **Enforcement:** All access paths validate all three levels - **no exceptions**

---

## Enforcement

### All Access Paths Enforce Validation
**All** permission checking functions now enforce the three-level validation when a module is provided:

- ✅ `has_module_permission()` - Always validates all three levels
- ✅ `has_permission()` - Validates all three levels when module is provided
- ✅ `can_view_record()` - Validates module access when module is provided
- ✅ `can_edit_record()` - Validates module access when module is provided
- ✅ `can_delete_record()` - Validates module access when module is provided
- ✅ `can_manage_record()` - Validates module access when module is provided

**Important:** When working with workspace modules, **always** provide the `module` parameter to ensure proper validation.

### New Code Pattern
When adding new workspace modules, use the standard pattern:

```python
from app.platform.rbac.utils import has_module_permission
from app.platform.rbac.constants import Modules, Permissions

# In views - ALWAYS provide module parameter
if not has_module_permission(user, Modules.MY_MODULE, Permissions.VIEW, company=company):
    return Response({"error": "Access denied"}, status=403)
```

---

## Files Modified

1. **`app/platform/rbac/utils.py`**
   - Added `is_module_enabled_for_company()` function
   - Enhanced `has_module_permission()` to **always** check all three levels
   - Enhanced `has_permission()` to check module enabled when module is provided
   - Enhanced `can_view_record()` to validate module access when module is provided
   - Enhanced `can_edit_record()` to validate module access when module is provided
   - Enhanced `can_delete_record()` to validate module access when module is provided
   - Enhanced `can_manage_record()` to validate module access when module is provided
   - Added `validate_module_access()` comprehensive validation function
   - Added logging for access denials

2. **Enforced Integration**
   - All DRF permission classes **automatically** use enhanced validation
   - All workspace module views **automatically** benefit
   - **All** access paths now enforce three-level validation
   - **No bypasses** - module access is strictly validated

---

## Next Steps

1. ✅ **Completed:** Three-level validation implemented
2. ⚠️ **Recommended:** Add unit tests for validation scenarios
3. ⚠️ **Recommended:** Add integration tests for workspace modules
4. ⚠️ **Optional:** Add monitoring/logging for access denials

---

## Summary

The module access validation **strictly enforces** that workspace modules are only accessible when:

1. ✅ **Company has the module enabled** (`CompanyModule.enabled = True`) - **Level 1**
2. ✅ **User has appropriate roles** (Role-based access) - **Level 2**
3. ✅ **User has required permissions** (Permission-based access) - **Level 3**

**All three levels MUST pass for access to be granted.** There are **no bypasses** or exceptions (except Platform Admins).

### Enforcement Points

✅ **All permission functions enforce validation:**
- `has_module_permission()` - **Always** validates all three levels
- `has_permission()` - Validates all three levels when `module` parameter is provided
- `can_view_record()` - Validates module access when `module` parameter is provided
- `can_edit_record()` - Validates module access when `module` parameter is provided
- `can_delete_record()` - Validates module access when `module` parameter is provided
- `can_manage_record()` - Validates module access when `module` parameter is provided

✅ **All DRF permission classes enforce validation:**
- `HasModulePermission` - Validates all three levels
- `HasPermission` - Validates all three levels when module is provided
- `CanViewRecord` - Validates module access when module is provided
- `CanEditRecord` - Validates module access when module is provided
- `CanDeleteRecord` - Validates module access when module is provided
- `CanManageRecord` - Validates module access when module is provided

**This provides enterprise-grade security and access control for workspace modules with no bypasses.**

---

**Last Updated:** 2024  
**Status:** ✅ Validation Implemented, Enforced, and Integrated - **No Backward Compatibility**

