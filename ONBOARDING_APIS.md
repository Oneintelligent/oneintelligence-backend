# Onboarding APIs Documentation

This document outlines all the onboarding APIs for the OneIntelligence MVP, following the flow:
**Signup → Company → Plan → Modules → Team Members**

## API Base URLs

- **Onboarding**: `/api/v1/onboarding/`
- **Users**: `/api/v1/users/`
- **Companies**: `/api/v1/companies/`
- **Subscriptions**: `/api/v1/subscriptions/`
- **Modules**: `/api/v1/modules/`

---

## 1. Signup API

### POST `/api/v1/users/signup/`
**Description**: Register a new user (Super Admin / Company Owner)

**Request Body**:
```json
{
  "email": "owner@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "role": "SuperAdmin",
  "companyId": null  // Optional, if joining existing company
}
```

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "user": { ... },
    "access": "jwt_token_here"
  }
}
```

**Features**:
- Email verification token sent automatically
- Password strength validation
- JWT tokens returned (access + refresh cookie)

---

## 2. Company Creation API

### POST `/api/v1/companies/create/`
**Description**: Create a new company (must be authenticated, cannot already belong to a company)

**Request Body**:
```json
{
  "name": "Acme Corp",
  "email": "contact@acme.com",
  "phone": "+1234567890",
  "address": "123 Main St",
  "country": "USA",
  "industry": "Technology",
  "company_size": "50-100"
}
```

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "companyId": "uuid",
    "name": "Acme Corp",
    "lifecycle_status": "onboarding",
    ...
  }
}
```

**Features**:
- Automatically sets `lifecycle_status` to `"onboarding"`
- Links creator to company
- Updates user status to ACTIVE

### GET `/api/v1/companies/{companyId}/detail/`
**Description**: Get company details

### PUT `/api/v1/companies/{companyId}/update/`
**Description**: Update company details

---

## 3. Plan Selection API

### GET `/api/v1/subscriptions/plans/`
**Description**: List all available subscription plans (public endpoint)

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Pro",
      "base_prices": {"1": 999, "3": 1999, "5": 2999},
      "multiplier": 1.0,
      "features": [...],
      "has_trial": true,
      "trial_days": 90
    }
  ]
}
```

### POST `/api/v1/subscriptions/`
**Description**: Create subscription for company (auto-sets companyId/userId from authenticated user)

**Request Body**:
```json
{
  "plan": 1,  // Plan ID
  "billing_type": "Monthly",  // or "Yearly"
  "license_count": 5,  // Number of seats
  "is_trial": false
}
```

**Response**:
```json
{
  "statusCode": 201,
  "status": "success",
  "data": {
    "subscriptionId": "uuid",
    "plan_name": "Pro",
    "license_count": 5,
    "final_total_price": 2999,
    "seats_used": 1,
    "seats_available": 4,
    ...
  }
}
```

**Features**:
- Auto-sets `companyId` and `userId` from authenticated user
- Updates company `lifecycle_status` to `"trial"` or `"active"`
- Calculates pricing with discounts
- Handles seat pack pricing

### GET `/api/v1/subscriptions/company/`
**Description**: Get subscription for current user's company (includes seat usage)

### GET `/api/v1/subscriptions/my/`
**Description**: Get subscription for logged-in user's company

### PUT `/api/v1/subscriptions/{subscriptionId}/update/`
**Description**: Update subscription (plan change, seat count change)

---

## 4. Module Selection API

### GET `/api/v1/modules/definitions/`
**Description**: List all available modules (public endpoint)

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": [
    {
      "id": 1,
      "code": "sales",
      "name": "Sales CRM",
      "category": "workspace",
      "description": "...",
      "plans": ["pro", "maxpro", "ultra"]
    }
  ]
}
```

### GET `/api/v1/modules/company/company/`
**Description**: Get enabled modules for current user's company

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "modules": [...],
    "count": 3
  }
}
```

### POST `/api/v1/modules/company/enable/`
**Description**: Enable modules for company

**Request Body**:
```json
{
  "module_codes": ["sales", "projects", "support"]
}
```

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "modules": [...],
    "count": 3
  }
}
```

**Features**:
- Updates company `products` JSON field
- Creates `CompanyModule` records

