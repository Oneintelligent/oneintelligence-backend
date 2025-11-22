#!/usr/bin/env python3
"""
Script to validate the onboarding status API
Tests that role and status fields are returned correctly for team members
"""

import os
import sys
import django
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from app.platform.companies.models import Company
from app.platform.onboarding.views import OnboardingViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

def validate_onboarding_api():
    """Validate the onboarding status API returns role and status for team members"""
    
    print("=" * 80)
    print("Onboarding Status API Validation Script")
    print("=" * 80)
    print()
    
    # Get a test user with a company
    user = User.objects.filter(company__isnull=False).first()
    
    if not user:
        print("❌ No user with company found. Please create a user with a company first.")
        return False
    
    print(f"✅ Testing with user: {user.email}")
    print(f"   Company: {user.company.name if user.company else 'None'}")
    print(f"   User role: {user.role}")
    print(f"   User status: {user.status}")
    print()
    
    # Get all users in the company
    company = user.company
    if company:
        company_users = User.objects.filter(
            company=company,
            status__in=[User.Status.ACTIVE, User.Status.PENDING]
        )
        print(f"📊 Company has {company_users.count()} users (ACTIVE or PENDING):")
        for u in company_users:
            print(f"   - {u.email}: role={u.role}, status={u.status}")
        print()
    
    # Create a request
    factory = APIRequestFactory()
    request = factory.get('/api/v1/onboarding/status/')
    request.user = user
    
    # Create viewset instance
    viewset = OnboardingViewSet()
    viewset.request = request
    
    # Call the get_status action
    try:
        response = viewset.get_status(request)
        
        if response.status_code != 200:
            print(f"❌ API returned status code: {response.status_code}")
            print(f"   Response: {response.data}")
            return False
        
        data = response.data.get('data', {})
        steps = data.get('steps', {})
        team_data = steps.get('team', {})
        members = team_data.get('members', [])
        
        print("=" * 80)
        print("API Response Validation")
        print("=" * 80)
        print()
        
        print(f"✅ API returned status code: {response.status_code}")
        print(f"✅ Total team members in response: {len(members)}")
        print()
        
        # Validate each member
        all_valid = True
        for i, member in enumerate(members, 1):
            print(f"Member {i}: {member.get('email', 'N/A')}")
            
            # Check required fields
            required_fields = ['userId', 'email', 'role', 'status', 'roles', 'primary_role']
            missing_fields = [f for f in required_fields if f not in member]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
                all_valid = False
            else:
                print(f"   ✅ All required fields present")
            
            # Check role field
            role = member.get('role')
            if role is None:
                print(f"   ⚠️  role field is None")
                all_valid = False
            elif role == "":
                print(f"   ⚠️  role field is empty string")
                all_valid = False
            else:
                print(f"   ✅ role: {role}")
            
            # Check status field
            status = member.get('status')
            if status is None:
                print(f"   ⚠️  status field is None")
                all_valid = False
            elif status == "":
                print(f"   ⚠️  status field is empty string")
                all_valid = False
            else:
                print(f"   ✅ status: {status}")
            
            # Check roles array
            roles = member.get('roles', [])
            print(f"   📋 RBAC roles count: {len(roles)}")
            if roles:
                for r in roles:
                    print(f"      - {r.get('code')}: {r.get('display_name')}")
            
            # Check primary_role
            primary_role = member.get('primary_role')
            if primary_role:
                print(f"   ✅ primary_role: {primary_role.get('code')} - {primary_role.get('display_name')}")
            else:
                print(f"   ⚠️  primary_role is None")
            
            print()
        
        # Print full response for debugging
        print("=" * 80)
        print("Full Team Data Response (JSON)")
        print("=" * 80)
        print(json.dumps(team_data, indent=2, default=str))
        print()
        
        if all_valid:
            print("=" * 80)
            print("✅ All validations passed!")
            print("=" * 80)
            return True
        else:
            print("=" * 80)
            print("❌ Some validations failed. See details above.")
            print("=" * 80)
            return False
            
    except Exception as e:
        print(f"❌ Error calling API: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database_users():
    """Check users in database to see their role and status values"""
    print("=" * 80)
    print("Database User Check")
    print("=" * 80)
    print()
    
    users = User.objects.filter(company__isnull=False)[:10]
    
    print(f"Checking {users.count()} users with companies:")
    print()
    
    for user in users:
        print(f"User: {user.email}")
        print(f"  - Company: {user.company.name if user.company else 'None'}")
        print(f"  - role (model field): {repr(user.role)} (type: {type(user.role).__name__})")
        print(f"  - status (model field): {repr(user.status)} (type: {type(user.status).__name__})")
        print(f"  - role value: {user.role}")
        print(f"  - status value: {user.status}")
        print(f"  - getattr role: {getattr(user, 'role', 'NOT_FOUND')}")
        print(f"  - getattr status: {getattr(user, 'status', 'NOT_FOUND')}")
        
        # Check if fields exist in the model
        from django.db import models
        role_field = user._meta.get_field('role')
        status_field = user._meta.get_field('status')
        print(f"  - role field type: {type(role_field)}")
        print(f"  - status field type: {type(status_field)}")
        print()
    
    print("=" * 80)
    print()
    
    # Also test the actual query that's used in the view
    if users.exists():
        test_user = users.first()
        company = test_user.company
        if company:
            print("Testing the exact query used in onboarding view:")
            test_users = User.objects.filter(
                company=company,
                status__in=[User.Status.ACTIVE, User.Status.PENDING]
            ).select_related("company")
            
            print(f"Found {test_users.count()} users with the query:")
            for u in test_users:
                print(f"  - {u.email}: role={repr(u.role)}, status={repr(u.status)}")
            print()


if __name__ == "__main__":
    print()
    check_database_users()
    print()
    success = validate_onboarding_api()
    print()
    sys.exit(0 if success else 1)

