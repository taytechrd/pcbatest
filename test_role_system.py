#!/usr/bin/env python3
"""
Simple test to check edit-user page functionality without external requests
"""

from app import app, db, User, Role
from flask import url_for

def test_template_rendering():
    """Test if the edit-user template renders correctly with roles"""
    print("🧪 Testing edit-user template rendering...")
    
    with app.app_context():
        # Get test user and roles
        user = User.query.get(1)  # admin user
        roles = Role.query.filter_by(is_active=True).all()
        
        print(f"✅ User: {user.username}")
        print(f"✅ Roles: {len(roles)} found")
        
        # Test the Flask route logic directly
        with app.test_request_context():
            # Simulate the edit_user route
            try:
                from flask import render_template
                rendered_html = render_template('edit-user.html', user=user, roles=roles)
                
                print("✅ Template rendered successfully")
                
                # Check if roles appear in the rendered HTML
                if 'Rol seçin' in rendered_html:
                    print("✅ Role selection dropdown found in template")
                    
                    # Count role options in the rendered HTML
                    role_option_count = rendered_html.count('data-role-id=')
                    print(f"✅ Found {role_option_count} role options in rendered HTML")
                    
                    # Check for specific roles
                    roles_in_html = []
                    for role in roles:
                        if f'value="{role.name}"' in rendered_html:
                            roles_in_html.append(role.name)
                    
                    print(f"✅ Roles in HTML: {roles_in_html}")
                    
                    if len(roles_in_html) >= 4:
                        print("🎉 SUCCESS: All roles are properly rendered in the template!")
                        return True
                    else:
                        print(f"⚠️ Issue: Only {len(roles_in_html)} roles found in HTML")
                        
                else:
                    print("❌ Role selection dropdown NOT found in template")
                    # Show a snippet of the HTML around where roles should be
                    role_section_start = rendered_html.find('name="role"')
                    if role_section_start != -1:
                        snippet = rendered_html[role_section_start-100:role_section_start+500]
                        print("HTML snippet around role field:")
                        print(snippet)
                    
            except Exception as e:
                print(f"❌ Template rendering failed: {e}")
                import traceback
                traceback.print_exc()
    
    return False

def check_route_registration():
    """Check if the edit-user route is properly registered"""
    print("\n🔍 Checking route registration...")
    
    with app.app_context():
        # Check if edit-user route exists
        routes = []
        for rule in app.url_map.iter_rules():
            if 'edit-user' in rule.rule:
                routes.append(f"{rule.rule} -> {rule.endpoint} (methods: {rule.methods})")
        
        if routes:
            print("✅ Edit-user routes found:")
            for route in routes:
                print(f"   {route}")
        else:
            print("❌ No edit-user routes found")
        
        return len(routes) > 0

def verify_role_system():
    """Verify that the role system is working correctly"""
    print("\n🔐 Verifying role system...")
    
    with app.app_context():
        # Check if Role model works
        try:
            total_roles = Role.query.count()
            active_roles = Role.query.filter_by(is_active=True).count()
            
            print(f"✅ Total roles in database: {total_roles}")
            print(f"✅ Active roles: {active_roles}")
            
            if active_roles >= 4:
                print("✅ Sufficient roles available")
                return True
            else:
                print("⚠️ Not enough active roles")
                
        except Exception as e:
            print(f"❌ Role system error: {e}")
    
    return False

if __name__ == "__main__":
    print("🚀 Testing edit-user page role functionality...")
    print("=" * 60)
    
    # Run tests
    route_ok = check_route_registration()
    role_system_ok = verify_role_system()
    template_ok = test_template_rendering()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"   Route Registration: {'✅ PASS' if route_ok else '❌ FAIL'}")
    print(f"   Role System: {'✅ PASS' if role_system_ok else '❌ FAIL'}")
    print(f"   Template Rendering: {'✅ PASS' if template_ok else '❌ FAIL'}")
    
    if all([route_ok, role_system_ok, template_ok]):
        print("\n🎉 ALL TESTS PASSED! Role system is working correctly.")
        print("\n💡 If you're still not seeing roles in the browser:")
        print("   1. Make sure you're logged in as admin")
        print("   2. Try hard refresh (Ctrl+F5)")
        print("   3. Check browser console for JavaScript errors") 
        print("   4. Clear browser cache")
        print("   5. Restart the server")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")