### POST `/api/v1/modules/company/{moduleId}/disable/`
**Description**: Disable a module for company

---

## 5. Team Member Invitation API

### POST `/api/v1/users/invite/`
**Description**: Invite a user to the company (with seat limit enforcement)

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "User"
}
```

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "user": { ... },
    "invite_token": "uuid",
    "seat_info": {
      "seats_used": 2,
      "seats_available": 3,
      "seats_total": 5
    }
  }
}
```

**Features**:
- **Seat limit enforcement**: Checks active + pending users against subscription `license_count`
- Returns error if limit reached: `SEAT_LIMIT_REACHED`
- Sends invite email with set-password link
- Returns seat usage information

**Error Response** (if seat limit reached):
```json
{
  "statusCode": 403,
  "status": "failure",
  "data": {},
  "errorCode": "SEAT_LIMIT_REACHED",
  "errorMessage": "Seat limit reached (5 seats). Please upgrade your plan to invite more users."
}
```

### POST `/api/v1/users/accept-invite/`
**Description**: Accept invite and set password

**Request Body**:
```json
{
  "token": "uuid",
  "password": "SecurePass123!"
}
```

---

## 6. Onboarding Status API

### GET `/api/v1/onboarding/status/`
**Description**: Get comprehensive onboarding status and progress

**Response**:
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "progress": {
      "percentage": 80,
      "steps_completed": 4,
      "total_steps": 5,
      "next_step": "team"
    },
    "steps": {
      "signup": {
        "completed": true,
        "user_id": "uuid",
        "email": "owner@example.com",
        "email_verified": true
      },
      "company": {
        "completed": true,
        "company_id": "uuid",
        "company_name": "Acme Corp",
        "lifecycle_status": "onboarding"
      },
      "plan": {
        "completed": true,
        "subscription_id": "uuid",
        "plan_name": "Pro",
        "license_count": 5,
        "seats_used": 1,
        "seats_available": 4
      },
      "modules": {
        "completed": true,
        "enabled_modules": ["sales", "projects"],
        "count": 2
      },
      "team": {
        "completed": false,
        "total_members": 1,
        "members": [...]
      }
    },
    "can_proceed_to_activation": true
  }
}
```

**Features**:
- Tracks completion of all 5 steps
- Calculates overall progress percentage
- Identifies next step
- Returns seat usage information
- Indicates if ready for activation

---

## Complete Onboarding Flow

1. **Signup** → `POST /api/v1/users/signup/`
2. **Create Company** → `POST /api/v1/companies/create/`
3. **Select Plan** → `POST /api/v1/subscriptions/`
4. **Select Modules** → `POST /api/v1/modules/company/enable/`
5. **Invite Team** → `POST /api/v1/users/invite/` (with seat limit checks)
6. **Check Status** → `GET /api/v1/onboarding/status/`

---

## Error Handling

All APIs return consistent error format:
```json
{
  "statusCode": 400,
  "status": "failure",
  "data": {},
  "errorCode": "VALIDATION_ERROR",
  "errorMessage": "Readable error message here"
}
```

Common error codes:
- `VALIDATION_ERROR` - Input validation failed
- `SEAT_LIMIT_REACHED` - Cannot invite more users (subscription limit)
- `NO_COMPANY` - User not associated with company
- `NOT_FOUND` - Resource not found
- `PERMISSION_DENIED` - Insufficient permissions

---

## Admin Portal Compatibility

All GET/UPDATE endpoints are designed to work with both:
- **Onboarding flow** (for new companies)
- **Admin portal** (for existing companies)

Examples:
- `GET /api/v1/companies/{id}/detail/` - Works in both contexts
- `PUT /api/v1/companies/{id}/update/` - Works in both contexts
- `PUT /api/v1/subscriptions/{id}/update/` - Update plan/seats anytime
- `POST /api/v1/modules/company/enable/` - Enable modules anytime

---

## Notes

- All endpoints require authentication except:
  - `GET /api/v1/subscriptions/plans/` (public)
  - `GET /api/v1/modules/definitions/` (public)
  - Signup/Signin endpoints

- Seat limits are enforced at invitation time, not at user activation
- Company `lifecycle_status` progresses: `signup` → `onboarding` → `trial`/`active`
- Subscription pricing is calculated automatically based on seat packs and discounts

