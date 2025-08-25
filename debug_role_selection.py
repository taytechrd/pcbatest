#!/usr/bin/env python3
"""
Debug script to test the exact role selection template rendering
"""

from app import app, db, User, Role
from flask import render_template_string

def test_role_selection_rendering():
    """Test the exact role selection template logic"""
    print("🔍 Testing role selection template rendering...")
    
    with app.app_context():
        # Get test user and roles
        user = User.query.get(1)  # admin user
        roles = Role.query.filter_by(is_active=True).all()
        
        print(f"User: {user.username}")
        print(f"User role: {user.role}")
        print(f"User role_id: {user.role_id}")
        print(f"User assigned_role: {user.assigned_role.name if user.assigned_role else 'None'}")
        
        # Create the exact template snippet
        template_snippet = """
<select class="form-control" id="role" name="role" required>
    <option value="">Rol seçin</option>
    {% for role in roles %}
    <option value="{{ role.name }}" 
            data-role-id="{{ role.id }}"
            {% if (user.assigned_role and user.assigned_role.id == role.id) or (not user.assigned_role and user.role == role.name) %}selected{% endif %}>
      {{ role.name.title() }}
      {% if role.description %} - {{ role.description }}{% endif %}
    </option>
    {% endfor %}
</select>
        """
        
        try:
            rendered = render_template_string(template_snippet, user=user, roles=roles)
            print("\n✅ Template rendered successfully")
            print("Rendered HTML:")
            print(rendered)
            
            # Check if any option has "selected"
            if 'selected' in rendered:
                print("\n✅ Found 'selected' attribute in rendered HTML")
                # Find which option is selected
                lines = rendered.split('\n')
                for i, line in enumerate(lines):
                    if 'selected' in line:
                        print(f"Selected line: {line.strip()}")
            else:
                print("\n❌ No 'selected' attribute found in rendered HTML")
                
        except Exception as e:
            print(f"❌ Template rendering failed: {e}")
            import traceback
            traceback.print_exc()

def test_different_users():
    """Test role selection for different users"""
    print("\n🧪 Testing role selection for all users...")
    
    with app.app_context():
        users = User.query.all()
        roles = Role.query.filter_by(is_active=True).all()
        
        for user in users:
            print(f"\n👤 User: {user.username}")
            print(f"   Legacy role: {user.role}")
            print(f"   Role ID: {user.role_id}")
            print(f"   Assigned role: {user.assigned_role.name if user.assigned_role else 'None'}")
            
            # Test selection logic for each role
            selected_roles = []
            for role in roles:
                condition1 = user.assigned_role and user.assigned_role.id == role.id
                condition2 = not user.assigned_role and user.role == role.name
                is_selected = condition1 or condition2
                
                if is_selected:
                    selected_roles.append(role.name)
            
            print(f"   Should select: {selected_roles}")

def test_javascript_interaction():
    """Check if there might be JavaScript interfering with the selection"""
    print("\n🔧 Checking for JavaScript interactions...")
    
    # Look for any JavaScript that might be affecting the role dropdown
    template_js = '''
    $(document).ready(function () {
        console.log("Role dropdown value:", $("#role").val());
        console.log("Selected option:", $("#role option:selected").text());
        
        // Check if role dropdown gets modified by JavaScript
        $("#role").on('change', function() {
            console.log("Role changed to:", $(this).val());
            $("#role_id").val($(this).find('option:selected').data('role-id'));
        });
    });
    '''
    
    print("JavaScript code that should be added for debugging:")
    print(template_js)

if __name__ == "__main__":
    print("🚀 Debugging role selection in edit-user page...")
    print("=" * 60)
    
    test_role_selection_rendering()
    test_different_users()
    test_javascript_interaction()
    
    print("\n" + "=" * 60)
    print("💡 If the role selection is still showing 'Rol seçin':")
    print("1. Check if the template is being cached")
    print("2. Verify that the browser is loading the latest HTML")
    print("3. Check browser developer tools for JavaScript errors")
    print("4. Look for any JavaScript that might be resetting the dropdown")
    print("5. Try hard refresh (Ctrl+F5) to clear cache")