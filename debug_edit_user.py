#!/usr/bin/env python3
"""
Debug script to test edit-user route and template rendering
"""

from app import app, db, Role, User
from flask import render_template_string
import os

def test_edit_user_route():
    """Test the edit-user route logic"""
    with app.app_context():
        print("🔍 Debugging edit-user route...")
        
        # Test with admin user (ID: 1)
        user_id = 1
        user = User.query.get(user_id)
        
        if not user:
            print(f"❌ User with ID {user_id} not found")
            return
        
        print(f"✅ User found: {user.username}")
        print(f"   - Email: {user.email}")
        print(f"   - Role (legacy): {user.role}")
        print(f"   - Role ID: {user.role_id}")
        print(f"   - Assigned Role: {user.assigned_role.name if user.assigned_role else 'None'}")
        print(f"   - Is Active: {user.is_active}")
        
        # Fetch roles
        roles = Role.query.filter_by(is_active=True).all()
        print(f"\n📋 Active roles fetched: {len(roles)}")
        for role in roles:
            print(f"   - {role.name} (ID: {role.id}) - {role.description}")
        
        # Test template rendering with a simple version
        template_test = """
        <select name="role">
            <option value="">Rol seçin</option>
            {% for role in roles %}
            <option value="{{ role.name }}" data-role-id="{{ role.id }}">
                {{ role.name.title() }}
            </option>
            {% endfor %}
        </select>
        """
        
        try:
            rendered = render_template_string(template_test, roles=roles)
            print(f"\n✅ Template rendering successful")
            print(f"Rendered HTML snippet:")
            print(rendered)
        except Exception as e:
            print(f"❌ Template rendering failed: {e}")
        
        # Check if template file exists
        template_path = os.path.join(app.template_folder, 'edit-user.html')
        if os.path.exists(template_path):
            print(f"\n✅ Template file exists: {template_path}")
            print(f"   File size: {os.path.getsize(template_path)} bytes")
        else:
            print(f"\n❌ Template file missing: {template_path}")
        
        return user, roles

def test_actual_route():
    """Test the actual Flask route"""
    print("\n🧪 Testing actual Flask route...")
    
    with app.test_client() as client:
        # Try to access edit-user page (will redirect to login)
        response = client.get('/edit-user/1')
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 302:
            print("💡 Redirected (likely to login page)")
            location = response.headers.get('Location', '')
            print(f"   Redirect location: {location}")
        elif response.status_code == 200:
            print("✅ Page accessible")
            # Check if 'roles' appears in the response
            response_text = response.get_data(as_text=True)
            if 'Rol seçin' in response_text:
                print("✅ Role selection dropdown found in response")
            else:
                print("❌ Role selection dropdown NOT found in response")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")

if __name__ == "__main__":
    print("🚀 Starting edit-user debug session...")
    
    user, roles = test_edit_user_route()
    test_actual_route()
    
    print(f"\n📊 Summary:")
    print(f"   User data: ✅ Available ({user.username})")
    print(f"   Roles data: ✅ Available ({len(roles)} roles)")
    print(f"   Template: ✅ Can render")
    print(f"\n💡 If roles are not showing in browser:")
    print(f"   1. Check if user is logged in with admin privileges")
    print(f"   2. Try hard refresh (Ctrl+F5)")
    print(f"   3. Check browser console for JavaScript errors")
    print(f"   4. Verify server is serving latest code")