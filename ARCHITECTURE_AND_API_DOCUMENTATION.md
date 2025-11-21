# OneIntelligence Backend - Architecture & API Documentation

**Version:** 1.0.0  
**Last Updated:** 2024  
**Base URL:** `http://localhost:8000` (Development)  
**API Version:** `/api/v1/`

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Design Principles](#api-design-principles)
3. [Authentication & Authorization](#authentication--authorization)
4. [API Endpoints](#api-endpoints)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)
7. [Frontend Integration Guide](#frontend-integration-guide)
8. [Scalability Considerations](#scalability-considerations)

---

## Architecture Overview

### System Architecture

The OneIntelligence backend follows a **layered, modular architecture** designed for scalability and maintainability:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ HTTP/REST API
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              API Gateway / URL Router                         │
│              (/api/v1/, /api/oneintelligentai/)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌────────▼────────┐  ┌─────▼──────┐
│   Platform   │  │   Workspace     │  │     AI     │
│   Services   │  │    Modules      │  │  Services  │
└───────┬──────┘  └────────┬────────┘  └─────┬──────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                ┌───────────▼───────────┐
                │   Core Services       │
                │  (Audit, Files, etc.) │
                └───────────┬───────────┘
                           │
                ┌───────────▼───────────┐
                │   Database Layer      │
                │   (PostgreSQL)        │
                └───────────────────────┘
```

### Application Layers

#### 1. **Platform Services** (`app.platform.*`)
Core platform functionality that applies across all workspaces:
- **Accounts**: User management, authentication, profiles
- **Companies**: Organization management
- **RBAC**: Role-based access control
- **Modules**: Feature module registry and enablement
- **Subscriptions**: Billing and subscription management
- **Onboarding**: User/company onboarding flows
- **Teams**: Organizational structure
- **Consent**: GDPR and consent management
- **FLAC**: Field-level access control
- **Licensing**: Seat management and enforcement
- **Invites**: User invitation system

#### 2. **Workspace Modules** (`app.workspace.*`)
Business domain-specific modules:
- **Sales**: CRM, leads, opportunities, accounts
- **Projects**: Project management
- **Tasks**: Task management
- **Support**: Ticket management
- **Dashboard**: Analytics and reporting

#### 3. **AI Services** (`app.ai.*`)
AI-powered features:
- **OneIntelligentAI**: Chat, audio, and image processing

#### 4. **Core Services** (`app.core.*`)
Shared infrastructure:
- **Models**: Base models, audit trails, attachments
- **Services**: Audit logging, file handling

### Technology Stack

- **Framework**: Django 4.x + Django REST Framework
- **Database**: PostgreSQL
- **Cache**: Redis (django-redis)
- **Authentication**: JWT (django-rest-framework-simplejwt)
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)
- **CORS**: django-cors-headers

---

## API Design Principles

### 1. **RESTful Design**
- Resource-based URLs (`/api/v1/users/`, `/api/v1/projects/`)
- HTTP methods: GET (read), POST (create), PUT/PATCH (update), DELETE (remove)
- Stateless requests

### 2. **Standardized Response Format**
All API responses follow a consistent structure:

```json
{
  "statusCode": 200,
  "status": "success" | "failure",
  "data": { ... },
  "errorCode": null | "ERROR_CODE",
  "errorMessage": null | "Human-readable error message"
}
```

### 3. **Versioning**
- API version in URL: `/api/v1/`
- AI endpoints: `/api/oneintelligentai/`
- Future versions: `/api/v2/`

### 4. **Pagination**
List endpoints support pagination:
- `?page=1&page_size=20`
- Default: 20 items per page
- Max: 100 items per page

### 5. **Filtering & Sorting**
- Query parameters for filtering: `?status=active&company=uuid`
- Sorting: `?ordering=-created_date`

---

## Authentication & Authorization

### Authentication Flow

#### 1. **Sign Up**
```http
POST /api/v1/users/signup/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Acme Corp",
  "role": "SuperAdmin"
}
```

**Response:**
```json
{
  "statusCode": 201,
  "status": "success",
  "data": {
    "user": {
      "userId": "uuid",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "company": { ... },
      "role": "SuperAdmin",
      "status": "Pending"
    },
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Note:** Refresh token is also set as HTTP-only cookie (`oi_refresh_token`).

#### 2. **Sign In**
```http
POST /api/v1/users/signin/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:** Same as signup (access_token + refresh_token cookie)

#### 3. **Token Refresh**
```http
POST /api/v1/users/token/refresh/
Content-Type: application/json

{
  "refresh": "refresh_token_string"
}
```

**OR** use the HTTP-only cookie (automatically sent):
```http
POST /api/v1/users/token/refresh/
```

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "access": "new_access_token"
  }
}
```

#### 4. **Sign Out**
```http
POST /api/v1/users/signout/
Authorization: Bearer {access_token}
```

### Authorization Headers

For authenticated requests:
```http
Authorization: Bearer {access_token}
```

### Token Lifetime
- **Access Token**: 6 hours
- **Refresh Token**: 7 days (stored in HTTP-only cookie)

### Role-Based Access Control (RBAC)

The system uses a hierarchical RBAC model:

#### Platform Roles
- `PlatformAdmin`: Full platform access
- `SuperAdmin`: Company-level super admin
- `Admin`: Company admin
- `Manager`: Department/team manager
- `User`: Standard user

#### Permission System
Permissions are checked at:
1. **Module Level**: Access to entire modules (Sales, Projects, etc.)
2. **Action Level**: CREATE, READ, UPDATE, DELETE, MANAGE
3. **Record Level**: Field-level access control (FLAC)

**Example Permission Check:**
```python
# Backend automatically checks permissions
# Frontend should handle 403 responses gracefully
```

---

## API Endpoints

### Base URLs
- **Platform APIs**: `/api/v1/`
- **AI APIs**: `/api/oneintelligentai/`
- **API Docs**: `/api/schema/swagger-ui/` (Swagger UI)
- **API Docs**: `/api/schema/redoc/` (ReDoc)

---

### Authentication & User Management

#### Sign Up
```http
POST /api/v1/users/signup/
```
**Request Body:**
```json
{
  "email": "string (required)",
  "password": "string (required, min 8 chars)",
  "first_name": "string (optional)",
  "last_name": "string (optional)",
  "company_name": "string (required)",
  "role": "SuperAdmin | Admin | User (default: User)"
}
```

#### Sign In
```http
POST /api/v1/users/signin/
```
**Request Body:**
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

#### Get Current User
```http
GET /api/v1/users/me/
Authorization: Bearer {token}
```

#### Update User Profile
```http
PATCH /api/v1/users/me/update/
Authorization: Bearer {token}
```
**Request Body:**
```json
{
  "first_name": "string (optional)",
  "last_name": "string (optional)",
  "phone": "string (optional)",
  "profile_picture_url": "string (optional)",
  "language_preference": "string (optional)",
  "time_zone": "string (optional)"
}
```

#### Invite User
```http
POST /api/v1/users/invite/
Authorization: Bearer {token}
```
**Request Body:**
```json
{
  "email": "string (required)",
  "role": "string (required)",
  "team_id": "uuid (optional)"
}
```

#### Accept Invite
```http
POST /api/v1/users/accept-invite/
```
**Request Body:**
```json
{
  "token": "uuid (required)",
  "password": "string (required)",
  "first_name": "string (optional)",
  "last_name": "string (optional)"
}
```

#### Forgot Password
```http
POST /api/v1/users/forgot-password/
```
**Request Body:**
```json
{
  "email": "string (required)"
}
```

#### Reset Password
```http
POST /api/v1/users/reset-password/
```
**Request Body:**
```json
{
  "token": "uuid (required)",
  "new_password": "string (required)"
}
```

#### Verify Email
```http
POST /api/v1/users/verify-email/
```
**Request Body:**
```json
{
  "token": "uuid (required)"
}
```

---

### Company Management

#### Create Company
```http
POST /api/v1/companies/create/
Authorization: Bearer {token}
```
**Request Body:**
```json
{
  "name": "string (required)",
  "email": "string (optional)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "country": "string (optional)"
}
```

#### Get Company Details
```http
GET /api/v1/companies/{companyId}/detail/
Authorization: Bearer {token}
```

#### Update Company
```http
PATCH /api/v1/companies/{companyId}/update/
Authorization: Bearer {token}
```
**Request Body:**
```json
{
  "name": "string (optional)",
  "email": "string (optional)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "website": "string (optional)",
  "logo_url": "string (optional)",
  "industry": "string (optional)",
  "company_size": "string (optional)"
}
```

---

### Onboarding

#### Get Onboarding Status
```http
GET /api/v1/onboarding/status/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "current_step": "company_details",
    "completed_steps": ["signup"],
    "total_steps": 5,
    "is_complete": false,
    "next_step": "company_details"
  }
}
```

#### Complete Onboarding Step
```http
POST /api/v1/onboarding/complete/{step_name}/
Authorization: Bearer {token}
```

**Steps:**
- `company_details`
- `subscription_selection`
- `module_selection`
- `team_setup`
- `invite_users`

**Request Body (varies by step):**
```json
{
  "step_data": { ... }
}
```

---

### Subscriptions

#### Get Subscription Plans
```http
GET /api/v1/subscriptions/plans/
```
**Public endpoint** (no auth required)

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": [
    {
      "planId": "uuid",
      "name": "Starter",
      "code": "starter",
      "price_monthly": 29.99,
      "price_yearly": 299.99,
      "features": ["feature1", "feature2"],
      "max_users": 10,
      "max_storage_mb": 500
    }
  ]
}
```

#### Get Company Subscription
```http
GET /api/v1/subscriptions/company/
Authorization: Bearer {token}
```

#### Create/Update Subscription
```http
POST /api/v1/subscriptions/
PUT /api/v1/subscriptions/{subscriptionId}/update/
Authorization: Bearer {token}
```

---

### Modules

#### Get Module Definitions
```http
GET /api/v1/modules/definitions/
Authorization: Bearer {token}
```

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": [
    {
      "moduleId": "uuid",
      "code": "sales",
      "name": "Sales CRM",
      "description": "Customer relationship management",
      "category": "workspace",
      "is_enabled": true
    }
  ]
}
```

#### Get Company Modules
```http
GET /api/v1/modules/company/company/
Authorization: Bearer {token}
```

#### Enable Modules
```http
POST /api/v1/modules/company/enable/
Authorization: Bearer {token}
```
**Request Body:**
```json
{
  "module_codes": ["sales", "projects", "tasks"]
}
```

#### Disable Module
```http
DELETE /api/v1/modules/company/{companyModuleId}/disable/
Authorization: Bearer {token}
```

---

### Teams

#### Teams
```http
GET    /api/v1/teams/                 # List teams
POST   /api/v1/teams/                 # Create team
GET    /api/v1/teams/{id}/            # Get team details
PATCH  /api/v1/teams/{id}/            # Update team
DELETE /api/v1/teams/{id}/            # Delete team
```

---

### Consent Management

#### Consent
```http
GET    /api/v1/consent/               # Get consent status
POST   /api/v1/consent/               # Create/update consent
PATCH  /api/v1/consent/{id}/          # Update consent
```

---

### Field-Level Access Control (FLAC)

#### FLAC Policies
```http
GET    /api/v1/flac/policies/         # List field policies
POST   /api/v1/flac/policies/         # Create policy
GET    /api/v1/flac/policies/{id}/    # Get policy details
PATCH  /api/v1/flac/policies/{id}/    # Update policy
DELETE /api/v1/flac/policies/{id}/    # Delete policy
```

---

### Sales Module

#### Accounts
```http
GET    /api/v1/accounts/              # List accounts
POST   /api/v1/accounts/              # Create account
GET    /api/v1/accounts/{id}/         # Get account details
PATCH  /api/v1/accounts/{id}/         # Update account
DELETE /api/v1/accounts/{id}/         # Delete account
```

#### Leads
```http
GET    /api/v1/leads/                 # List leads
POST   /api/v1/leads/                 # Create lead
GET    /api/v1/leads/{id}/            # Get lead details
PATCH  /api/v1/leads/{id}/            # Update lead
DELETE /api/v1/leads/{id}/            # Delete lead
```

#### Opportunities
```http
GET    /api/v1/opportunities/         # List opportunities
POST   /api/v1/opportunities/        # Create opportunity
GET    /api/v1/opportunities/{id}/    # Get opportunity details
PATCH  /api/v1/opportunities/{id}/    # Update opportunity
DELETE /api/v1/opportunities/{id}/    # Delete opportunity
```

#### Activities
```http
GET    /api/v1/activities/            # List activities
POST   /api/v1/activities/            # Create activity
GET    /api/v1/activities/{id}/       # Get activity details
PATCH  /api/v1/activities/{id}/       # Update activity
DELETE /api/v1/activities/{id}/       # Delete activity
```

#### Sales Dashboard
```http
GET /api/v1/dashboard/                # Get sales dashboard data
```

---

### General Dashboard

#### Dashboard
```http
GET /api/v1/dashboard/                # Get workspace dashboard data
```

---

### Projects Module

#### Projects
```http
GET    /api/v1/projects/              # List projects
POST   /api/v1/projects/              # Create project
GET    /api/v1/projects/{id}/         # Get project details
PATCH  /api/v1/projects/{id}/         # Update project
DELETE /api/v1/projects/{id}/         # Delete project
```

---

### Tasks Module

#### Tasks
```http
GET    /api/v1/tasks/                 # List tasks
POST   /api/v1/tasks/                 # Create task
GET    /api/v1/tasks/{id}/            # Get task details
PATCH  /api/v1/tasks/{id}/            # Update task
DELETE /api/v1/tasks/{id}/            # Delete task
```

---

### Support Module

#### Tickets
```http
GET    /api/v1/tickets/               # List tickets
POST   /api/v1/tickets/               # Create ticket
GET    /api/v1/tickets/{id}/          # Get ticket details
PATCH  /api/v1/tickets/{id}/          # Update ticket
DELETE /api/v1/tickets/{id}/           # Delete ticket
```

#### Ticket Comments
```http
GET    /api/v1/comments/              # List comments
POST   /api/v1/comments/              # Create comment
GET    /api/v1/comments/{id}/         # Get comment details
PATCH  /api/v1/comments/{id}/          # Update comment
DELETE /api/v1/comments/{id}/         # Delete comment
```

---

### AI Services

#### Chat API
```http
POST /api/oneintelligentai/chat/
Authorization: Bearer {token}
```
**Request Body:**
```json
{
  "message": "string (required)",
  "conversation_id": "uuid (optional)",
  "context": { ... } // optional context
}
```

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "data": {
    "response": "AI response text",
    "conversation_id": "uuid",
    "tokens_used": 150
  }
}
```

#### Audio Chat
```http
POST /api/oneintelligentai/audio-chat/
Authorization: Bearer {token}
Content-Type: multipart/form-data

{
  "audio_file": File,
  "message": "string (optional)"
}
```

#### Image Chat
```http
POST /api/oneintelligentai/image-chat/
Authorization: Bearer {token}
Content-Type: multipart/form-data

{
  "image_file": File,
  "message": "string (required)"
}
```

---

## Data Models

### User Model
```typescript
interface User {
  userId: string;                    // UUID
  email: string;                     // Unique
  first_name: string;
  last_name: string;
  phone?: string;
  company?: Company;                 // Foreign key
  team?: Team;                       // Foreign key
  role: UserRole;                    // Enum
  status: UserStatus;                // Active | Inactive | Pending | Suspended
  profile_picture_url?: string;
  language_preference: string;       // Default: "en-US"
  time_zone: string;                 // Default: "UTC"
  email_verified: boolean;
  created_date: string;              // ISO datetime
  last_updated_date: string;         // ISO datetime
  preferences: Record<string, any>;   // JSON field
}

enum UserRole {
  PLATFORMADMIN = "PlatformAdmin",
  SUPERADMIN = "SuperAdmin",
  ADMIN = "Admin",
  MANAGER = "Manager",
  USER = "User",
  // ... more roles
}

enum UserStatus {
  ACTIVE = "Active",
  INACTIVE = "Inactive",
  PENDING = "Pending",
  SUSPENDED = "Suspended"
}
```

### Company Model
```typescript
interface Company {
  companyId: string;                 // UUID
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  country?: string;
  website?: string;
  domain?: string;
  logo_url?: string;
  industry?: string;
  company_size?: string;
  plan: string;                      // Default: "starter"
  lifecycle_status: CompanyLifecycle;
  time_zone: string;                 // Default: "UTC"
  language: string;                  // Default: "en-US"
  ai_enabled: boolean;
  monthly_ai_quota: number;
  created_date: string;
  last_updated_date: string;
}

enum CompanyLifecycle {
  SIGNUP = "signup",
  ONBOARDING = "onboarding",
  TRIAL = "trial",
  ACTIVE = "active",
  PAUSED = "paused",
  CANCELLED = "cancelled",
  SUSPENDED = "suspended"
}
```

### Common Fields
Most models include:
- `created_date`: ISO datetime
- `last_updated_date`: ISO datetime
- `created_by`: User reference (optional)
- Audit fields (via `app.core.models.base.BaseModel`)

---

## Error Handling

### Standard Error Response
```json
{
  "statusCode": 400 | 401 | 403 | 404 | 500,
  "status": "failure",
  "data": {},
  "errorCode": "ERROR_CODE",
  "errorMessage": "Human-readable error message"
}
```

### Common Error Codes

| Status Code | Error Code | Description |
|------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Request validation failed |
| 401 | `AUTH_ERROR` | Authentication required or invalid |
| 403 | `PERMISSION_DENIED` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 500 | `INTERNAL_SERVER_ERROR` | Server error |

### Error Handling Example

```typescript
// Frontend error handling
try {
  const response = await fetch('/api/v1/users/me/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  const data = await response.json();
  
  if (data.status === 'failure') {
    switch (data.errorCode) {
      case 'AUTH_ERROR':
        // Redirect to login
        break;
      case 'PERMISSION_DENIED':
        // Show permission error
        break;
      case 'VALIDATION_ERROR':
        // Show validation errors
        break;
      default:
        // Show generic error
    }
  }
} catch (error) {
  // Network error handling
}
```

---

## Frontend Integration Guide

### 1. API Client Setup

#### Base Configuration
```typescript
// lib/api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

class APIClient {
  private baseURL: string;
  private accessToken: string | null = null;

  constructor() {
    this.baseURL = `${API_BASE_URL}${API_VERSION}`;
    this.loadToken();
  }

  private loadToken() {
    // Load from localStorage or state management
    this.accessToken = localStorage.getItem('access_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // For cookie-based refresh tokens
    });

    const data: APIResponse<T> = await response.json();

    // Handle token refresh on 401
    if (data.statusCode === 401 && data.errorCode === 'AUTH_ERROR') {
      await this.refreshToken();
      // Retry request
      return this.request<T>(endpoint, options);
    }

    if (data.status === 'failure') {
      throw new APIError(data.errorCode, data.errorMessage);
    }

    return data;
  }

  async get<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, body?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async patch<T>(endpoint: string, body?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  }

  async delete<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  private async refreshToken(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/users/token/refresh/`, {
        method: 'POST',
        credentials: 'include', // Send HTTP-only cookie
      });

      const data = await response.json();
      if (data.status === 'success' && data.data.access) {
        this.accessToken = data.data.access;
        localStorage.setItem('access_token', data.data.access);
      } else {
        // Refresh failed, redirect to login
        this.logout();
      }
    } catch (error) {
      this.logout();
    }
  }

  logout() {
    this.accessToken = null;
    localStorage.removeItem('access_token');
    // Redirect to login
  }
}

export const apiClient = new APIClient();
```

#### Type Definitions
```typescript
// lib/types/api.ts
interface APIResponse<T> {
  statusCode: number;
  status: 'success' | 'failure';
  data: T;
  errorCode?: string;
  errorMessage?: string;
}

class APIError extends Error {
  constructor(
    public code: string,
    public message: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}
```

### 2. Authentication Flow

```typescript
// lib/api/auth.ts
export const authAPI = {
  async signup(data: SignUpRequest): Promise<User> {
    const response = await apiClient.post<{ user: User; access_token: string }>(
      '/users/signup/',
      data
    );
    
    // Store access token
    localStorage.setItem('access_token', response.data.access_token);
    apiClient.setAccessToken(response.data.access_token);
    
    return response.data.user;
  },

  async signin(email: string, password: string): Promise<User> {
    const response = await apiClient.post<{ user: User; access_token: string }>(
      '/users/signin/',
      { email, password }
    );
    
    localStorage.setItem('access_token', response.data.access_token);
    apiClient.setAccessToken(response.data.access_token);
    
    return response.data.user;
  },

  async signout(): Promise<void> {
    await apiClient.post('/users/signout/');
    localStorage.removeItem('access_token');
    apiClient.setAccessToken(null);
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<{ user: User }>('/users/me/');
    return response.data.user;
  },
};
```

### 3. React Hooks for API Calls

```typescript
// lib/hooks/useAPI.ts
import { useState, useEffect } from 'react';

export function useAPI<T>(
  apiCall: () => Promise<APIResponse<T>>,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<APIError | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const response = await apiCall();
        if (!cancelled) {
          setData(response.data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err as APIError);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      cancelled = true;
    };
  }, dependencies);

  return { data, loading, error };
}
```

### 4. Pagination Helper

```typescript
// lib/utils/pagination.ts
export interface PaginationParams {
  page?: number;
  page_size?: number;
  ordering?: string;
}

export function buildQueryString(params: Record<string, any>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });
  return searchParams.toString();
}

// Usage
const query = buildQueryString({ page: 1, page_size: 20, ordering: '-created_date' });
const response = await apiClient.get(`/projects/?${query}`);
```

### 5. Error Boundary

```typescript
// components/ErrorBoundary.tsx
import React from 'react';

interface Props {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: APIError }>;
}

export class APIErrorBoundary extends React.Component<Props, { error: APIError | null }> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    if (error instanceof APIError) {
      return { error };
    }
    return null;
  }

  render() {
    if (this.state.error) {
      const Fallback = this.props.fallback || DefaultErrorFallback;
      return <Fallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

---

## Scalability Considerations

### 1. **Database Optimization**
- **Indexing**: All foreign keys and frequently queried fields are indexed
- **Query Optimization**: Use `select_related()` and `prefetch_related()` for related objects
- **Connection Pooling**: Configured via Django database settings

### 2. **Caching Strategy**
- **Redis Cache**: Configured for session storage and API response caching
- **Cache Keys**: Namespaced by company/user for multi-tenancy
- **TTL**: Configurable per endpoint (e.g., AI responses: 12 hours)

### 3. **API Rate Limiting** (Recommended)
```python
# Add to settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

### 4. **Horizontal Scaling**
- **Stateless Design**: All endpoints are stateless (JWT tokens)
- **Database**: PostgreSQL supports read replicas
- **Cache**: Redis cluster for high availability
- **Load Balancing**: Use nginx/HAProxy for request distribution

### 5. **Background Tasks** (Recommended)
For long-running operations:
- **Celery**: Task queue for async processing
- **Redis/RabbitMQ**: Message broker
- Use cases: Email sending, report generation, data exports

### 6. **API Versioning Strategy**
- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: Maintain old versions for 6-12 months
- **Deprecation Warnings**: Include in API responses

### 7. **Monitoring & Logging**
- **Structured Logging**: JSON format for log aggregation
- **Error Tracking**: Integrate Sentry or similar
- **Performance Monitoring**: APM tools (New Relic, Datadog)
- **Health Checks**: `/health/` endpoint for load balancers

### 8. **Multi-Tenancy**
- **Company Isolation**: All queries filtered by `company` field
- **Row-Level Security**: Database-level isolation (PostgreSQL RLS)
- **Data Partitioning**: Consider sharding by company for very large scale

### 9. **CDN & Static Assets**
- **Static Files**: Serve via CDN (CloudFront, Cloudflare)
- **Media Files**: Use S3-compatible storage
- **API Responses**: Cache static data (module definitions, plans)

### 10. **Database Migrations**
- **Zero-Downtime Migrations**: Use Django migrations with care
- **Backward Compatible Changes**: Add fields as nullable first
- **Rollback Strategy**: Maintain migration rollback scripts

---

## Additional Resources

### API Documentation
- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

### Testing
- **Postman Collection**: Export from Swagger UI
- **Integration Tests**: See `test_super_admin_e2e.py`

### Support
- **Backend Issues**: Check logs in Django console
- **API Errors**: Review error codes and messages
- **Authentication Issues**: Verify JWT token expiration

---

## Changelog

### Version 1.0.0 (Current)
- Initial API documentation
- Complete endpoint coverage
- Authentication flow documented
- Frontend integration guide

---

**Document Maintained By:** Backend Team  
**Last Review Date:** 2024  
**Next Review Date:** Quarterly

