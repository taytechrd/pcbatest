#!/usr/bin/env python3
"""
Test script to simulate authenticated access to edit-user page
"""

from app import app, db, User
from flask import session
import requests

def test_authenticated_access():
    """Test accessing edit-user page with authentication"""
    print("🔐 Testing authenticated access to edit-user page...")
    
    # Test with requests to the actual server
    base_url = "http://localhost:9002"
    
    # Create a session
    session = requests.Session()
    
    try:
        # First, get the login page to establish session
        login_response = session.get(f"{base_url}/login")
        print(f"Login page status: {login_response.status_code}")
        
        # Attempt to login (you'll need to provide credentials)
        login_data = {
            'username': 'admin',
            'password': 'admin123'  # Default admin password
        }
        
        # Post login credentials
        auth_response = session.post(f"{base_url}/login", data=login_data)
        print(f"Login attempt status: {auth_response.status_code}")
        
        if auth_response.status_code == 302:
            print("✅ Login successful (redirected)")
            
            # Now try to access edit-user page
            edit_response = session.get(f"{base_url}/edit-user/1")
            print(f"Edit-user page status: {edit_response.status_code}")
            
            if edit_response.status_code == 200:
                print("✅ Edit-user page accessible")
                
                # Check if roles are in the response
                page_content = edit_response.text
                
                # Check for role dropdown
                if 'Rol seçin' in page_content:
                    print("✅ Role selection dropdown found")
                    
                    # Count role options
                    role_count = page_content.count('<option value="') - 1  # -1 for empty option
                    print(f"✅ Found {role_count} role options")
                    
                    # Check for specific roles
                    roles_found = []
                    if 'value="admin"' in page_content:
                        roles_found.append("admin")
                    if 'value="technician"' in page_content:
                        roles_found.append("technician")
                    if 'value="operator"' in page_content:
                        roles_found.append("operator")
                    if 'value="viewer"' in page_content:
                        roles_found.append("viewer")
                    if 'value="Developer"' in page_content:
                        roles_found.append("Developer")
                    
                    print(f"✅ Roles found in page: {roles_found}")
                    
                    if len(roles_found) >= 4:  # At least 4 roles should be there
                        print("🎉 ROLES ARE WORKING CORRECTLY!")
                        return True
                    else:
                        print(f"⚠️ Only {len(roles_found)} roles found, expected 5")
                        
                else:
                    print("❌ Role selection dropdown NOT found")
                    print("First 500 chars of response:")
                    print(page_content[:500])
                    
            else:
                print(f"❌ Cannot access edit-user page: {edit_response.status_code}")
                
        else:
            print(f"❌ Login failed: {auth_response.status_code}")
            print("Response content:", auth_response.text[:200])
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on localhost:9002?")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    return False

def check_user_permissions():
    """Check what users exist and their permissions"""
    print("\n👥 Checking available users and permissions...")
    
    with app.app_context():
        users = User.query.all()
        print(f"Total users: {len(users)}")
        
        for user in users:
            print(f"\n👤 User: {user.username}")
            print(f"   - Email: {user.email}")
            print(f"   - Role: {user.role}")
            print(f"   - Role ID: {user.role_id}")
            print(f"   - Active: {user.is_active}")
            print(f"   - Has manage_users permission: {user.has_permission('manage_users')}")

if __name__ == "__main__":
    print("🧪 Testing edit-user page role display...")
    
    check_user_permissions()
    success = test_authenticated_access()
    
    if not success:
        print(f"\n💡 Troubleshooting steps:")
        print(f"1. Make sure PCBA server is running on localhost:9002")
        print(f"2. Try logging in with admin/admin123 credentials") 
        print(f"3. Navigate to Users > Edit User manually")
        print(f"4. Check browser developer tools for any errors")
        print(f"5. Try hard refresh (Ctrl+F5) to clear cache")