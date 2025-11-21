# OneIntelligence API - Quick Reference Guide

**Base URL:** `http://localhost:8000`  
**API Version:** `/api/v1/`

---

## Authentication

### Sign Up
```http
POST /api/v1/users/signup/
Body: { email, password, first_name, last_name, company_name, role }
Response: { user, access_token, refresh_token }
```

### Sign In
```http
POST /api/v1/users/signin/
Body: { email, password }
Response: { user, access_token, refresh_token }
```

### Get Current User
```http
GET /api/v1/users/me/
Headers: Authorization: Bearer {token}
```

### Refresh Token
```http
POST /api/v1/users/token/refresh/
(Cookie: oi_refresh_token sent automatically)
Response: { access }
```

### Sign Out
```http
POST /api/v1/users/signout/
Headers: Authorization: Bearer {token}
```

---

## Standard Response Format

```json
{
  "statusCode": 200,
  "status": "success" | "failure",
  "data": { ... },
  "errorCode": null | "ERROR_CODE",
  "errorMessage": null | "Message"
}
```

---

## Common Endpoints

### Users
- `GET /api/v1/users/me/` - Current user
- `PATCH /api/v1/users/me/update/` - Update profile
- `POST /api/v1/users/invite/` - Invite user
- `POST /api/v1/users/accept-invite/` - Accept invite

### Companies
- `POST /api/v1/companies/create/` - Create company
- `GET /api/v1/companies/{id}/detail/` - Get company
- `PATCH /api/v1/companies/{id}/update/` - Update company

### Onboarding
- `GET /api/v1/onboarding/status/` - Get status
- `POST /api/v1/onboarding/complete/{step}/` - Complete step

### Subscriptions
- `GET /api/v1/subscriptions/plans/` - List plans (public)
- `GET /api/v1/subscriptions/company/` - Get subscription
- `POST /api/v1/subscriptions/` - Create subscription

### Modules
- `GET /api/v1/modules/definitions/` - List all modules
- `GET /api/v1/modules/company/company/` - Company modules
- `POST /api/v1/modules/company/enable/` - Enable modules
- `DELETE /api/v1/modules/company/{id}/disable/` - Disable module

### Teams
- `GET /api/v1/teams/` - List teams
- `POST /api/v1/teams/` - Create team
- `GET /api/v1/teams/{id}/` - Get team
- `PATCH /api/v1/teams/{id}/` - Update team
- `DELETE /api/v1/teams/{id}/` - Delete team

### Consent
- `GET /api/v1/consent/` - Get consent
- `POST /api/v1/consent/` - Create/update consent

### FLAC Policies
- `GET /api/v1/flac/policies/` - List policies
- `POST /api/v1/flac/policies/` - Create policy

### Sales
- `GET /api/v1/accounts/` - List accounts
- `POST /api/v1/accounts/` - Create account
- `GET /api/v1/leads/` - List leads
- `POST /api/v1/leads/` - Create lead
- `GET /api/v1/opportunities/` - List opportunities
- `POST /api/v1/opportunities/` - Create opportunity
- `GET /api/v1/activities/` - List activities
- `GET /api/v1/dashboard/` - Sales dashboard

### Projects
- `GET /api/v1/projects/` - List projects
- `POST /api/v1/projects/` - Create project
- `GET /api/v1/projects/{id}/` - Get project
- `PATCH /api/v1/projects/{id}/` - Update project
- `DELETE /api/v1/projects/{id}/` - Delete project

### Tasks
- `GET /api/v1/tasks/` - List tasks
- `POST /api/v1/tasks/` - Create task
- `GET /api/v1/tasks/{id}/` - Get task
- `PATCH /api/v1/tasks/{id}/` - Update task
- `DELETE /api/v1/tasks/{id}/` - Delete task

### Support
- `GET /api/v1/tickets/` - List tickets
- `POST /api/v1/tickets/` - Create ticket
- `GET /api/v1/comments/` - List comments
- `POST /api/v1/comments/` - Create comment

### AI
- `POST /api/oneintelligentai/chat/` - Chat
- `POST /api/oneintelligentai/audio-chat/` - Audio chat
- `POST /api/oneintelligentai/image-chat/` - Image chat

---

## Pagination

```
GET /api/v1/projects/?page=1&page_size=20&ordering=-created_date
```

**Defaults:**
- `page`: 1
- `page_size`: 20
- `max_page_size`: 100

---

## Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `AUTH_ERROR` | 401 | Authentication required |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INTERNAL_SERVER_ERROR` | 500 | Server error |

---

## Request Headers

```http
Content-Type: application/json
Authorization: Bearer {access_token}
```

---

## Token Lifetime

- **Access Token**: 6 hours
- **Refresh Token**: 7 days (HTTP-only cookie)

---

## Frontend Integration Pattern

```typescript
// 1. API Client
const apiClient = new APIClient(baseURL);

// 2. Make Request
const response = await apiClient.get<User>('/users/me/');

// 3. Handle Response
if (response.status === 'success') {
  const user = response.data;
} else {
  // Handle error
  console.error(response.errorMessage);
}
```

---

## Quick TypeScript Types

```typescript
interface APIResponse<T> {
  statusCode: number;
  status: 'success' | 'failure';
  data: T;
  errorCode?: string;
  errorMessage?: string;
}

interface User {
  userId: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  company?: Company;
}

interface Company {
  companyId: string;
  name: string;
  plan: string;
  lifecycle_status: string;
}
```

---

## API Documentation URLs

- **Swagger UI**: `/api/schema/swagger-ui/`
- **ReDoc**: `/api/schema/redoc/`
- **OpenAPI Schema**: `/api/schema/`

---

**For detailed documentation, see:** `ARCHITECTURE_AND_API_DOCUMENTATION.md`

